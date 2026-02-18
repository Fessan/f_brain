"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str = Field(description="Telegram Bot API token")
    deepgram_api_key: str = Field(description="Deepgram API key for transcription")
    todoist_api_key: str = Field(default="", description="Todoist API key for tasks")
    singularity_api_key: str = Field(default="", description="Singularity API key/token for MCP")
    task_backend: Literal["singularity", "todoist"] = Field(
        default="singularity",
        description="Task backend integration used by agent prompts",
    )
    llm_provider: Literal["openai-cli", "claude-cli", "openai-api"] = Field(
        default="openai-cli",
        description="LLM provider backend",
    )
    openai_api_key: str = Field(default="", description="OpenAI-compatible API key")
    openai_model: str = Field(default="", description="OpenAI-compatible model name")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI-compatible API base URL",
    )
    vault_path: Path = Field(
        default=Path("./vault"),
        description="Path to Obsidian vault directory",
    )
    allowed_user_ids: list[int] = Field(
        default_factory=list,
        description="List of Telegram user IDs allowed to use the bot",
    )
    allow_all_users: bool = Field(
        default=False,
        description="Whether to allow access to all users (security risk!)",
    )

    @property
    def daily_path(self) -> Path:
        """Path to daily notes directory."""
        return self.vault_path / "daily"

    @property
    def attachments_path(self) -> Path:
        """Path to attachments directory."""
        return self.vault_path / "attachments"

    @property
    def thoughts_path(self) -> Path:
        """Path to thoughts directory."""
        return self.vault_path / "thoughts"

    @model_validator(mode="after")
    def validate_llm_config(self) -> "Settings":
        """Validate provider-specific settings."""
        if self.task_backend == "todoist" and not self.todoist_api_key:
            raise ValueError("TASK_BACKEND=todoist requires TODOIST_API_KEY")

        if self.llm_provider == "openai-api":
            missing: list[str] = []
            if not self.openai_api_key:
                missing.append("OPENAI_API_KEY")
            if not self.openai_model:
                missing.append("OPENAI_MODEL")
            if self.task_backend == "singularity":
                missing.append("TASK_BACKEND=todoist (singularity unsupported for openai-api)")
            if missing:
                missing_str = ", ".join(missing)
                raise ValueError(
                    f"LLM_PROVIDER=openai-api requires the following settings: {missing_str}"
                )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached application settings instance."""
    return Settings()
