#!/usr/bin/env python
"""Weekly digest script - generates and sends to Telegram."""

import asyncio
import logging
import sys
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


async def main() -> None:
    """Generate weekly digest and send to Telegram."""
    settings = get_settings()
    processor = LLMProcessor(
        settings.vault_path,
        settings.todoist_api_key,
        singularity_api_key=settings.singularity_api_key,
        task_backend=settings.task_backend,
        provider_name=settings.llm_provider,
        openai_api_key=settings.openai_api_key,
        openai_model=settings.openai_model,
        openai_base_url=settings.openai_base_url,
    )
    git = VaultGit(settings.vault_path)

    logger.info("Starting weekly digest generation...")

    result_envelope = processor.generate_weekly_result()
    legacy_result = result_envelope.to_legacy_dict()
    report = format_process_report(legacy_result)

    has_error = result_envelope.error is not None

    if has_error:
        logger.error("Weekly digest failed: %s", result_envelope.error)
    else:
        logger.info("Weekly digest generated successfully")
        if not git.commit_and_push("chore: weekly digest"):
            logger.warning("Git commit/push failed for weekly digest")

    # Send to Telegram
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    try:
        user_id = settings.allowed_user_ids[0] if settings.allowed_user_ids else None
        if not user_id:
            logger.error("No allowed user IDs configured")
            sys.exit(1 if has_error else 0)

        try:
            await bot.send_message(chat_id=user_id, text=report)
        except Exception:
            # Fallback: send without HTML parsing
            await bot.send_message(chat_id=user_id, text=report, parse_mode=None)

        if has_error:
            logger.error("Weekly digest completed with errors")
            sys.exit(1)

        logger.info("Weekly digest sent to user %s", user_id)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        logging.exception("Weekly digest script failed")
        sys.exit(1)
