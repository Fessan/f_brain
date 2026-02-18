"""Core LLM abstractions and shared data models."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class LLMProviderError(Exception):
    """Raised when provider execution cannot be completed."""


@dataclass(slots=True)
class LLMExecutionResult:
    """Raw provider execution output."""

    stdout: str
    stderr: str
    returncode: int
    provider: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LLMResponseEnvelope:
    """Structured response shared by processor use-cases."""

    report: str = ""
    error: str | None = None
    processed_entries: int = 0
    provider: str = ""
    tool_failures: list[dict[str, Any]] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    timings: dict[str, float] = field(default_factory=dict)

    def to_legacy_dict(self) -> dict[str, Any]:
        """Compatibility payload for existing handlers and formatters."""
        payload: dict[str, Any] = {"processed_entries": self.processed_entries}
        if self.error is not None:
            payload["error"] = self.error
            return payload
        payload["report"] = self.report
        if self.tool_failures:
            payload["tool_failures"] = self.tool_failures
        return payload


class LLMProvider(ABC):
    """Low-level provider interface (transport + execution)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def execute(self, prompt: str, *, timeout: int) -> LLMExecutionResult:
        """Execute a prompt and return raw provider result."""
