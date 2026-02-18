"""Claude CLI adapter for LLMProvider interface."""

import os
import subprocess
from pathlib import Path

from d_brain.llm.base import LLMExecutionResult, LLMProvider, LLMProviderError


class ClaudeCLIProvider(LLMProvider):
    """Provider that executes prompts via claude CLI."""

    def __init__(
        self,
        *,
        workdir: Path,
        mcp_config_path: Path,
        todoist_api_key: str = "",
        singularity_api_key: str = "",
    ) -> None:
        self.workdir = Path(workdir)
        self.mcp_config_path = Path(mcp_config_path)
        self.todoist_api_key = todoist_api_key
        self.singularity_api_key = singularity_api_key

    @property
    def name(self) -> str:
        return "claude-cli"

    def execute(self, prompt: str, *, timeout: int) -> LLMExecutionResult:
        """Run a prompt through Claude CLI and return raw output."""
        if not self.mcp_config_path.exists():
            raise LLMProviderError(f"MCP config not found: {self.mcp_config_path}")

        env = os.environ.copy()
        if self.todoist_api_key:
            env["TODOIST_API_KEY"] = self.todoist_api_key
        if self.singularity_api_key:
            env["SINGULARITY_API_KEY"] = self.singularity_api_key

        try:
            result = subprocess.run(
                [
                    "claude",
                    "--print",
                    "--dangerously-skip-permissions",
                    "--mcp-config",
                    str(self.mcp_config_path),
                    "-p",
                    prompt,
                ],
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=env,
            )
            return LLMExecutionResult(
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
                provider=self.name,
            )
        except subprocess.TimeoutExpired as exc:
            raise LLMProviderError("Execution timed out") from exc
        except FileNotFoundError as exc:
            raise LLMProviderError("Claude CLI not installed") from exc
        except Exception as exc:  # pragma: no cover - defensive wrapper
            raise LLMProviderError(str(exc)) from exc
