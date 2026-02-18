"""OpenAI-compatible provider adapter."""

import json
from typing import Any

from d_brain.llm.base import LLMExecutionResult, LLMProvider, LLMProviderError
from d_brain.llm.tools import CapabilitySpec, ToolRuntime


class OpenAIProvider(LLMProvider):
    """Provider using OpenAI-compatible Chat Completions API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        tool_runtime: ToolRuntime | None = None,
        capability_registry: dict[str, CapabilitySpec] | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.tool_runtime = tool_runtime
        self.capability_registry = capability_registry or {}
        self.tool_name_to_capability = {
            self._capability_to_tool_name(name): name for name in self.capability_registry
        }

    @property
    def name(self) -> str:
        return "openai"

    def execute(self, prompt: str, *, timeout: int) -> LLMExecutionResult:
        """Execute prompt via OpenAI-compatible API."""
        if not self.api_key:
            raise LLMProviderError("OpenAI API key is required")
        if not self.model:
            raise LLMProviderError("OpenAI model is required")

        endpoint = f"{self.base_url}/chat/completions"
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            import httpx
        except ModuleNotFoundError as exc:  # pragma: no cover - env-dependent
            raise LLMProviderError("httpx is required for OpenAI provider execution") from exc

        tools = self._build_openai_tools()
        tool_failures: list[dict[str, Any]] = []

        with httpx.Client(timeout=timeout) as client:
            for _ in range(8):
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0,
                }
                if tools:
                    payload["tools"] = tools
                    payload["tool_choice"] = "auto"

                try:
                    response = client.post(endpoint, headers=headers, json=payload)
                except httpx.TimeoutException as exc:
                    raise LLMProviderError("OpenAI request timed out") from exc
                except httpx.HTTPError as exc:
                    raise LLMProviderError(f"OpenAI transport error: {exc}") from exc

                if response.status_code >= 400:
                    body = response.text[:500]
                    raise LLMProviderError(f"OpenAI API error {response.status_code}: {body}")

                try:
                    data = response.json()
                except json.JSONDecodeError as exc:
                    raise LLMProviderError("OpenAI response is not valid JSON") from exc

                try:
                    message = data["choices"][0]["message"]
                except (KeyError, IndexError, TypeError) as exc:
                    raise LLMProviderError("OpenAI response missing message payload") from exc

                if message.get("tool_calls"):
                    messages.append(
                        {
                            "role": "assistant",
                            "content": message.get("content"),
                            "tool_calls": message["tool_calls"],
                        }
                    )

                    for tool_call in message["tool_calls"]:
                        call_name = tool_call.get("function", {}).get("name", "")
                        call_args_raw = tool_call.get("function", {}).get("arguments", "{}")
                        capability = self.tool_name_to_capability.get(call_name, "")

                        try:
                            call_args = json.loads(call_args_raw) if call_args_raw else {}
                            if not isinstance(call_args, dict):
                                raise ValueError("tool arguments must be JSON object")
                        except Exception as exc:
                            tool_output = {
                                "ok": False,
                                "error": {
                                    "code": "invalid_tool_arguments",
                                    "message": str(exc),
                                    "retryable": False,
                                },
                            }
                            tool_failures.append(
                                {"capability": capability or call_name, "error": tool_output["error"]}
                            )
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.get("id", ""),
                                    "name": call_name,
                                    "content": json.dumps(tool_output, ensure_ascii=False),
                                }
                            )
                            continue

                        if not capability or self.tool_runtime is None:
                            tool_output = {
                                "ok": False,
                                "error": {
                                    "code": "unsupported_capability",
                                    "message": f"Unsupported tool: {call_name}",
                                    "retryable": False,
                                },
                            }
                            tool_failures.append(
                                {"capability": capability or call_name, "error": tool_output["error"]}
                            )
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.get("id", ""),
                                    "name": call_name,
                                    "content": json.dumps(tool_output, ensure_ascii=False),
                                }
                            )
                            continue

                        tool_result = self.tool_runtime.execute(capability, call_args)
                        if not tool_result.ok and tool_result.error is not None:
                            tool_failures.append(
                                {
                                    "capability": capability,
                                    "error": {
                                        "code": tool_result.error.code,
                                        "message": tool_result.error.message,
                                        "retryable": tool_result.error.retryable,
                                        "details": tool_result.error.details,
                                    },
                                }
                            )

                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.get("id", ""),
                                "name": call_name,
                                "content": json.dumps(
                                    {
                                        "ok": tool_result.ok,
                                        "data": tool_result.data,
                                        "error": None
                                        if tool_result.error is None
                                        else {
                                            "code": tool_result.error.code,
                                            "message": tool_result.error.message,
                                            "retryable": tool_result.error.retryable,
                                            "details": tool_result.error.details,
                                        },
                                    },
                                    ensure_ascii=False,
                                ),
                            }
                        )
                    continue

                content = message.get("content", "")
                if not isinstance(content, str):
                    content = str(content)

                return LLMExecutionResult(
                    stdout=content,
                    stderr="",
                    returncode=0,
                    provider=self.name,
                    meta={
                        "model": self.model,
                        "id": data.get("id", ""),
                        "usage": data.get("usage", {}),
                        "tool_failures": tool_failures,
                    },
                )

        raise LLMProviderError("OpenAI tool loop exceeded maximum iterations")

    def _build_openai_tools(self) -> list[dict[str, Any]]:
        """Build OpenAI function-tool definitions from capability registry."""
        tools: list[dict[str, Any]] = []
        for capability, spec in self.capability_registry.items():
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": self._capability_to_tool_name(capability),
                        "description": spec.description,
                        "parameters": spec.input_schema,
                    },
                }
            )
        return tools

    @staticmethod
    def _capability_to_tool_name(capability: str) -> str:
        return capability.replace(".", "_")
