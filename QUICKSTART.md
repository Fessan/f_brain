<!-- FRAME AUTO-GENERATED FILE -->
<!-- Purpose: Quick onboarding guide for developers and AI assistants -->
<!-- For AI assistants: Read this FIRST to quickly understand how to work with this project. Contains setup instructions, common commands, and key files to know. -->
<!-- Last Updated: 2026-02-17 -->

# f_brain - Quick Start Guide

## What This Project Is

`f_brain` is a Telegram-based personal assistant:
- receives voice/text/photo/forwarded messages,
- stores them in an Obsidian-style vault,
- uses a provider-selectable LLM layer (`claude-cli` or `openai`) for `/process`, `/do`, `/weekly`.

Runtime stack:
- Python 3.12+
- `uv` for dependency management
- `httpx` for provider/tool HTTP calls
- Claude CLI (`claude`) when `LLM_PROVIDER=claude-cli`
- OpenAI-compatible API key/model when `LLM_PROVIDER=openai`
- Node.js (for Todoist MCP via `npx`) when using Claude MCP path
- Docker + Docker Compose (closed-contour runtime/deploy path)

## Setup

```bash
git clone <repo-url>
cd f_brain
cp .env.example .env
# Fill .env with your real tokens/IDs
uv sync
```

Provider config in `.env`:
- Default mode: `LLM_PROVIDER=claude-cli`
- OpenAI mode: set `LLM_PROVIDER=openai` and provide `OPENAI_API_KEY` + `OPENAI_MODEL`
- Optional custom endpoint: `OPENAI_BASE_URL`
- Scheduler config: `DAILY_CRON`, `WEEKLY_CRON`, `TZ`
- Rollout/fallback policy: see `docs/provider-rollout-policy.md`

## Run

```bash
# Start Telegram bot
uv run python -m d_brain

# Run weekly digest manually
uv run python scripts/weekly.py

# Run daily processing script manually
./scripts/process.sh
```

Docker + Make path:

```bash
make build
make up
make claude-auth   # one-time, only for LLM_PROVIDER=claude-cli
make logs
```

Manual one-off job runs:

```bash
make process-daily
make weekly
```

## Key Files

| File | Purpose |
|------|---------|
| `src/d_brain/__main__.py` | App entrypoint |
| `src/d_brain/config.py` | Environment settings |
| `src/d_brain/bot/` | Telegram bot wiring, handlers, formatters |
| `src/d_brain/services/` | Transcription, vault IO, session, git, processor facade |
| `src/d_brain/llm/` | Provider contracts, adapters, router, use-cases, tool runtime |
| `deploy/` | systemd service and timer templates |
| `scripts/` | Manual/cron helpers (`process.sh`, `weekly.py`) |
| `Dockerfile` | Container image definition |
| `docker-compose.yml` | Orchestration for `bot` + `scheduler` services |
| `Makefile` | Unified build/test/deploy commands over docker compose |
| `docs/provider-rollout-policy.md` | Production default/fallback provider policy |
| `mcp-config.json` | Todoist MCP server config |
| `vault/` | Knowledge base and generated artifacts |

## Project Structure

```
f_brain/
├── src/d_brain/      # Application source code
├── vault/            # Obsidian-style data storage
├── deploy/           # systemd units/timers
├── scripts/          # operational scripts
├── docs/             # setup/ops docs
├── tasks.json        # Frame task tracking
├── PROJECT_NOTES.md  # decisions and context
├── STRUCTURE.json    # architecture map
└── ...
```

## For AI Assistants

1. Read `AGENTS.md` first and follow Frame rules.
2. At session start, review pending items in `tasks.json`.
3. Use `STRUCTURE.json` + `PROJECT_NOTES.md` before implementing changes.
4. Keep docs in sync when architecture/files/workflows change.

## Quick Validation

```bash
# Syntax check
python3 -m compileall -q src

# If pytest is installed in your env
python3 -m pytest -q

# Containerized checks/tests
make check
make test
```
