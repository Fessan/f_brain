# Docker + Make Workflow (Closed Contour)

This project runs fully inside Docker:
- `bot` service handles Telegram updates
- `scheduler` service runs daily/weekly jobs via cron expressions

## Prerequisites

- Docker Engine with Compose plugin
- `.env` file in project root
- Optional for `claude-cli`: run `make claude-auth` once to persist auth in Docker volume `claude-data`
- Git identity configured in repository config used for automated commits:
  - `git config user.name "Your Name"`
  - `git config user.email "you@example.com"`

## Build and Run Bot

```bash
make build
make up
make logs
```

Check running services:

```bash
make ps
```

State is persisted in named volumes:
- `vault-data` -> `/app/vault`
- `git-data` -> `/app/.git`
- `claude-data` -> `/home/app/.claude`

## Verification and Tests

```bash
make check
make test
```

`make test` skips pytest automatically when there is no `tests/` directory.

## Manual Jobs

```bash
make process-daily
make weekly
```

## Deploy (build + start bot)

```bash
make deploy
```

## Scheduler Configuration

Set cron expressions in `.env`:

```bash
DAILY_CRON="0 21 * * *"
WEEKLY_CRON="0 9 * * 1"
TZ=UTC
```

Scheduler logs:

```bash
make logs-scheduler
```

## Provider Switch and Rollback

- Default production provider policy is defined in `docs/provider-rollout-policy.md`.
- Switch active provider by changing `LLM_PROVIDER` in `.env` and running:

```bash
make restart
make ps
make logs-bot
```

If you have old root-owned Docker volumes from earlier images, reset once:

```bash
make down
docker compose down -v
make up
```
