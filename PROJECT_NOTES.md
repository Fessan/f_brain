# f_brain - Project Notes

## Project Vision

*What is this project? Why does it exist? Who is it for?*

---

## Session Notes

### [2026-02-17] Initial Setup
- Frame project initialized

### [2026-02-17] Architecture: Universal LLM Provider Router

**Проблема:** f_brain жёстко привязан к Claude CLI — все три метода `ClaudeProcessor` вызывают `subprocess.run(["claude", ...])`. Невозможно использовать другие LLM-провайдеры.

**Решение:** Создаём пакет `src/d_brain/llm/` с абстракцией и двумя реализациями.

**Архитектурные решения:**
- Claude CLI остаётся как есть — MCP работает из коробки, ломать незачем
- OpenAI через SDK с function calling — `TodoistToolExecutor` вызывает Todoist API напрямую
- `openai_base_url` даёт совместимость с Ollama, Together и другими OpenAI-compatible API
- Промпты не трогаем на первом этапе — MCP-инструкции OpenAI проигнорирует
- Провайдер выбирается через `LLM_PROVIDER=claude-cli|openai` в `.env`

**Структура нового пакета:**
```
src/d_brain/llm/
    __init__.py      # экспорт
    base.py          # ABC LLMProvider + dataclasses (LLMResponse, ToolDefinition, ToolCall)
    claude_cli.py    # ClaudeCLIProvider — subprocess логика из processor.py
    openai_api.py    # OpenAIProvider — openai SDK + function calling + tool loop
    tools.py         # ToolDefinition для Todoist + TodoistToolExecutor
    router.py        # get_provider() — фабрика по имени из конфига
```

**Изменяемые файлы:**
- `config.py` — +4 поля: `llm_provider`, `openai_api_key`, `openai_model`, `openai_base_url`
- `processor.py` — `ClaudeProcessor` → `LLMProcessor`, методы async, принимает `LLMProvider`
- `handlers/process.py`, `do.py`, `weekly.py` — фабрика `create_processor()`, убираем `asyncio.to_thread`
- `pyproject.toml` — +`openai` dependency

**Ключевая абстракция:**
```python
class LLMProvider(ABC):
    async def execute(self, prompt: str, *, tools: list[ToolDefinition] | None = None, timeout: int = 1200) -> LLMResponse: ...
```

**Объём:** ~400 строк нового кода, ~100 строк изменений. 6 новых файлов, 6 изменяемых.

### [2026-02-17] Documentation Update Before Change Planning
User: актуалиизруй пока документацию поп роекту. Делать план будем после этого

User: goals ведь надо будет создать? или нет?

Assistant: С нуля создавать не нужно: шаблоны уже есть в `vault/goals/` (`0-vision-3y.md`, `1-yearly-2025.md`, `2-monthly.md`, `3-weekly.md`). Нужно просто заполнить их под себя; отдельный `1-yearly-2026.md` создавать только если хочешь вести новый год отдельным файлом.

Assistant: Я выделил это как task по правилам Frame. Добавить запись в `tasks.json`? И отдельно: добавить этот контекст в `PROJECT_NOTES.md`?

User: да. да

### [2026-02-17] Plan Review Accepted and Revised Implementation Plan
User: теперь давай вернемся к плану по реализации. сделай его ревью

Assistant: [review findings shared: missing OpenAI file-tool parity, risk of blocking event loop if removing to_thread, missing scripts migration scope, missing output contract/config validation/test matrix]

User: да. делай

User: да. и сразу выполняй задачи

Decision: Use a revised implementation plan that keeps current behavior stable while introducing provider routing safely.

Revised Plan:
1. Provider surface and parity:
   - Keep one provider-agnostic contract for three operations: `process_daily`, `execute_prompt`, `generate_weekly`.
   - Define tool parity for `openai` with two groups:
     - Todoist operations (create/update/find/complete, user info)
     - Vault file operations required by current prompts (`read`, `write`, `append`, optional `list/search`)
   - If a requested tool is unavailable, provider must return structured failure that is still Telegram-safe and explicit.
2. Non-blocking execution model:
   - Keep `asyncio.to_thread(...)` in handlers as compatibility layer for blocking providers.
   - Provider interface is async, but each provider is free to use internal sync operations wrapped safely.
   - Remove `to_thread` only after both providers are proven non-blocking under load tests.
3. Full migration scope (not only handlers):
   - Migrate `src/d_brain/bot/handlers/process.py`, `src/d_brain/bot/handlers/do.py`, `src/d_brain/bot/handlers/weekly.py`.
   - Migrate script entrypoints using processor directly (`scripts/weekly.py`; daily processing automation paths).
   - Keep one shared provider router so handlers and scripts cannot diverge.
4. Output contract across providers:
   - Every provider returns a `report` string targeting Telegram HTML constraints.
   - Allowed tags stay aligned with formatter (`b`, `i`, `code`, `pre`, `a`, `s`, `u`).
   - Enforce truncation-safe output and fallback to escaped plain text on malformed HTML.
5. Configuration and validation:
   - Add settings: `llm_provider`, `openai_api_key`, `openai_model`, `openai_base_url`.
   - Startup validation rules:
     - `llm_provider` in `{claude-cli, openai}`
     - if `openai` selected -> require `openai_api_key` and `openai_model`
     - if `claude-cli` selected -> check `claude` availability at runtime with clear error message
   - Fail fast on invalid combinations with actionable error text.
6. Test matrix and acceptance gates:
   - Provider matrix: run smoke scenarios for both `claude-cli` and `openai`.
   - Flow matrix: `/process`, `/do` (text+voice), `/weekly`, `scripts/weekly.py`.
   - Verify:
     - no event-loop blocking symptoms during long runs
     - vault updates still produced
     - Todoist actions still executed
     - Telegram output passes formatter safety path
   - Migration is accepted only when both provider modes pass the same core scenarios.

### [2026-02-17] Architecture Clarifications Chosen by Best Practices
User: да внеси. по уточнениям. я не знаю как лучше. выбери сам опираясь н алучшие практики

Chosen Decisions:
1. `scripts/process.sh` strategy:
   - Migrate to a Python entrypoint that uses the same provider router as bot handlers and `scripts/weekly.py`.
   - Keep shell script as a thin operational wrapper only (env/bootstrap), without provider-specific logic.
   - Rationale: single runtime path prevents architecture drift and split-brain behavior.
2. Todoist tool strategy for OpenAI vs Claude:
   - Define a canonical capability contract in Python (`todoist.*`, `vault.*`) with strict schemas and error model.
   - Use this contract as source of truth for OpenAI execution and parity checks for Claude path.
   - Keep Claude MCP path initially for stability; enforce parity via capability tests, then reduce divergence incrementally.
   - Rationale: maximize reliability now while converging behavior by contract, not by provider internals.
3. Delivery priority:
   - Phase 1: architecture scaffold first (interfaces, router, contracts, config validation) with no behavior changes.
   - Phase 2: migrate entrypoints/adapters incrementally behind provider flag.
   - Phase 3: run full matrix (including failure modes) before default switch.
   - Rationale: lower rollout risk and easier regression isolation.

### [2026-02-17] Implemented Phase-1 Architecture Scaffold (Task-008)
Decision implemented in code:
- Added new layered package `src/d_brain/llm/`:
  - `base.py`: low-level provider contract (`LLMProvider`) and execution result model.
  - `claude_cli.py`: Claude CLI adapter implementing transport/execution only.
  - `router.py`: default provider factory.
  - `use_cases.py`: business use-cases (`DailyProcessingUseCase`, `ExecutePromptUseCase`, `WeeklyDigestUseCase`) + context loader.
- Reworked `src/d_brain/services/processor.py` into facade (`LLMProcessor`) that composes use-cases and provider.
- Kept backward compatibility through `ClaudeProcessor` class aliasing behavior to avoid handler/script breakage.
- Updated `STRUCTURE.json` to reflect layered architecture and new module dependencies.

### [2026-02-17] Unified Daily Runtime Entry (Task-009)
Decision implemented in code:
- Added `scripts/process_daily.py` to run daily processing through the shared Python architecture (`LLMProcessor` + formatter + git service + Telegram send).
- Converted `scripts/process.sh` into a thin wrapper (load `.env`, run `uv run python scripts/process_daily.py`).
- Removed provider-specific daily logic from shell layer so runtime behavior is no longer split between shell and Python orchestration.

### [2026-02-17] Added Canonical Capability Contract (Task-010)
Decision implemented in code:
- Added `src/d_brain/llm/tools.py` with canonical capability registry for `todoist.*` and `vault.*` operations.
- Introduced structured tool result and error envelopes (`ToolExecutionResult`, `ToolExecutionError`) plus runtime interface (`ToolRuntime`).
- Exported tool-contract primitives via `src/d_brain/llm/__init__.py` to keep provider integrations anchored to one shared schema source.

### [2026-02-17] Hardened Provider Response Contract (Task-011)
Decision implemented in code:
- Added typed response model `LLMResponseEnvelope` in `src/d_brain/llm/base.py` with `report/error/provider/meta/timings/tool_failures`.
- Updated use-cases in `src/d_brain/llm/use_cases.py` to return typed envelopes and capture elapsed execution time.
- Kept compatibility by adding `to_legacy_dict()` and leaving existing handler-facing processor methods in dict format.
- Added explicit typed facade methods in `src/d_brain/services/processor.py` (`*_result`) and switched automation scripts to use typed responses internally.

### [2026-02-17] Added Failure-Mode Migration Matrix (Task-012)
Decision implemented in docs:
- Added `docs/llm-migration-test-matrix.md` with:
  - provider parity scenarios (`claude-cli` vs `openai`) for `/process`, `/do`, `/weekly`, and scripts,
  - explicit negative scenarios (timeouts, tool errors, malformed HTML, partial capabilities, provider outage),
  - acceptance gates for rollout.
- Updated `STRUCTURE.json` to include the QA matrix artifact in project architecture map.

### [2026-02-17] Added Provider Config Validation and Routing
Decision implemented in code:
- Added provider config fields to `Settings`: `llm_provider`, `openai_api_key`, `openai_model`, `openai_base_url`.
- Added fail-fast validation: when `LLM_PROVIDER=openai`, both `OPENAI_API_KEY` and `OPENAI_MODEL` are required.
- Added `OpenAIProvider` adapter (`src/d_brain/llm/openai_api.py`) and extended router selection in `src/d_brain/llm/router.py`.
- Updated handlers and scripts to pass provider config into `LLMProcessor` so runtime provider selection is centralized and explicit.

### [2026-02-17] OpenAI Tool Loop Connected to Capability Runtime
Decision implemented in code:
- Added `DefaultToolRuntime` (`src/d_brain/llm/runtime.py`) to execute canonical capabilities (`todoist.*`, `vault.*`) with structured success/error payloads.
- Extended `OpenAIProvider` to run iterative tool-calling loop using OpenAI-compatible `tools` API and capability schemas from registry.
- Wired router to inject capability registry + runtime into OpenAI provider creation.
- Propagated `tool_failures` metadata from provider result into use-case response envelope for observability and parity debugging.

### [2026-02-17] Provider-Aware Prompt Tool Contract and Docs Sync
Decision implemented in code/docs:
- Added provider-aware prompt tool instructions in `src/d_brain/llm/use_cases.py`:
  - `claude-cli` path keeps MCP naming (`mcp__todoist__*`),
  - `openai` path uses function tool names (`todoist_*`, `vault_*`) exposed by capability registry.
- Removed MCP-only wording from generic execution steps so prompts are valid across both providers.
- Updated `QUICKSTART.md` and `STRUCTURE.json` to reflect provider-selectable runtime and current operational requirements.

### [2026-02-17] Chosen Deploy/Test Model: Docker Runtime + Host Scheduler (Option A)
User: так. давай подумаем над тем как тестироватьи  разворачивать? я бы хотел делалать это в докер файле используя мейк файл

User: ок. дава

User: делай А

Decision implemented:
- Added container runtime artifacts:
  - `Dockerfile`
  - `docker-compose.yml`
  - `.dockerignore`
- Added operational command surface in `Makefile`:
  - `build`, `up`, `down`, `restart`, `logs`, `ps`
  - `check`, `test`
  - `process-daily`, `weekly`, `deploy`, `claude-auth`
- Added operator docs for this flow:
  - `docs/docker-deploy.md`
  - Updated `QUICKSTART.md` and `docs/vps-setup.md` with Docker + Make commands
- Kept scheduled processing in host timers/cron by invoking Make targets (`make process-daily`, `make weekly`) to avoid in-container scheduler complexity.

### [2026-02-17] Revised to Fully Closed Docker Contour
User: так подожди. все таки нужен вараинт И. я хочу что бы вс ебыло в закртом конткре. нужен докер тогда

Decision implemented:
- Replaced host-scheduler approach with fully containerized scheduling:
  - Added `scripts/run_scheduler.sh` with `supercronic` and env-driven cron expressions.
  - Updated `docker-compose.yml` to run two services:
    - `bot` (Telegram runtime)
    - `scheduler` (daily/weekly job runner)
- Added persistent named volumes for closed contour state:
  - `vault-data` for vault artifacts
  - `claude-data` for Claude auth/runtime state
- Updated `Dockerfile` to include `supercronic` and Node runtime from `node:20-bookworm-slim` stage.
- Updated `Makefile` targets to operate full stack (`bot` + `scheduler`) and include scheduler script validation.
- Updated docs (`docs/docker-deploy.md`, `QUICKSTART.md`, `docs/vps-setup.md`) and `.env.example` (`DAILY_CRON`, `WEEKLY_CRON`, `TZ`) for closed-contour operation.

### [2026-02-17] Phase-3 Local Verification Executed
User: ок. что там дальше по палну?

User: да. делай

Decision implemented:
- Added local migration verification suite `tests/test_llm_migration_local.py` for scenarios that do not require external credentials:
  - provider/config fail-fast checks,
  - output sanitization/fallback behavior,
  - response envelope propagation and metadata checks,
  - session corruption tolerance,
  - non-blocking policy precondition (`asyncio.to_thread` presence in handlers),
  - weekly summary persistence and MOC update flow.
- Updated `docs/llm-migration-test-matrix.md` with an execution status section (PASS/BLOCKED split) for local closed-contour verification.
- Marked remaining credential-dependent E2E matrix and rollout policy as pending follow-up tasks in `tasks.json`.
- During local verification, fixed two operational issues:
  - Included `tests/` in Docker image so `make test` actually executes pytest in container.
  - Quoted `DAILY_CRON`/`WEEKLY_CRON` defaults in `.env.example` and docs to keep `.env` shell-compatible when sourced by scripts.

### [2026-02-17] Production Provider Rollout Policy Finalized
User: делай

Decision implemented:
- Defined production provider policy in `docs/provider-rollout-policy.md`.
- Chosen default provider: `claude-cli` until credentialed matrix (`task-018`) is fully passed.
- Chosen fallback model: manual operational switch (`LLM_PROVIDER` + `make restart`) without automatic runtime failover.
- Added explicit promotion criteria for `openai` and documented rollback procedure.

### [2026-02-17] Closed-Contour Git/Volume Hardening After Review
User: это тогда уже завтра. сейчас проведи анализ сдеанного. поищи пробелмы. выхови код ревью

User: 1. от корня. 2. надо исправлять

Decision implemented:
- Updated `VaultGit` to detect repository root via `git rev-parse --show-toplevel` and run git commands from root while scoping staged/status files to `vault/`.
- Fixed `commit_and_push` behavior so git failures return `False` (no longer masked as success when commit fails).
- Added file lock (`.git/vault-git-ops.lock`) to serialize concurrent git operations between bot and scheduler containers.
- Added `scripts/docker-entrypoint.sh`:
  - ensures `/app/vault`, `/app/.git`, `/home/app/.claude` are writable,
  - seeds `git-data` volume from image template (`/app/.git-template`) on first boot,
  - drops privileges to `app` via `gosu`.
- Updated Docker stack:
  - `Dockerfile`: installs `gosu`, includes git template, uses entrypoint bootstrap.
  - `docker-compose.yml`: adds shared `git-data` volume for both `bot` and `scheduler`.
- Updated docs (`docs/docker-deploy.md`, `QUICKSTART.md`) and added regression tests (`tests/test_vault_git.py`) for the new git contract.
