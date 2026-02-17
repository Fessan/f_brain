"""Provider factory functions."""

from pathlib import Path

from d_brain.llm.base import LLMProvider
from d_brain.llm.claude_cli import ClaudeCLIProvider


def create_default_provider(vault_path: Path, todoist_api_key: str = "") -> LLMProvider:
    """Create default provider for current runtime.

    For now default is Claude CLI to preserve existing behavior.
    """
    resolved_vault = Path(vault_path)
    return ClaudeCLIProvider(
        workdir=resolved_vault.parent,
        mcp_config_path=(resolved_vault.parent / "mcp-config.json").resolve(),
        todoist_api_key=todoist_api_key,
    )
