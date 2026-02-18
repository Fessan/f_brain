#!/usr/bin/env bash
set -euo pipefail

ensure_dir() {
    local dir_path="$1"
    mkdir -p "${dir_path}"
}

seed_git_metadata() {
    if git -C /app rev-parse --git-dir >/dev/null 2>&1; then
        return
    fi

    if [ ! -d /app/.git-template ]; then
        echo "Git metadata template is missing at /app/.git-template" >&2
        return
    fi

    cp -a /app/.git-template/. /app/.git/
}

fix_ownership() {
    local dir_path="$1"
    if [ "$(stat -c %u "$dir_path" 2>/dev/null || echo 0)" != "1000" ]; then
        chown -R app:app "$dir_path"
    fi
}

ensure_dir /app/.git
ensure_dir /app/vault
ensure_dir /home/app/.claude

seed_git_metadata

fix_ownership /app/.git
fix_ownership /app/vault
fix_ownership /home/app/.claude

exec gosu app "$@"
