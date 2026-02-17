#!/bin/bash
set -euo pipefail

# Thin wrapper: load .env and run shared Python daily processor.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +a
fi

cd "$PROJECT_DIR"
exec uv run python scripts/process_daily.py
