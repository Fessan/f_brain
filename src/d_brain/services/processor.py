"""High-level processor facade built on provider/use-case architecture."""

from datetime import date
from pathlib import Path
from typing import Any

from d_brain.llm import (
    DailyProcessingUseCase,
    ExecutePromptUseCase,
    LLMProvider,
    LLMResponseEnvelope,
    PromptContextLoader,
    WeeklyDigestUseCase,
    create_default_provider,
)


class LLMProcessor:
    """Facade for daily/weekly/arbitrary processing use cases."""

    def __init__(
        self,
        vault_path: Path,
        todoist_api_key: str = "",
        provider: LLMProvider | None = None,
    ) -> None:
        self.vault_path = Path(vault_path)
        self.provider = provider or create_default_provider(
            self.vault_path,
            todoist_api_key=todoist_api_key,
        )

        context_loader = PromptContextLoader(self.vault_path)
        self._daily_use_case = DailyProcessingUseCase(
            vault_path=self.vault_path,
            provider=self.provider,
            context_loader=context_loader,
        )
        self._prompt_use_case = ExecutePromptUseCase(
            vault_path=self.vault_path,
            provider=self.provider,
            context_loader=context_loader,
        )
        self._weekly_use_case = WeeklyDigestUseCase(
            vault_path=self.vault_path,
            provider=self.provider,
        )

    def process_daily_result(self, day: date | None = None) -> LLMResponseEnvelope:
        """Process daily notes and return typed envelope."""
        return self._daily_use_case.run(day)

    def process_daily(self, day: date | None = None) -> dict[str, Any]:
        """Process daily notes (legacy dict format)."""
        return self.process_daily_result(day).to_legacy_dict()

    def execute_prompt_result(self, user_prompt: str, user_id: int = 0) -> LLMResponseEnvelope:
        """Execute arbitrary user request and return typed envelope."""
        return self._prompt_use_case.run(user_prompt, user_id=user_id)

    def execute_prompt(self, user_prompt: str, user_id: int = 0) -> dict[str, Any]:
        """Execute arbitrary user request (legacy dict format)."""
        return self.execute_prompt_result(user_prompt, user_id=user_id).to_legacy_dict()

    def generate_weekly_result(self) -> LLMResponseEnvelope:
        """Generate weekly digest and return typed envelope."""
        return self._weekly_use_case.run()

    def generate_weekly(self) -> dict[str, Any]:
        """Generate weekly digest (legacy dict format)."""
        return self.generate_weekly_result().to_legacy_dict()


class ClaudeProcessor(LLMProcessor):
    """Backward-compatible name for existing imports."""
