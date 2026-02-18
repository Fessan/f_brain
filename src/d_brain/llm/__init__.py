"""LLM routing and provider abstraction layer."""

from d_brain.llm.base import (
    LLMExecutionResult,
    LLMProvider,
    LLMProviderError,
    LLMResponseEnvelope,
)
from d_brain.llm.claude_cli import ClaudeCLIProvider
from d_brain.llm.openai_api import OpenAIProvider
from d_brain.llm.runtime import DefaultToolRuntime
from d_brain.llm.router import create_default_provider, create_provider
from d_brain.llm.use_cases import (
    DailyProcessingUseCase,
    ExecutePromptUseCase,
    PromptContextLoader,
    WeeklyDigestUseCase,
)
from d_brain.llm.tools import (
    CapabilitySpec,
    ToolExecutionError,
    ToolExecutionResult,
    ToolRuntime,
    build_capability_registry,
)

__all__ = [
    "ClaudeCLIProvider",
    "DailyProcessingUseCase",
    "ExecutePromptUseCase",
    "LLMExecutionResult",
    "LLMProvider",
    "LLMProviderError",
    "LLMResponseEnvelope",
    "OpenAIProvider",
    "DefaultToolRuntime",
    "PromptContextLoader",
    "CapabilitySpec",
    "ToolExecutionError",
    "ToolExecutionResult",
    "ToolRuntime",
    "create_provider",
    "WeeklyDigestUseCase",
    "build_capability_registry",
    "create_default_provider",
]
