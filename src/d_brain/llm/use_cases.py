"""High-level use cases built on top of low-level LLM providers."""

import logging
import time
from datetime import date
from pathlib import Path

from d_brain.llm.base import LLMProvider, LLMProviderError, LLMResponseEnvelope
from d_brain.services.session import SessionStore

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 1200  # 20 minutes


def _daily_tool_instructions(provider_name: str) -> str:
    if provider_name == "openai-api":
        return """ПЕРВЫМ ДЕЛОМ: вызови todoist_user_info чтобы проверить доступ к инструментам.

CRITICAL TOOL RULE:
- Ты имеешь доступ к tools: todoist_user_info, todoist_add_tasks, todoist_find_completed_tasks, vault_read_file, vault_write_file, vault_list_files.
- ВЫЗЫВАЙ tools напрямую.
- НИКОГДА не пиши "MCP недоступен" или "добавь вручную".
- Для задач: вызови todoist_add_tasks.
- Если tool вернул ошибку — покажи ТОЧНУЮ ошибку в отчёте."""

    return """ПЕРВЫМ ДЕЛОМ: вызови mcp__todoist__user-info чтобы убедиться что MCP работает.

CRITICAL MCP RULE:
- ТЫ ИМЕЕШЬ ДОСТУП к mcp__todoist__* tools — ВЫЗЫВАЙ ИХ НАПРЯМУЮ.
- НИКОГДА не пиши "MCP недоступен" или "добавь вручную".
- Для задач: вызови mcp__todoist__add-tasks tool.
- Если tool вернул ошибку — покажи ТОЧНУЮ ошибку в отчёте."""


def _prompt_tool_instructions(provider_name: str) -> str:
    if provider_name == "openai-api":
        return """ПЕРВЫМ ДЕЛОМ: вызови todoist_user_info чтобы проверить доступ к инструментам.

CRITICAL TOOL RULE:
- Ты имеешь доступ к tools: todoist_user_info, todoist_add_tasks, todoist_find_completed_tasks, vault_read_file, vault_write_file, vault_list_files.
- ВЫЗЫВАЙ tools напрямую.
- НИКОГДА не пиши "MCP недоступен" или "добавь вручную".
- Если tool вернул ошибку — покажи ТОЧНУЮ ошибку в отчёте."""

    return """ПЕРВЫМ ДЕЛОМ: вызови mcp__todoist__user-info чтобы убедиться что MCP работает.

CRITICAL MCP RULE:
- ТЫ ИМЕЕШЬ ДОСТУП к mcp__todoist__* tools — ВЫЗЫВАЙ ИХ НАПРЯМУЮ.
- НИКОГДА не пиши "MCP недоступен" или "добавь вручную".
- Если tool вернул ошибку — покажи ТОЧНУЮ ошибку в отчёте."""


def _weekly_tool_instructions(provider_name: str) -> str:
    if provider_name == "openai-api":
        return """ПЕРВЫМ ДЕЛОМ: вызови todoist_user_info чтобы проверить доступ к инструментам.

CRITICAL TOOL RULE:
- Ты имеешь доступ к tools: todoist_user_info, todoist_add_tasks, todoist_find_completed_tasks, vault_read_file, vault_write_file, vault_list_files.
- ВЫЗЫВАЙ tools напрямую.
- НИКОГДА не пиши "MCP недоступен" или "добавь вручную".
- Для выполненных задач: вызови todoist_find_completed_tasks.
- Если tool вернул ошибку — покажи ТОЧНУЮ ошибку в отчёте."""

    return """ПЕРВЫМ ДЕЛОМ: вызови mcp__todoist__user-info чтобы убедиться что MCP работает.

CRITICAL MCP RULE:
- ТЫ ИМЕЕШЬ ДОСТУП к mcp__todoist__* tools — ВЫЗЫВАЙ ИХ НАПРЯМУЮ.
- НИКОГДА не пиши "MCP недоступен" или "добавь вручную".
- Для выполненных задач: вызови mcp__todoist__find-completed-tasks tool.
- Если tool вернул ошибку — покажи ТОЧНУЮ ошибку в отчёте."""


class PromptContextLoader:
    """Loads context files and session snippets for prompts."""

    def __init__(self, vault_path: Path) -> None:
        self.vault_path = Path(vault_path)

    def load_skill_content(self) -> str:
        """Load dbrain-processor skill content if present."""
        skill_path = self.vault_path / ".claude/skills/dbrain-processor/SKILL.md"
        if skill_path.exists():
            return skill_path.read_text(encoding="utf-8")
        return ""

    def load_todoist_reference(self) -> str:
        """Load Todoist reference file if present."""
        ref_path = self.vault_path / ".claude/skills/dbrain-processor/references/todoist.md"
        if ref_path.exists():
            return ref_path.read_text(encoding="utf-8")
        return ""

    def get_session_context(self, user_id: int) -> str:
        """Get today's session context for prompt enrichment."""
        if user_id == 0:
            return ""

        session = SessionStore(self.vault_path)
        today_entries = session.get_today(user_id)
        if not today_entries:
            return ""

        lines = ["=== TODAY'S SESSION ==="]
        for entry in today_entries[-10:]:
            ts = entry.get("ts", "")[11:16]
            entry_type = entry.get("type", "unknown")
            text = entry.get("text", "")[:80]
            if text:
                lines.append(f"{ts} [{entry_type}] {text}")
        lines.append("=== END SESSION ===\n")
        return "\n".join(lines)


class DailyProcessingUseCase:
    """Daily processing orchestration."""

    def __init__(
        self,
        *,
        vault_path: Path,
        provider: LLMProvider,
        context_loader: PromptContextLoader,
    ) -> None:
        self.vault_path = Path(vault_path)
        self.provider = provider
        self.context_loader = context_loader

    def run(self, day: date | None = None) -> LLMResponseEnvelope:
        started_at = time.monotonic()
        if day is None:
            day = date.today()

        daily_file = self.vault_path / "daily" / f"{day.isoformat()}.md"
        if not daily_file.exists():
            logger.warning("No daily file for %s", day)
            return LLMResponseEnvelope(
                error=f"No daily file for {day}",
                processed_entries=0,
                provider=self.provider.name,
                timings={"total_seconds": round(time.monotonic() - started_at, 3)},
            )

        prompt = f"""Сегодня {day}. Выполни ежедневную обработку.

=== SKILL INSTRUCTIONS ===
{self.context_loader.load_skill_content()}
=== END SKILL ===

{_daily_tool_instructions(self.provider.name)}

CRITICAL OUTPUT FORMAT:
- Return ONLY raw HTML for Telegram (parse_mode=HTML)
- NO markdown: no **, no ## , no ```, no tables
- Start directly with 📊 <b>Обработка за {day}</b>
- Allowed tags: <b>, <i>, <code>, <s>, <u>
- If entries already processed, return status report in same HTML format"""

        try:
            result = self.provider.execute(prompt, timeout=DEFAULT_TIMEOUT)
        except LLMProviderError as exc:
            logger.error("Daily processing execution error: %s", exc)
            return LLMResponseEnvelope(
                error=str(exc),
                processed_entries=0,
                provider=self.provider.name,
                timings={"total_seconds": round(time.monotonic() - started_at, 3)},
            )

        if result.returncode != 0:
            logger.error("Daily processing failed: %s", result.stderr)
            return LLMResponseEnvelope(
                error=result.stderr or "Daily processing failed",
                processed_entries=0,
                provider=result.provider,
                meta={
                    "returncode": result.returncode,
                    **result.meta,
                },
                timings={"total_seconds": round(time.monotonic() - started_at, 3)},
            )

        return LLMResponseEnvelope(
            report=result.stdout.strip(),
            processed_entries=1,
            provider=result.provider,
            tool_failures=list(result.meta.get("tool_failures", [])),
            meta={
                "returncode": result.returncode,
                **result.meta,
            },
            timings={"total_seconds": round(time.monotonic() - started_at, 3)},
        )


class ExecutePromptUseCase:
    """Arbitrary user prompt execution orchestration."""

    def __init__(
        self,
        *,
        vault_path: Path,
        provider: LLMProvider,
        context_loader: PromptContextLoader,
    ) -> None:
        self.vault_path = Path(vault_path)
        self.provider = provider
        self.context_loader = context_loader

    def run(self, user_prompt: str, user_id: int = 0) -> LLMResponseEnvelope:
        started_at = time.monotonic()
        today = date.today()
        session_context = self.context_loader.get_session_context(user_id)
        todoist_reference = self.context_loader.load_todoist_reference()

        prompt = f"""Ты - персональный ассистент d-brain.

CONTEXT:
- Текущая дата: {today}
- Vault path: {self.vault_path}

{session_context}=== TODOIST REFERENCE ===
{todoist_reference}
=== END REFERENCE ===

{_prompt_tool_instructions(self.provider.name)}

USER REQUEST:
{user_prompt}

CRITICAL OUTPUT FORMAT:
- Return ONLY raw HTML for Telegram (parse_mode=HTML)
- NO markdown: no **, no ##, no ```, no tables, no -
- Start with emoji and <b>header</b>
- Allowed tags: <b>, <i>, <code>, <s>, <u>
- Be concise - Telegram has 4096 char limit

EXECUTION:
1. Analyze the request
2. Call available Todoist/Vault tools directly
3. Return HTML status report with results"""

        try:
            result = self.provider.execute(prompt, timeout=DEFAULT_TIMEOUT)
        except LLMProviderError as exc:
            logger.error("Prompt execution error: %s", exc)
            return LLMResponseEnvelope(
                error=str(exc),
                processed_entries=0,
                provider=self.provider.name,
                timings={"total_seconds": round(time.monotonic() - started_at, 3)},
            )

        if result.returncode != 0:
            logger.error("Prompt execution failed: %s", result.stderr)
            return LLMResponseEnvelope(
                error=result.stderr or "Prompt execution failed",
                processed_entries=0,
                provider=result.provider,
                meta={
                    "returncode": result.returncode,
                    **result.meta,
                },
                timings={"total_seconds": round(time.monotonic() - started_at, 3)},
            )

        return LLMResponseEnvelope(
            report=result.stdout.strip(),
            processed_entries=1,
            provider=result.provider,
            tool_failures=list(result.meta.get("tool_failures", [])),
            meta={
                "returncode": result.returncode,
                **result.meta,
            },
            timings={"total_seconds": round(time.monotonic() - started_at, 3)},
        )


class WeeklyDigestUseCase:
    """Weekly digest orchestration."""

    def __init__(
        self,
        *,
        vault_path: Path,
        provider: LLMProvider,
    ) -> None:
        self.vault_path = Path(vault_path)
        self.provider = provider

    def _html_to_markdown(self, value: str) -> str:
        """Convert Telegram HTML to Obsidian markdown."""
        import re

        flags = re.DOTALL
        text = value
        text = re.sub(r"<b>(.*?)</b>", r"**\1**", text, flags=flags)
        text = re.sub(r"<i>(.*?)</i>", r"*\1*", text, flags=flags)
        text = re.sub(r"<code>(.*?)</code>", r"`\1`", text, flags=flags)
        text = re.sub(r"<s>(.*?)</s>", r"~~\1~~", text, flags=flags)
        text = re.sub(r"</?u>", "", text)
        text = re.sub(r'<a href="([^"]+)">([^<]+)</a>', r"[\2](\1)", text)
        return text

    def _save_weekly_summary(self, report_html: str, week_date: date) -> Path:
        """Save weekly summary to vault/summaries/YYYY-WXX-summary.md."""
        year, week, _ = week_date.isocalendar()
        filename = f"{year}-W{week:02d}-summary.md"
        summary_path = self.vault_path / "summaries" / filename

        content = self._html_to_markdown(report_html)
        frontmatter = f"""---
date: {week_date.isoformat()}
type: weekly-summary
week: {year}-W{week:02d}
---

"""
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(frontmatter + content, encoding="utf-8")
        logger.info("Weekly summary saved to %s", summary_path)
        return summary_path

    def _update_weekly_moc(self, summary_path: Path) -> None:
        """Append summary link to MOC-weekly.md."""
        moc_path = self.vault_path / "MOC" / "MOC-weekly.md"
        if not moc_path.exists():
            return

        content = moc_path.read_text(encoding="utf-8")
        link = f"- [[summaries/{summary_path.name}|{summary_path.stem}]]"
        if summary_path.stem in content:
            return

        marker = "## Previous Weeks\n"
        if marker in content:
            content = content.replace(marker, f"{marker}\n{link}\n")
        else:
            content = content.rstrip() + f"\n\n{link}\n"
        moc_path.write_text(content, encoding="utf-8")
        logger.info("Updated MOC-weekly.md with link to %s", summary_path.stem)

    def run(self) -> LLMResponseEnvelope:
        started_at = time.monotonic()
        today = date.today()
        prompt = f"""Сегодня {today}. Сгенерируй недельный дайджест.

{_weekly_tool_instructions(self.provider.name)}

WORKFLOW:
1. Собери данные за неделю (daily файлы в vault/daily/, completed tasks через доступные tools)
2. Проанализируй прогресс по целям (goals/3-weekly.md)
3. Определи победы и вызовы
4. Сгенерируй HTML отчёт

CRITICAL OUTPUT FORMAT:
- Return ONLY raw HTML for Telegram (parse_mode=HTML)
- NO markdown: no **, no ##, no ```, no tables
- Start with 📅 <b>Недельный дайджест</b>
- Allowed tags: <b>, <i>, <code>, <s>, <u>
- Be concise - Telegram has 4096 char limit"""

        try:
            result = self.provider.execute(prompt, timeout=DEFAULT_TIMEOUT)
        except LLMProviderError as exc:
            logger.error("Weekly digest execution error: %s", exc)
            return LLMResponseEnvelope(
                error=str(exc),
                processed_entries=0,
                provider=self.provider.name,
                timings={"total_seconds": round(time.monotonic() - started_at, 3)},
            )

        if result.returncode != 0:
            logger.error("Weekly digest failed: %s", result.stderr)
            return LLMResponseEnvelope(
                error=result.stderr or "Weekly digest failed",
                processed_entries=0,
                provider=result.provider,
                meta={
                    "returncode": result.returncode,
                    **result.meta,
                },
                timings={"total_seconds": round(time.monotonic() - started_at, 3)},
            )

        output = result.stdout.strip()
        try:
            summary_path = self._save_weekly_summary(output, today)
            self._update_weekly_moc(summary_path)
        except Exception as exc:
            logger.warning("Failed to save weekly summary: %s", exc)

        return LLMResponseEnvelope(
            report=output,
            processed_entries=1,
            provider=result.provider,
            tool_failures=list(result.meta.get("tool_failures", [])),
            meta={
                "returncode": result.returncode,
                **result.meta,
            },
            timings={"total_seconds": round(time.monotonic() - started_at, 3)},
        )
