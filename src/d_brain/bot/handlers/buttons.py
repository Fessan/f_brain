"""Button handlers for reply keyboard."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from d_brain.bot.states import DoCommandState
from d_brain.config import get_settings
from d_brain.services.model_provider import (
    get_provider_label,
    set_active_provider,
)

router = Router(name="buttons")


@router.message(F.text == "📊 Статус")
async def btn_status(message: Message) -> None:
    """Handle Status button."""
    from d_brain.bot.handlers.commands import cmd_status

    await cmd_status(message)


@router.message(F.text == "⚙️ Обработать")
async def btn_process(message: Message) -> None:
    """Handle Process button."""
    from d_brain.bot.handlers.process import cmd_process

    await cmd_process(message)


@router.message(F.text == "📅 Неделя")
async def btn_weekly(message: Message) -> None:
    """Handle Weekly button."""
    from d_brain.bot.handlers.weekly import cmd_weekly

    await cmd_weekly(message)


@router.message(F.text == "✨ Запрос")
async def btn_do(message: Message, state: FSMContext) -> None:
    """Handle Do button - set state and wait for input."""
    await state.set_state(DoCommandState.waiting_for_input)
    await message.answer(
        "🎯 <b>Что сделать?</b>\n\n"
        "Отправь голосовое или текстовое сообщение с запросом."
    )


@router.message(F.text == "❓ Помощь")
async def btn_help(message: Message) -> None:
    """Handle Help button."""
    from d_brain.bot.handlers.commands import cmd_help

    await cmd_help(message)


@router.message(F.text == "🤖 GPT")
async def btn_select_gpt(message: Message) -> None:
    """Switch active model to GPT CLI."""
    settings = get_settings()
    set_active_provider("openai-cli")
    await message.answer(
        f"✅ Активная модель: <b>{get_provider_label('openai-cli')}</b>\n"
        f"Базовая из .env: <i>{get_provider_label(settings.llm_provider)}</i>"
    )


@router.message(F.text == "🧠 Claude")
async def btn_select_claude(message: Message) -> None:
    """Switch active model to Claude CLI."""
    settings = get_settings()
    set_active_provider("claude-cli")
    await message.answer(
        f"✅ Активная модель: <b>{get_provider_label('claude-cli')}</b>\n"
        f"Базовая из .env: <i>{get_provider_label(settings.llm_provider)}</i>"
    )
