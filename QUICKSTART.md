<!-- FRAME AUTO-GENERATED FILE -->
<!-- Purpose: Quick onboarding guide for developers and AI assistants -->
<!-- For AI assistants: Read this FIRST to quickly understand how to work with this project. Contains setup instructions, common commands, and key files to know. -->
<!-- Last Updated: 2026-02-17 -->

# f_brain - Quick Start Guide

## What This Project Is

`f_brain` is a Telegram-based personal assistant:
- receives voice/text/photo/forwarded messages,
- stores them in an Obsidian-style vault,
- uses Claude CLI + MCP Todoist tools for `/process`, `/do`, `/weekly`.

Runtime stack:
- Python 3.12+
- `uv` for dependency management
- Node.js (for Todoist MCP via `npx`)
- Claude CLI (`claude`)

## Setup

```bash
git clone <repo-url>
cd f_brain
cp .env.example .env
# Fill .env with your real tokens/IDs
uv sync
```

## Run

```bash
# Start Telegram bot
uv run python -m d_brain

# Run weekly digest manually
uv run python scripts/weekly.py

# Run daily processing script manually
./scripts/process.sh
```

## Key Files

| File | Purpose |
|------|---------|
| `src/d_brain/__main__.py` | App entrypoint |
| `src/d_brain/config.py` | Environment settings |
| `src/d_brain/bot/` | Telegram bot wiring, handlers, formatters |
| `src/d_brain/services/` | Transcription, vault IO, session, git, Claude processing |
| `deploy/` | systemd service and timer templates |
| `scripts/` | Manual/cron helpers (`process.sh`, `weekly.py`) |
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
```
