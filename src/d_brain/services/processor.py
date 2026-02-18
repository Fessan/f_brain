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
    create_provider,
)


class LLMProcessor:
    """Facade for daily/weekly/arbitrary processing use cases."""

    def __init__(
        self,
        vault_path: Path,
        todoist_api_key: str = "",
        singularity_api_key: str = "",
        task_backend: str = "singularity",
        provider_name: str = "claude-cli",
        openai_api_key: str = "",
        openai_model: str = "",
        openai_base_url: str = "https://api.openai.com/v1",
        provider: LLMProvider | None = None,
    ) -> None:
        self.vault_path = Path(vault_path)
        self.provider = provider or create_provider(
            self.vault_path,
            provider_name=provider_name,
            todoist_api_key=todoist_api_key,
            singularity_api_key=singularity_api_key,
            openai_api_key=openai_api_key,
            openai_model=openai_model,
            openai_base_url=openai_base_url,
        )

        context_loader = PromptContextLoader(self.vault_path)
        self._daily_use_case = DailyProcessingUseCase(
            vault_path=self.vault_path,
            provider=self.provider,
            context_loader=context_loader,
            task_backend=task_backend,
        )
        self._prompt_use_case = ExecutePromptUseCase(
            vault_path=self.vault_path,
            provider=self.provider,
            context_loader=context_loader,
            task_backend=task_backend,
        )
        self._weekly_use_case = WeeklyDigestUseCase(
            vault_path=self.vault_path,
            provider=self.provider,
            task_backend=task_backend,
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
