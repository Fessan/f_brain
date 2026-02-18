"""Local migration verification scenarios that do not require external tokens."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from d_brain.bot.formatters import format_process_report
from d_brain.llm.base import LLMExecutionResult, LLMProvider, LLMProviderError
from d_brain.llm.router import create_provider
from d_brain.llm.use_cases import (
    DailyProcessingUseCase,
    ExecutePromptUseCase,
    PromptContextLoader,
    WeeklyDigestUseCase,
    _daily_tool_instructions,
    _prompt_tool_instructions,
    _weekly_tool_instructions,
)
from d_brain.services.session import SessionStore


class StaticProvider(LLMProvider):
    """Provider test double returning deterministic results."""

    def __init__(
        self,
        *,
        name: str = "openai",
        stdout: str = "",
        stderr: str = "",
        returncode: int = 0,
        meta: dict | None = None,
        exc: Exception | None = None,
    ) -> None:
        self._name = name
        self._stdout = stdout
        self._stderr = stderr
        self._returncode = returncode
        self._meta = meta or {}
        self._exc = exc

    @property
    def name(self) -> str:
        return self._name

    def execute(self, prompt: str, *, timeout: int) -> LLMExecutionResult:
        del prompt
        del timeout
        if self._exc is not None:
            raise self._exc
        return LLMExecutionResult(
            stdout=self._stdout,
            stderr=self._stderr,
            returncode=self._returncode,
            provider=self._name,
            meta=self._meta,
        )


def _prepare_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / "daily").mkdir(parents=True)
    (vault / "MOC").mkdir(parents=True)
    (vault / "summaries").mkdir(parents=True)
    return vault


def test_daily_use_case_propagates_meta_and_tool_failures(tmp_path: Path) -> None:
    vault = _prepare_vault(tmp_path)
    today = date.today()
    (vault / "daily" / f"{today.isoformat()}.md").write_text("entry")

    provider = StaticProvider(
        name="openai",
        stdout="<b>ok</b>",
        meta={"usage": {"prompt_tokens": 11}, "tool_failures": [{"capability": "x"}]},
    )
    use_case = DailyProcessingUseCase(
        vault_path=vault,
        provider=provider,
        context_loader=PromptContextLoader(vault),
    )

    result = use_case.run(today)
    assert result.error is None
    assert result.provider == "openai"
    assert result.processed_entries == 1
    assert result.tool_failures == [{"capability": "x"}]
    assert result.meta["returncode"] == 0
    assert result.meta["usage"]["prompt_tokens"] == 11
    assert "total_seconds" in result.timings


def test_execute_prompt_timeout_returns_structured_error(tmp_path: Path) -> None:
    vault = _prepare_vault(tmp_path)
    provider = StaticProvider(exc=LLMProviderError("Execution timed out"))

    use_case = ExecutePromptUseCase(
        vault_path=vault,
        provider=provider,
        context_loader=PromptContextLoader(vault),
    )
    result = use_case.run("do work", user_id=0)

    assert result.error == "Execution timed out"
    assert result.processed_entries == 0
    assert result.report == ""
    assert "total_seconds" in result.timings


def test_weekly_use_case_saves_summary_and_updates_moc(tmp_path: Path) -> None:
    vault = _prepare_vault(tmp_path)
    (vault / "MOC" / "MOC-weekly.md").write_text("# Weekly\n\n## Previous Weeks\n")
    provider = StaticProvider(
        name="openai",
        stdout="<b>Weekly</b>\n<i>Progress</i>",
    )
    use_case = WeeklyDigestUseCase(vault_path=vault, provider=provider)

    result = use_case.run()
    assert result.error is None
    assert result.processed_entries == 1

    year, week, _ = date.today().isocalendar()
    summary_name = f"{year}-W{week:02d}-summary.md"
    summary_path = vault / "summaries" / summary_name
    assert summary_path.exists()
    summary_text = summary_path.read_text()
    assert "**Weekly**" in summary_text
    assert "*Progress*" in summary_text

    moc_text = (vault / "MOC" / "MOC-weekly.md").read_text()
    assert summary_name in moc_text


def test_invalid_html_report_falls_back_to_plain_text_escape() -> None:
    formatted = format_process_report({"report": "<b>broken<i>"})
    assert formatted == "&lt;b&gt;broken&lt;i&gt;"


def test_session_store_skips_corrupt_jsonl_lines(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir(parents=True)
    store = SessionStore(vault)
    path = store._get_session_file(1)  # noqa: SLF001 - explicit corruption test
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '{"ts":"2026-02-17T12:00:00+00:00","type":"text"}\n'
        "{not json}\n"
        '{"ts":"2026-02-17T13:00:00+00:00","type":"voice"}\n'
    )

    entries = store.get_recent(1)
    assert len(entries) == 2
    assert entries[0]["type"] == "text"
    assert entries[1]["type"] == "voice"


def test_router_validation_errors(monkeypatch, tmp_path: Path) -> None:
    vault = _prepare_vault(tmp_path)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        create_provider(vault, provider_name="openai", openai_model="gpt-4o-mini")

    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        create_provider(vault, provider_name="unknown")

    monkeypatch.setattr("d_brain.llm.router.which", lambda _: None)
    with pytest.raises(ValueError, match="binary is not in PATH"):
        create_provider(vault, provider_name="claude-cli")


def test_provider_specific_tool_instructions_switch() -> None:
    openai_daily = _daily_tool_instructions("openai")
    assert "todoist_user_info" in openai_daily
    assert "mcp__todoist__" not in openai_daily

    claude_prompt = _prompt_tool_instructions("claude-cli")
    assert "mcp__todoist__user-info" in claude_prompt

    openai_weekly = _weekly_tool_instructions("openai")
    assert "todoist_find_completed_tasks" in openai_weekly


def test_handlers_keep_to_thread_for_non_blocking_policy() -> None:
    project_root = Path(__file__).resolve().parent.parent
    files = [
        project_root / "src/d_brain/bot/handlers/process.py",
        project_root / "src/d_brain/bot/handlers/do.py",
        project_root / "src/d_brain/bot/handlers/weekly.py",
    ]
    for file_path in files:
        assert file_path.exists(), f"Handler file not found: {file_path}"
        content = file_path.read_text(encoding="utf-8")
        assert "asyncio.to_thread" in content
