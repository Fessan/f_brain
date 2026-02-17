"""Canonical tool capability contract for provider parity."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class CapabilitySpec:
    """Capability schema contract shared across providers."""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    parity_required: bool = True


@dataclass(slots=True)
class ToolExecutionError:
    """Structured tool execution failure payload."""

    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolExecutionResult:
    """Result envelope for capability execution."""

    capability: str
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: ToolExecutionError | None = None


class ToolRuntime(ABC):
    """Runtime executor for canonical capabilities."""

    @abstractmethod
    def execute(self, capability: str, payload: dict[str, Any]) -> ToolExecutionResult:
        """Execute capability call and return structured result."""


def build_capability_registry() -> dict[str, CapabilitySpec]:
    """Define canonical capability contracts for Todoist and Vault."""
    return {
        "todoist.user_info": CapabilitySpec(
            name="todoist.user_info",
            description="Get current Todoist user profile.",
            input_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            output_schema={
                "type": "object",
                "properties": {
                    "userId": {"type": "string"},
                    "email": {"type": "string"},
                    "name": {"type": "string"},
                },
                "required": ["userId", "name"],
            },
        ),
        "todoist.add_tasks": CapabilitySpec(
            name="todoist.add_tasks",
            description="Create one or many Todoist tasks.",
            input_schema={
                "type": "object",
                "properties": {
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "description": {"type": "string"},
                                "dueString": {"type": "string"},
                                "priority": {"type": "integer"},
                                "projectId": {"type": "string"},
                            },
                            "required": ["content"],
                        },
                    }
                },
                "required": ["tasks"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "created": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "content": {"type": "string"},
                            },
                            "required": ["id", "content"],
                        },
                    }
                },
                "required": ["created"],
            },
        ),
        "todoist.find_completed_tasks": CapabilitySpec(
            name="todoist.find_completed_tasks",
            description="Find completed tasks in Todoist.",
            input_schema={
                "type": "object",
                "properties": {
                    "since": {"type": "string"},
                    "until": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "content": {"type": "string"},
                                "completedAt": {"type": "string"},
                            },
                            "required": ["id", "content"],
                        },
                    }
                },
                "required": ["tasks"],
            },
        ),
        "vault.read_file": CapabilitySpec(
            name="vault.read_file",
            description="Read text file from vault path.",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "exists": {"type": "boolean"},
                    "content": {"type": "string"},
                },
                "required": ["path", "exists", "content"],
            },
        ),
        "vault.write_file": CapabilitySpec(
            name="vault.write_file",
            description="Write or append text to a vault file.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "mode": {"type": "string", "enum": ["overwrite", "append"]},
                },
                "required": ["path", "content"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "writtenBytes": {"type": "integer"},
                },
                "required": ["path", "writtenBytes"],
            },
        ),
        "vault.list_files": CapabilitySpec(
            name="vault.list_files",
            description="List files in a vault directory by optional pattern.",
            input_schema={
                "type": "object",
                "properties": {
                    "dir": {"type": "string"},
                    "pattern": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "files": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["files"],
            },
        ),
    }
