SHELL := /bin/bash
COMPOSE := docker compose
BOT := bot
SCHEDULER := scheduler

.PHONY: build up down restart logs logs-bot logs-scheduler ps check test process-daily weekly deploy claude-auth codex-auth

build:
	$(COMPOSE) build $(BOT)

up:
	$(COMPOSE) up -d $(BOT) $(SCHEDULER)

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart $(BOT) $(SCHEDULER)

logs:
	$(COMPOSE) logs -f --tail=200 $(BOT) $(SCHEDULER)

logs-bot:
	$(COMPOSE) logs -f --tail=200 $(BOT)

logs-scheduler:
	$(COMPOSE) logs -f --tail=200 $(SCHEDULER)

ps:
	$(COMPOSE) ps

check:
	$(COMPOSE) run --rm --no-deps $(BOT) bash -lc '\
		python3 -m compileall -q src scripts/process_daily.py scripts/weekly.py && \
		python3 -m json.tool tasks.json >/dev/null && \
		python3 -m json.tool STRUCTURE.json >/dev/null && \
		bash -n scripts/process.sh && \
		bash -n scripts/run_scheduler.sh && \
		bash -n scripts/docker-entrypoint.sh \
	'

test:
	$(COMPOSE) run --rm --no-deps $(BOT) bash -lc '\
		if [ -d tests ]; then uv run pytest -q; else echo "No tests directory, skipping pytest"; fi \
	'

process-daily:
	$(COMPOSE) run --rm --no-deps $(BOT) uv run python scripts/process_daily.py

weekly:
	$(COMPOSE) run --rm --no-deps $(BOT) uv run python scripts/weekly.py

claude-auth:
	$(COMPOSE) run --rm -it --no-deps $(BOT) claude auth login

codex-auth:
	$(COMPOSE) run --rm -it --no-deps $(BOT) codex login

deploy: build up
