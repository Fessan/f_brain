"""Tests for git automation behavior in closed Docker contour."""

from __future__ import annotations

import subprocess
from pathlib import Path

from d_brain.services.git import VaultGit


_GIT_ISOLATED_ENV = {
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
}


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    import os

    env = {**os.environ, **_GIT_ISOLATED_ENV}
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _init_repo(tmp_path: Path, *, with_identity: bool = True) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    vault = repo / "vault"
    vault.mkdir(parents=True)

    init = _git(repo, "init")
    assert init.returncode == 0, init.stderr

    if with_identity:
        assert _git(repo, "config", "user.email", "bot@example.com").returncode == 0
        assert _git(repo, "config", "user.name", "Bot").returncode == 0

    (repo / "README.md").write_text("init\n", encoding="utf-8")
    (vault / "daily.md").write_text("start\n", encoding="utf-8")
    assert _git(repo, "add", "-A").returncode == 0

    commit = _git(repo, "commit", "-m", "init")
    assert commit.returncode == 0, commit.stderr

    return repo, vault


def test_commit_changes_runs_from_repo_root_and_scopes_to_vault(tmp_path: Path) -> None:
    repo, vault = _init_repo(tmp_path)

    (vault / "daily.md").write_text("updated\n", encoding="utf-8")
    (repo / "outside.txt").write_text("should stay uncommitted\n", encoding="utf-8")

    git = VaultGit(vault)
    assert git.repo_root == repo.resolve()

    committed = git.commit_changes("chore: update vault")
    assert committed is True

    changed = _git(repo, "show", "--name-only", "--pretty=format:", "HEAD")
    assert changed.returncode == 0
    files = {line.strip() for line in changed.stdout.splitlines() if line.strip()}
    assert "vault/daily.md" in files
    assert "outside.txt" not in files

    status = _git(repo, "status", "--porcelain")
    assert status.returncode == 0
    assert "outside.txt" in status.stdout


def test_commit_and_push_returns_false_when_repo_is_missing(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir(parents=True)

    git = VaultGit(vault)
    assert git.commit_and_push("chore: should fail") is False


def test_commit_and_push_returns_false_on_commit_error(tmp_path: Path) -> None:
    repo, vault = _init_repo(tmp_path)
    assert _git(repo, "config", "--unset", "user.email").returncode == 0
    assert _git(repo, "config", "--unset", "user.name").returncode == 0

    (vault / "daily.md").write_text("another update\n", encoding="utf-8")

    git = VaultGit(vault)
    assert git.commit_and_push("chore: should not be masked") is False


def test_commit_and_push_returns_true_when_no_changes(tmp_path: Path) -> None:
    _, vault = _init_repo(tmp_path)

    git = VaultGit(vault)
    assert git.commit_and_push("chore: no changes") is True
