"""Weekly digest command handler."""

import asyncio
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from d_brain.bot.formatters import format_process_report
from d_brain.config import get_settings
from d_brain.services.git import VaultGit
from d_brain.services.model_provider import get_active_provider
from d_brain.services.processor import ClaudeProcessor

router = Router(name="weekly")
logger = logging.getLogger(__name__)

MAX_WAIT_SECONDS = 1500  # slightly above provider timeout (1200s)


@router.message(Command("weekly"))
async def cmd_weekly(message: Message) -> None:
    """Handle /weekly command - generate weekly digest."""
    user_id = message.from_user.id if message.from_user else 0
    logger.info("Weekly digest triggered by user %s", user_id)

    status_msg = await message.answer("⏳ Генерирую недельный дайджест...")

    try:
        settings = get_settings()
        active_provider = get_active_provider(settings.llm_provider)
        processor = ClaudeProcessor(
            settings.vault_path,
            settings.todoist_api_key,
            provider_name=active_provider,
            openai_api_key=settings.openai_api_key,
            openai_model=settings.openai_model,
            openai_base_url=settings.openai_base_url,
        )
        git = VaultGit(settings.vault_path)

        async def run_with_progress() -> dict:
            task = asyncio.create_task(
                asyncio.to_thread(processor.generate_weekly)
            )

            elapsed = 0
            while not task.done() and elapsed < MAX_WAIT_SECONDS:
                await asyncio.sleep(30)
                elapsed += 30
                if not task.done():
                    try:
                        await status_msg.edit_text(
                            f"⏳ Генерирую дайджест... ({elapsed // 60}m {elapsed % 60}s)"
                        )
                    except Exception:
                        pass

            if not task.done():
                task.cancel()
                return {"error": "Weekly digest timed out"}

            return await task

        report = await run_with_progress()

        # Commit any changes (weekly goal updates, etc)
        if "error" not in report:
            pushed = await asyncio.to_thread(git.commit_and_push, "chore: weekly digest")
            if not pushed:
                logger.warning("Git push failed for weekly digest")

        formatted = format_process_report(report)
        try:
            await status_msg.edit_text(formatted)
        except Exception:
            await status_msg.edit_text(formatted, parse_mode=None)
    except Exception:
        logger.exception("Unhandled error in /weekly handler")
        try:
            await status_msg.edit_text("❌ Internal error during weekly digest. Check logs.")
        except Exception:
            pass
