from __future__ import annotations

from typing import Any, Callable, Dict

from flowpilot.agent.tools.code_editor import CodeEditor


class FlowPilotToolset:
    """Central tool interface used by the FlowPilot agent."""

    def __init__(self, workspace: str = ".") -> None:
        self.workspace = workspace
        self.editor = CodeEditor(workspace)

        self._tools: Dict[str, Callable[..., Any]] = {
            "code_search": self._code_search,
            "run_command": self._run_command,
            "git_status": self._git_status,
            "git_diff": self._git_diff,
            "read_file": self._read_file,
            "create_file": self._create_file,
            "overwrite_file": self._overwrite_file,
            "append_file": self._append_file,
            "replace_file": self._replace_file,
        }

    def call(self, name: str, **kwargs: Any) -> Any:
        if name not in self._tools:
            raise ValueError(
                f"Unknown FlowPilot tool: {name}"
            )

        return self._tools[name](**kwargs)

    def names(self) -> list[str]:
        return sorted(self._tools.keys())

    def has(self, name: str) -> bool:
        return name in self._tools

    def _code_search(self, query: str) -> Any:
        from flowpilot.agent.tools.code_search import search_code

        return search_code(
            self.workspace,
            query,
        )

    def _run_command(self, command: str) -> Any:
        from flowpilot.agent.tools.command_runner import (
            CommandRunner,
        )

        runner = CommandRunner(
            workspace=self.workspace,
            timeout=120,
        )

        result = runner.run(command)

        if hasattr(result, "to_dict"):
            return result.to_dict()

        if hasattr(result, "__dict__"):
            return dict(result.__dict__)

        return result

    def _git_status(self) -> Any:
        return self._run_command(
            "git status --short"
        )

    def _git_diff(self) -> Any:
        return self._run_command(
            "git diff --"
        )

    def _read_file(self, path: str) -> Any:
        return self.editor.read(path)

    def _create_file(
        self,
        path: str,
        content: str,
    ) -> Any:
        return self.editor.create(
            path,
            content,
        ).to_dict()

    def _overwrite_file(
        self,
        path: str,
        content: str,
    ) -> Any:
        return self.editor.overwrite(
            path,
            content,
        ).to_dict()

    def _append_file(
        self,
        path: str,
        content: str,
    ) -> Any:
        return self.editor.append(
            path,
            content,
        ).to_dict()

    def _replace_file(
        self,
        path: str,
        old: str,
        new: str,
        count: int = 1,
    ) -> Any:
        return self.editor.replace(
            path,
            old,
            new,
            count,
        ).to_dict()


__all__ = [
    "FlowPilotToolset",
]