from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from flowpilot.agent.code_generator import GeneratedFile


@dataclass
class ValidationIssue:
    level: str
    message: str
    path: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "message": self.message,
            "path": self.path,
        }


@dataclass
class CodeValidationResult:
    success: bool
    files_checked: int = 0
    valid_files: List[GeneratedFile] = field(
        default_factory=list
    )
    issues: List[ValidationIssue] = field(
        default_factory=list
    )

    def summary(self) -> dict:
        return {
            "success": self.success,
            "files_checked": self.files_checked,
            "valid_files": len(self.valid_files),
            "issues": len(self.issues),
            "errors": sum(
                1
                for issue in self.issues
                if issue.level == "error"
            ),
            "warnings": sum(
                1
                for issue in self.issues
                if issue.level == "warning"
            ),
        }


class CodeValidator:
    """
    Validates generated files before they reach the
    controlled editing layer.
    """

    MAX_FILE_SIZE = 2 * 1024 * 1024

    ALLOWED_EXTENSIONS = {
        ".py",
        ".pyi",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".md",
        ".txt",
        ".c",
        ".cc",
        ".cpp",
        ".h",
        ".hpp",
        ".java",
        ".rs",
        ".go",
        ".html",
        ".css",
        ".sh",
        ".bat",
    }

    BLOCKED_PATH_PARTS = {
        ".git",
        "__pycache__",
        ".env",
    }

    def validate(
        self,
        files: List[GeneratedFile],
    ) -> CodeValidationResult:

        issues: List[ValidationIssue] = []
        valid_files: List[GeneratedFile] = []
        seen_paths = set()

        for generated_file in files:

            path = generated_file.path.strip()

            if not path:

                issues.append(
                    ValidationIssue(
                        level="error",
                        message="Generated file path is empty.",
                    )
                )
                continue

            normalized = self._normalize_path(path)

            if normalized in seen_paths:

                issues.append(
                    ValidationIssue(
                        level="error",
                        message="Duplicate generated file path.",
                        path=path,
                    )
                )
                continue

            seen_paths.add(normalized)

            path_issues = self._validate_path(
                path
            )

            if path_issues:
                issues.extend(path_issues)
                continue

            content_issues = (
                self._validate_content(
                    generated_file
                )
            )

            if content_issues:
                issues.extend(content_issues)
                continue

            valid_files.append(
                generated_file
            )

        has_errors = any(
            issue.level == "error"
            for issue in issues
        )

        return CodeValidationResult(
            success=not has_errors,
            files_checked=len(files),
            valid_files=valid_files,
            issues=issues,
        )

    def _validate_path(
        self,
        path: str,
    ) -> List[ValidationIssue]:

        issues: List[ValidationIssue] = []

        candidate = Path(path)

        if candidate.is_absolute():

            issues.append(
                ValidationIssue(
                    level="error",
                    message=(
                        "Absolute paths are not allowed."
                    ),
                    path=path,
                )
            )

            return issues

        normalized = path.replace(
            "\\",
            "/",
        )

        parts = normalized.split("/")

        if ".." in parts:

            issues.append(
                ValidationIssue(
                    level="error",
                    message=(
                        "Path traversal is not allowed."
                    ),
                    path=path,
                )
            )

        lowered_parts = {
            part.lower()
            for part in parts
        }

        blocked = (
            lowered_parts
            & self.BLOCKED_PATH_PARTS
        )

        if blocked:

            issues.append(
                ValidationIssue(
                    level="error",
                    message=(
                        "Generated path contains "
                        "a protected directory/file."
                    ),
                    path=path,
                )
            )

        suffix = candidate.suffix.lower()

        if (
            suffix
            and suffix not in self.ALLOWED_EXTENSIONS
        ):

            issues.append(
                ValidationIssue(
                    level="warning",
                    message=(
                        f"File extension '{suffix}' "
                        "is not in the standard "
                        "FlowPilot allowlist."
                    ),
                    path=path,
                )
            )

        return issues

    def _validate_content(
        self,
        generated_file: GeneratedFile,
    ) -> List[ValidationIssue]:

        issues: List[ValidationIssue] = []

        content = generated_file.content

        if not isinstance(content, str):

            issues.append(
                ValidationIssue(
                    level="error",
                    message="File content must be text.",
                    path=generated_file.path,
                )
            )

            return issues

        size = len(
            content.encode(
                "utf-8",
                errors="replace",
            )
        )

        if size > self.MAX_FILE_SIZE:

            issues.append(
                ValidationIssue(
                    level="error",
                    message=(
                        "Generated file exceeds "
                        "the maximum allowed size."
                    ),
                    path=generated_file.path,
                )
            )

        if "\x00" in content:

            issues.append(
                ValidationIssue(
                    level="error",
                    message=(
                        "Generated file contains "
                        "null bytes."
                    ),
                    path=generated_file.path,
                )
            )

        return issues

    @staticmethod
    def _normalize_path(
        path: str,
    ) -> str:

        return (
            path.replace("\\", "/")
            .strip()
            .lower()
        )


__all__ = [
    "ValidationIssue",
    "CodeValidationResult",
    "CodeValidator",
]