"""Process command handler."""

import asyncio
import logging
from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from d_brain.bot.formatters import format_process_report
from d_brain.config import get_settings
from d_brain.services.git import VaultGit
from d_brain.services.model_provider import get_active_provider
from d_brain.services.processor import ClaudeProcessor

router = Router(name="process")
logger = logging.getLogger(__name__)

MAX_WAIT_SECONDS = 1500  # slightly above provider timeout (1200s)


@router.message(Command("process"))
async def cmd_process(message: Message) -> None:
    """Handle /process command - trigger Claude processing."""
    user_id = message.from_user.id if message.from_user else 0
    logger.info("Process command triggered by user %s", user_id)

    status_msg = await message.answer("⏳ Processing... (may take up to 10 min)")

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

        # Run subprocess in thread to avoid blocking event loop
        async def process_with_progress() -> dict:
            task = asyncio.create_task(
                asyncio.to_thread(processor.process_daily, date.today())
            )

            elapsed = 0
            while not task.done() and elapsed < MAX_WAIT_SECONDS:
                await asyncio.sleep(30)
                elapsed += 30
                if not task.done():
                    try:
                        await status_msg.edit_text(
                            f"⏳ Processing... ({elapsed // 60}m {elapsed % 60}s)"
                        )
                    except Exception:
                        pass  # Ignore edit errors

            if not task.done():
                task.cancel()
                return {"error": "Processing timed out"}

            return await task

        report = await process_with_progress()

        # Commit and push changes
        if "error" not in report:
            today = date.today().isoformat()
            pushed = await asyncio.to_thread(git.commit_and_push, f"chore: process daily {today}")
            if not pushed:
                logger.warning("Git push failed for daily processing")

        # Format and send report
        formatted = format_process_report(report)
        try:
            await status_msg.edit_text(formatted)
        except Exception:
            # Fallback: send without HTML parsing
            await status_msg.edit_text(formatted, parse_mode=None)
    except Exception:
        logger.exception("Unhandled error in /process handler")
        try:
            await status_msg.edit_text("❌ Internal error during processing. Check logs.")
        except Exception:
            pass
