"""Tool runtime implementation for canonical capability contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from d_brain.llm.tools import ToolExecutionError, ToolExecutionResult, ToolRuntime


class DefaultToolRuntime(ToolRuntime):
    """Default runtime for todoist.* and vault.* capabilities."""

    def __init__(self, *, vault_path: Path, todoist_api_key: str = "") -> None:
        self.vault_path = Path(vault_path).resolve()
        self.todoist_api_key = todoist_api_key

    def execute(self, capability: str, payload: dict[str, Any]) -> ToolExecutionResult:
        """Execute capability and return structured result."""
        try:
            handler = self._resolve_handler(capability)
            data = handler(payload)
            return ToolExecutionResult(capability=capability, ok=True, data=data)
        except CapabilityError as exc:
            return ToolExecutionResult(
                capability=capability,
                ok=False,
                error=ToolExecutionError(
                    code=exc.code,
                    message=str(exc),
                    retryable=exc.retryable,
                    details=exc.details,
                ),
            )
        except Exception as exc:  # pragma: no cover - defensive safety
            return ToolExecutionResult(
                capability=capability,
                ok=False,
                error=ToolExecutionError(
                    code="runtime_error",
                    message=str(exc),
                    retryable=False,
                ),
            )

    def _resolve_handler(self, capability: str):
        handlers = {
            "vault.read_file": self._vault_read_file,
            "vault.write_file": self._vault_write_file,
            "vault.list_files": self._vault_list_files,
            "todoist.user_info": self._todoist_user_info,
            "todoist.add_tasks": self._todoist_add_tasks,
            "todoist.find_completed_tasks": self._todoist_find_completed_tasks,
        }
        if capability not in handlers:
            raise CapabilityError("unsupported_capability", f"Unsupported capability: {capability}")
        return handlers[capability]

    def _resolve_vault_path(self, relative_path: str) -> Path:
        path = (self.vault_path / relative_path).resolve()
        if not path.is_relative_to(self.vault_path):
            raise CapabilityError(
                "path_outside_vault",
                f"Path escapes vault: {relative_path}",
                details={"path": relative_path},
            )
        return path

    def _vault_read_file(self, payload: dict[str, Any]) -> dict[str, Any]:
        path = str(payload.get("path", ""))
        if not path:
            raise CapabilityError("invalid_input", "vault.read_file requires 'path'")

        resolved = self._resolve_vault_path(path)
        if not resolved.exists():
            return {"path": path, "exists": False, "content": ""}
        if resolved.is_dir():
            raise CapabilityError("invalid_input", "Cannot read directory as file")

        return {"path": path, "exists": True, "content": resolved.read_text(encoding="utf-8")}

    def _vault_write_file(self, payload: dict[str, Any]) -> dict[str, Any]:
        path = str(payload.get("path", ""))
        content = str(payload.get("content", ""))
        mode = str(payload.get("mode", "overwrite"))
        if not path:
            raise CapabilityError("invalid_input", "vault.write_file requires 'path'")
        if mode not in {"overwrite", "append"}:
            raise CapabilityError("invalid_input", "mode must be overwrite or append")

        resolved = self._resolve_vault_path(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        if mode == "append":
            with resolved.open("a", encoding="utf-8") as file_obj:
                file_obj.write(content)
        else:
            resolved.write_text(content, encoding="utf-8")

        return {"path": path, "writtenBytes": len(content.encode("utf-8"))}

    def _vault_list_files(self, payload: dict[str, Any]) -> dict[str, Any]:
        directory = str(payload.get("dir", "."))
        pattern = str(payload.get("pattern", "*"))
        limit = int(payload.get("limit", 200))
        resolved = self._resolve_vault_path(directory)
        if not resolved.exists():
            return {"files": []}
        if not resolved.is_dir():
            raise CapabilityError("invalid_input", "dir must point to directory")

        files: list[str] = []
        for file_path in sorted(resolved.rglob(pattern)):
            if file_path.is_file():
                files.append(str(file_path.relative_to(self.vault_path)))
                if len(files) >= limit:
                    break
        return {"files": files}

    def _todoist_user_info(self, payload: dict[str, Any]) -> dict[str, Any]:
        del payload
        data = self._todoist_request(
            "https://api.todoist.com/sync/v9/sync",
            {"sync_token": "*", "resource_types": json.dumps(["user"])},
        )
        user = data.get("user", {})
        return {
            "userId": str(user.get("id", "")),
            "email": user.get("email", ""),
            "name": user.get("full_name", "") or user.get("name", ""),
        }

    def _todoist_add_tasks(self, payload: dict[str, Any]) -> dict[str, Any]:
        tasks = payload.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            raise CapabilityError("invalid_input", "todoist.add_tasks requires non-empty tasks list")

        created: list[dict[str, Any]] = []
        for task in tasks:
            if not isinstance(task, dict):
                raise CapabilityError("invalid_input", "task item must be object")
            content = str(task.get("content", "")).strip()
            if not content:
                raise CapabilityError("invalid_input", "task content is required")

            body: dict[str, Any] = {"content": content}
            if task.get("description"):
                body["description"] = task["description"]
            if task.get("priority"):
                body["priority"] = int(task["priority"])
            if task.get("projectId"):
                body["project_id"] = task["projectId"]
            if task.get("dueString"):
                body["due_string"] = task["dueString"]

            data = self._todoist_request(
                "https://api.todoist.com/rest/v2/tasks",
                body,
                method="json_post",
            )
            created.append({"id": str(data.get("id", "")), "content": data.get("content", content)})

        return {"created": created}

    def _todoist_find_completed_tasks(self, payload: dict[str, Any]) -> dict[str, Any]:
        query: dict[str, Any] = {}
        if payload.get("since"):
            query["since"] = str(payload["since"])
        if payload.get("until"):
            query["until"] = str(payload["until"])
        if payload.get("limit"):
            query["limit"] = int(payload["limit"])

        data = self._todoist_request(
            "https://api.todoist.com/sync/v9/completed/get_all",
            query,
        )
        items = data.get("items", []) or []
        tasks: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            tasks.append(
                {
                    "id": str(item.get("task_id", item.get("id", ""))),
                    "content": item.get("content", ""),
                    "completedAt": item.get("completed_at", ""),
                }
            )
        return {"tasks": tasks}

    def _todoist_request(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        method: str = "post",
    ) -> dict[str, Any]:
        if not self.todoist_api_key:
            raise CapabilityError("missing_credentials", "TODOIST_API_KEY is not configured")

        try:
            import httpx
        except ModuleNotFoundError as exc:
            raise CapabilityError("runtime_dependency_missing", "httpx is required for todoist capabilities") from exc

        headers = {"Authorization": f"Bearer {self.todoist_api_key}"}
        try:
            with httpx.Client(timeout=30) as client:
                if method == "json_post":
                    response = client.post(url, json=payload, headers=headers)
                else:
                    response = client.post(url, data=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise CapabilityError("todoist_timeout", "Todoist request timed out", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise CapabilityError(
                "todoist_transport_error",
                f"Todoist transport error: {type(exc).__name__}",
                retryable=True,
            ) from exc

        if response.status_code >= 400:
            raise CapabilityError(
                "todoist_api_error",
                f"Todoist API error {response.status_code}",
                details={"body": response.text[:500]},
                retryable=response.status_code >= 500,
            )

        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise CapabilityError("todoist_invalid_json", "Todoist response is not valid JSON") from exc


class CapabilityError(Exception):
    """Capability execution exception with structured metadata."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.details = details or {}
