"""Git automation service for vault."""

import fcntl
import logging
import os
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Literal

logger = logging.getLogger(__name__)


class VaultGit:
    """Service for git operations on vault."""

    def __init__(self, vault_path: Path) -> None:
        self.vault_path = Path(vault_path).resolve()
        self.git_env = {**os.environ, "GIT_DISCOVERY_ACROSS_FILESYSTEM": "1"}
        self.repo_root = self._detect_repo_root()
        self.lock_timeout_seconds = 30.0

        if self.repo_root is not None:
            self.scope_path = self._resolve_scope_path()
            self.lock_path = self.repo_root / ".git" / "vault-git-ops.lock"
            logger.info(
                "VaultGit initialized with repo root '%s' and scope '%s'",
                self.repo_root,
                self.scope_path,
            )
        else:
            self.scope_path = "."
            self.lock_path = self.vault_path / ".git-ops.lock"
            logger.error(
                "VaultGit initialization failed: no git repository found for vault path '%s'",
                self.vault_path,
            )

    def _detect_repo_root(self) -> Path | None:
        """Detect git repository root from the vault path."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=self.vault_path,
                capture_output=True,
                text=True,
                check=False,
                env=self.git_env,
            )
        except FileNotFoundError:
            logger.error("Git executable not found in PATH")
            return None
        except Exception:
            logger.exception("Unexpected error while detecting git repository")
            return None

        if result.returncode != 0:
            logger.error(
                "Could not detect git repository from '%s': %s",
                self.vault_path,
                result.stderr.strip() or "unknown error",
            )
            return None

        root = Path(result.stdout.strip()).resolve()
        if not root.exists():
            logger.error("Detected git root '%s' does not exist", root)
            return None

        return root

    def _resolve_scope_path(self) -> str:
        """Resolve vault path relative to repository root for scoped git ops."""
        if self.repo_root is None:
            return "."

        if self.vault_path == self.repo_root:
            return "."

        try:
            return self.vault_path.relative_to(self.repo_root).as_posix()
        except ValueError:
            logger.warning(
                "Vault path '%s' is outside repo root '%s'; falling back to full repository scope",
                self.vault_path,
                self.repo_root,
            )
            return "."

    @contextmanager
    def _acquire_lock(self) -> Iterator[None]:
        """Serialize git operations across bot and scheduler processes."""
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as lock_file:
            deadline = time.monotonic() + self.lock_timeout_seconds
            while True:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError(
                            f"Timed out acquiring git lock: {self.lock_path}"
                        )
                    time.sleep(0.2)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _run_git(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run git command in repository root directory."""
        if self.repo_root is None:
            return subprocess.CompletedProcess(
                ["git", *args],
                returncode=128,
                stdout="",
                stderr=f"No git repository detected for vault path '{self.vault_path}'",
            )
        return subprocess.run(
            ["git", *args],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
            env=self.git_env,
        )

    def get_status(self) -> str | None:
        """Get git status."""
        status_args: list[str] = ["status", "--porcelain"]
        if self.scope_path != ".":
            status_args.extend(["--", self.scope_path])
        result = self._run_git(*status_args)
        if result.returncode != 0:
            logger.error("Git status failed: %s", result.stderr.strip() or "unknown error")
            return None
        return result.stdout

    def has_changes(self) -> bool | None:
        """Check if there are uncommitted changes."""
        status = self.get_status()
        if status is None:
            return None
        return bool(status.strip())

    def _commit_changes_detailed(
        self, message: str
    ) -> Literal["committed", "no_changes", "error"]:
        """Stage scoped changes and commit with explicit outcome."""
        has_changes = self.has_changes()
        if has_changes is None:
            return "error"

        if not has_changes:
            logger.info("No changes to commit")
            return "no_changes"

        add_args: list[str] = ["add", "-A"]
        if self.scope_path != ".":
            add_args.extend(["--", self.scope_path])
        add_result = self._run_git(*add_args)
        if add_result.returncode != 0:
            logger.error("Git add failed: %s", add_result.stderr.strip() or "unknown error")
            return "error"

        commit_result = self._run_git("commit", "-m", message)
        if commit_result.returncode != 0:
            logger.error(
                "Git commit failed: %s", commit_result.stderr.strip() or "unknown error"
            )
            return "error"

        logger.info("Committed: %s", message)
        return "committed"

    def commit_changes(self, message: str) -> bool:
        """Stage all changes and commit.

        Args:
            message: Commit message

        Returns:
            True if commit was made, False otherwise
        """
        return self._commit_changes_detailed(message) == "committed"

    def push(self) -> bool:
        """Push to remote.

        Returns:
            True if push was successful
        """
        result = self._run_git("push")
        if result.returncode != 0:
            logger.error("Git push failed: %s", result.stderr.strip() or "unknown error")
            return False

        logger.info("Pushed to remote")
        return True

    def commit_and_push(self, message: str) -> bool:
        """Commit all changes and push.

        Args:
            message: Commit message

        Returns:
            True if successful
        """
        try:
            with self._acquire_lock():
                commit_outcome = self._commit_changes_detailed(message)
                if commit_outcome == "committed":
                    return self.push()
                if commit_outcome == "no_changes":
                    return True
                return False
        except TimeoutError as exc:
            logger.error("Git operation lock timeout: %s", exc)
            return False
