#!/usr/bin/env bash
set -euo pipefail

DAILY_CRON_EXPR="${DAILY_CRON:-0 21 * * *}"
WEEKLY_CRON_EXPR="${WEEKLY_CRON:-0 9 * * 1}"

cat >/tmp/d-brain.cron <<EOF
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
${DAILY_CRON_EXPR} cd /app && uv run python scripts/process_daily.py >> /proc/1/fd/1 2>&1
${WEEKLY_CRON_EXPR} cd /app && uv run python scripts/weekly.py >> /proc/1/fd/1 2>&1
EOF

echo "Starting scheduler with DAILY_CRON='${DAILY_CRON_EXPR}' and WEEKLY_CRON='${WEEKLY_CRON_EXPR}'"
exec supercronic -passthrough-logs /tmp/d-brain.cron
