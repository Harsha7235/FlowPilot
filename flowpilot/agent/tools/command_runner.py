from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class CommandResult:
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


class CommandRunner:
    """
    Safe command execution layer for the FlowPilot agent.

    This class executes commands from a controlled working directory
    and returns structured results for the agent.
    """

    DEFAULT_TIMEOUT = 120

    def __init__(
        self,
        workspace: str = ".",
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.timeout = timeout

    def run(
        self,
        command: str,
        timeout: Optional[int] = None,
    ) -> CommandResult:
        """
        Execute a shell command inside the configured workspace.
        """

        if not command or not command.strip():
            return CommandResult(
                command=command,
                success=False,
                return_code=-1,
                stdout="",
                stderr="Command cannot be empty.",
            )

        if not self.workspace.exists():
            return CommandResult(
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
            completed = subprocess.run(
                command,
                cwd=str(self.workspace),
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=effective_timeout,
            )

            return CommandResult(
                command=command,
                success=completed.returncode == 0,
                return_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
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

            return CommandResult(
                command=command,
                success=False,
                return_code=-2,
                stdout=stdout,
                stderr=(
                    f"Command timed out after "
                    f"{effective_timeout} seconds.\n{stderr}"
                ),
            )

        except Exception as exc:
            return CommandResult(
                command=command,
                success=False,
                return_code=-1,
                stdout="",
                stderr=str(exc),
            )

    def run_python(
        self,
        code: str,
        timeout: Optional[int] = None,
    ) -> CommandResult:
        """
        Execute a Python one-liner/script using the current Python
        interpreter.
        """

        if not code or not code.strip():
            return CommandResult(
                command="python",
                success=False,
                return_code=-1,
                stdout="",
                stderr="Python code cannot be empty.",
            )

        command = f'py -c "{code}"'

        return self.run(
            command,
            timeout=timeout,
        )

    def run_test_file(
        self,
        test_file: str,
        timeout: Optional[int] = None,
    ) -> CommandResult:
        """
        Run a Python test file.
        """

        path = Path(test_file)

        if not path.is_absolute():
            path = self.workspace / path

        if not path.exists():
            return CommandResult(
                command=f"py {test_file}",
                success=False,
                return_code=-1,
                stdout="",
                stderr=f"Test file not found: {path}",
            )

        command = f'py "{path}"'

        return self.run(
            command,
            timeout=timeout,
        )

    def run_py_compile(
        self,
        python_file: str,
        timeout: Optional[int] = None,
    ) -> CommandResult:
        """
        Compile a Python file to check for syntax errors.
        """

        path = Path(python_file)

        if not path.is_absolute():
            path = self.workspace / path

        if not path.exists():
            return CommandResult(
                command=f'py -m py_compile "{python_file}"',
                success=False,
                return_code=-1,
                stdout="",
                stderr=f"Python file not found: {path}",
            )

        command = f'py -m py_compile "{path}"'

        return self.run(
            command,
            timeout=timeout,
        )


__all__: List[str] = [
    "CommandResult",
    "CommandRunner",
]