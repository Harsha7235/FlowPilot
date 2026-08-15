from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class GitResult:
    command: str
    success: bool
    return_code: int
    stdout: str
    stderr: str

    def summary(self) -> dict:
        return {
            "command": self.command,
            "success": self.success,
            "return_code": self.return_code,
            "stdout_length": len(self.stdout),
            "stderr_length": len(self.stderr),
        }


class GitTools:
    """
    Git operations used by the FlowPilot coding agent.

    This first version intentionally provides read-oriented
    repository operations and safe diff/status inspection.

    It does not automatically commit or push changes.
    """

    DEFAULT_TIMEOUT = 60

    def __init__(
        self,
        workspace: str = ".",
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.timeout = timeout

    def _run(
        self,
        arguments: List[str],
        timeout: Optional[int] = None,
    ) -> GitResult:
        command = "git " + " ".join(arguments)

        if not self.workspace.exists():
            return GitResult(
                command=command,
                success=False,
                return_code=-1,
                stdout="",
                stderr=f"Workspace does not exist: {self.workspace}",
            )

        effective_timeout = (
            timeout if timeout is not None else self.timeout
        )

        try:
            result = subprocess.run(
                ["git", *arguments],
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=effective_timeout,
            )

            return GitResult(
                command=command,
                success=result.returncode == 0,
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )

        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""

            if isinstance(stdout, bytes):
                stdout = stdout.decode(
                    "utf-8",
                    errors="replace",
                )

            if isinstance(stderr, bytes):
                stderr = stderr.decode(
                    "utf-8",
                    errors="replace",
                )

            return GitResult(
                command=command,
                success=False,
                return_code=-2,
                stdout=stdout,
                stderr=(
                    f"Git command timed out after "
                    f"{effective_timeout} seconds.\n{stderr}"
                ),
            )

        except Exception as exc:
            return GitResult(
                command=command,
                success=False,
                return_code=-1,
                stdout="",
                stderr=str(exc),
            )

    def status(
        self,
        timeout: Optional[int] = None,
    ) -> GitResult:
        """Return the current Git working-tree status."""

        return self._run(
            ["status", "--short", "--branch"],
            timeout,
        )

    def diff(
        self,
        timeout: Optional[int] = None,
    ) -> GitResult:
        """Return unstaged working-tree changes."""

        return self._run(
            ["diff", "--no-ext-diff"],
            timeout,
        )

    def staged_diff(
        self,
        timeout: Optional[int] = None,
    ) -> GitResult:
        """Return staged changes."""

        return self._run(
            ["diff", "--cached", "--no-ext-diff"],
            timeout,
        )

    def log(
        self,
        count: int = 10,
        timeout: Optional[int] = None,
    ) -> GitResult:
        """Return recent commits."""

        if count < 1:
            count = 1

        return self._run(
            [
                "log",
                f"-{count}",
                "--oneline",
                "--decorate",
            ],
            timeout,
        )

    def current_branch(
        self,
        timeout: Optional[int] = None,
    ) -> GitResult:
        """Return the current branch name."""

        return self._run(
            ["branch", "--show-current"],
            timeout,
        )

    def is_repository(self) -> bool:
        """Return True when the workspace is inside a Git repository."""

        result = self._run(
            ["rev-parse", "--is-inside-work-tree"]
        )

        return (
            result.success
            and result.stdout.strip().lower() == "true"
        )

    def changed_files(
        self,
        timeout: Optional[int] = None,
    ) -> GitResult:
        """Return files changed in the working tree."""

        return self._run(
            [
                "status",
                "--short",
            ],
            timeout,
        )


__all__: List[str] = [
    "GitResult",
    "GitTools",
]