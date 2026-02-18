"""OpenAI Codex CLI adapter for LLMProvider interface."""

import os
import subprocess
from pathlib import Path

from d_brain.llm.base import LLMExecutionResult, LLMProvider, LLMProviderError


class CodexCLIProvider(LLMProvider):
    """Provider that executes prompts via OpenAI Codex CLI (``codex exec``)."""

    def __init__(
        self,
        *,
        workdir: Path,
        todoist_api_key: str = "",
    ) -> None:
        self.workdir = Path(workdir)
        self.todoist_api_key = todoist_api_key

    @property
    def name(self) -> str:
        return "openai-cli"

    def execute(self, prompt: str, *, timeout: int) -> LLMExecutionResult:
        """Run a prompt through Codex CLI and return raw output."""
        env = os.environ.copy()
        if self.todoist_api_key:
            env["TODOIST_API_KEY"] = self.todoist_api_key

        try:
            result = subprocess.run(
                [
                    "codex",
                    "exec",
                    "--ask-for-approval",
                    "never",
                    "--sandbox",
                    "workspace-write",
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
            raise LLMProviderError("Codex CLI not installed") from exc
        except Exception as exc:  # pragma: no cover - defensive wrapper
            raise LLMProviderError(str(exc)) from exc
