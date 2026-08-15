from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class EditResult:
    success: bool
    path: str
    action: str
    message: str
    bytes_written: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "path": self.path,
            "action": self.action,
            "message": self.message,
            "bytes_written": self.bytes_written,
            "error": self.error,
        }


class CodeEditor:
    """
    Controlled filesystem editor for FlowPilot.

    The editor is restricted to the configured workspace and
    refuses paths that escape the workspace.

    Supported operations:

        create
        overwrite
        append
        replace

    Destructive operations are intentionally conservative.
    """

    def __init__(self, workspace: str = ".") -> None:
        self.workspace = Path(workspace).resolve()

    def _safe_path(self, path: str) -> Path:
        candidate = Path(path)

        if not candidate.is_absolute():
            candidate = self.workspace / candidate

        candidate = candidate.resolve()

        try:
            candidate.relative_to(self.workspace)
        except ValueError as exc:
            raise ValueError(
                f"Path is outside workspace: {path}"
            ) from exc

        return candidate

    def exists(self, path: str) -> bool:
        target = self._safe_path(path)
        return target.exists()

    def read(self, path: str) -> str:
        target = self._safe_path(path)

        if not target.exists():
            raise FileNotFoundError(
                f"File does not exist: {path}"
            )

        if not target.is_file():
            raise IsADirectoryError(
                f"Path is not a file: {path}"
            )

        return target.read_text(
            encoding="utf-8"
        )

    def create(
        self,
        path: str,
        content: str,
    ) -> EditResult:
        try:
            target = self._safe_path(path)

            if target.exists():
                return EditResult(
                    success=False,
                    path=str(target),
                    action="create",
                    message="File already exists.",
                    error="File already exists.",
                )

            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            target.write_text(
                content,
                encoding="utf-8",
            )

            return EditResult(
                success=True,
                path=str(target),
                action="create",
                message="File created successfully.",
                bytes_written=len(
                    content.encode("utf-8")
                ),
            )

        except Exception as exc:
            return EditResult(
                success=False,
                path=path,
                action="create",
                message="File creation failed.",
                error=str(exc),
            )

    def overwrite(
        self,
        path: str,
        content: str,
    ) -> EditResult:
        try:
            target = self._safe_path(path)

            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            target.write_text(
                content,
                encoding="utf-8",
            )

            return EditResult(
                success=True,
                path=str(target),
                action="overwrite",
                message="File overwritten successfully.",
                bytes_written=len(
                    content.encode("utf-8")
                ),
            )

        except Exception as exc:
            return EditResult(
                success=False,
                path=path,
                action="overwrite",
                message="File overwrite failed.",
                error=str(exc),
            )

    def append(
        self,
        path: str,
        content: str,
    ) -> EditResult:
        try:
            target = self._safe_path(path)

            if not target.exists():
                return EditResult(
                    success=False,
                    path=str(target),
                    action="append",
                    message="File does not exist.",
                    error="File does not exist.",
                )

            with target.open(
                "a",
                encoding="utf-8",
            ) as file:
                file.write(content)

            return EditResult(
                success=True,
                path=str(target),
                action="append",
                message="Content appended successfully.",
                bytes_written=len(
                    content.encode("utf-8")
                ),
            )

        except Exception as exc:
            return EditResult(
                success=False,
                path=path,
                action="append",
                message="Append operation failed.",
                error=str(exc),
            )

    def replace(
        self,
        path: str,
        old: str,
        new: str,
        count: int = 1,
    ) -> EditResult:
        try:
            target = self._safe_path(path)

            if not target.exists():
                return EditResult(
                    success=False,
                    path=str(target),
                    action="replace",
                    message="File does not exist.",
                    error="File does not exist.",
                )

            content = target.read_text(
                encoding="utf-8"
            )

            occurrences = content.count(old)

            if occurrences == 0:
                return EditResult(
                    success=False,
                    path=str(target),
                    action="replace",
                    message="Target text was not found.",
                    error="Target text was not found.",
                )

            if count < 0:
                count = occurrences

            updated = content.replace(
                old,
                new,
                count,
            )

            target.write_text(
                updated,
                encoding="utf-8",
            )

            return EditResult(
                success=True,
                path=str(target),
                action="replace",
                message=(
                    f"Replaced {min(occurrences, count)} "
                    "occurrence(s)."
                ),
                bytes_written=len(
                    new.encode("utf-8")
                ),
            )

        except Exception as exc:
            return EditResult(
                success=False,
                path=path,
                action="replace",
                message="Replace operation failed.",
                error=str(exc),
            )

    def list_files(
        self,
        pattern: str = "**/*",
    ) -> List[str]:
        files: List[str] = []

        for path in self.workspace.glob(pattern):
            if path.is_file():
                files.append(
                    str(
                        path.relative_to(
                            self.workspace
                        )
                    )
                )

        return sorted(files)


__all__ = [
    "EditResult",
    "CodeEditor",
]