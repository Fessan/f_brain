"""Provider factory functions."""

from pathlib import Path
from shutil import which

from d_brain.llm.base import LLMProvider
from d_brain.llm.claude_cli import ClaudeCLIProvider
from d_brain.llm.codex_cli import CodexCLIProvider
from d_brain.llm.openai_api import OpenAIProvider
from d_brain.llm.runtime import DefaultToolRuntime
from d_brain.llm.tools import build_capability_registry


def create_provider(
    vault_path: Path,
    *,
    provider_name: str = "openai-cli",
    todoist_api_key: str = "",
    openai_api_key: str = "",
    openai_model: str = "",
    openai_base_url: str = "https://api.openai.com/v1",
) -> LLMProvider:
    """Create provider instance from configuration.

    Raises:
        ValueError: if provider config is invalid.
    """
    resolved_vault = Path(vault_path)

    if provider_name == "openai-cli":
        if which("codex") is None:
            raise ValueError("LLM provider 'openai-cli' selected but 'codex' binary is not in PATH")
        return CodexCLIProvider(
            workdir=resolved_vault.parent,
            todoist_api_key=todoist_api_key,
        )

    if provider_name == "claude-cli":
        if which("claude") is None:
            raise ValueError("LLM provider 'claude-cli' selected but 'claude' binary is not in PATH")
        return ClaudeCLIProvider(
            workdir=resolved_vault.parent,
            mcp_config_path=(resolved_vault.parent / "mcp-config.json").resolve(),
            todoist_api_key=todoist_api_key,
        )

    if provider_name == "openai-api":
        if not openai_api_key:
            raise ValueError("LLM provider 'openai-api' requires OPENAI_API_KEY")
        if not openai_model:
            raise ValueError("LLM provider 'openai-api' requires OPENAI_MODEL")

        capability_registry = build_capability_registry()
        tool_runtime = DefaultToolRuntime(
            vault_path=resolved_vault,
            todoist_api_key=todoist_api_key,
        )
        return OpenAIProvider(
            api_key=openai_api_key,
            model=openai_model,
            base_url=openai_base_url,
            tool_runtime=tool_runtime,
            capability_registry=capability_registry,
        )

    raise ValueError(f"Unsupported LLM provider: {provider_name}")


def create_default_provider(vault_path: Path, todoist_api_key: str = "") -> LLMProvider:
    """Backward-compatible default provider creation."""
    return create_provider(
        vault_path,
        provider_name="openai-cli",
        todoist_api_key=todoist_api_key,
    )
