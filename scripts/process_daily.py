#!/usr/bin/env python3
"""Daily processing runner using shared Python processor architecture."""

import asyncio
import logging
import subprocess
import sys
from datetime import date
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from d_brain.bot.formatters import format_process_report
from d_brain.config import get_settings
from d_brain.services.git import VaultGit
from d_brain.services.processor import LLMProcessor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def rebuild_vault_graph(vault_path: Path) -> None:
    """Rebuild optional vault graph index if graph-builder skill exists."""
    script_path = vault_path / ".claude/skills/graph-builder/scripts/analyze.py"
    if not script_path.exists():
        logger.info("Graph builder script not found, skipping graph rebuild")
        return

    result = subprocess.run(
        ["uv", "run", str(script_path)],
        cwd=vault_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logger.warning("Graph rebuild failed: %s", result.stderr.strip() or "unknown error")
    else:
        logger.info("Vault graph rebuilt")


async def main() -> None:
    """Run daily processing and send report to Telegram."""
    settings = get_settings()
    processor = LLMProcessor(settings.vault_path, settings.todoist_api_key)
    git = VaultGit(settings.vault_path)

    today = date.today()
    logger.info("Starting daily processing for %s", today.isoformat())
    result_envelope = processor.process_daily_result(today)
    result = result_envelope.to_legacy_dict()

    if result_envelope.error is None:
        rebuild_vault_graph(settings.vault_path)
        git.commit_and_push(f"chore: process daily {today.isoformat()}")

    report = format_process_report(result)
    user_id = settings.allowed_user_ids[0] if settings.allowed_user_ids else None
    if not user_id:
        logger.error("No allowed user IDs configured, cannot send report")
        return

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    try:
        try:
            await bot.send_message(chat_id=user_id, text=report)
        except Exception:
            await bot.send_message(chat_id=user_id, text=report, parse_mode=None)
    finally:
        await bot.session.close()

    logger.info("Daily report sent to user %s", user_id)


if __name__ == "__main__":
    asyncio.run(main())
