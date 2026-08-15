from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class Diagnostic:
    category: str
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    command: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "message": self.message,
            "file": self.file,
            "line": self.line,
            "command": self.command,
        }


@dataclass
class RepairPlan:
    success: bool
    diagnostics: List[Diagnostic] = field(
        default_factory=list
    )
    actions: List[str] = field(
        default_factory=list
    )
    errors: List[str] = field(
        default_factory=list
    )

    def summary(self) -> dict:
        return {
            "success": self.success,
            "diagnostics": len(self.diagnostics),
            "actions": len(self.actions),
            "errors": len(self.errors),
        }


class FailureDiagnoser:
    """
    Converts execution/test failures into structured
    diagnostics that the repair layer can understand.
    """

    def diagnose(
        self,
        execution_result: Any,
    ) -> List[Diagnostic]:

        diagnostics: List[Diagnostic] = []

        if execution_result is None:
            return [
                Diagnostic(
                    category="execution",
                    message=(
                        "No execution result was provided."
                    ),
                )
            ]

        errors = getattr(
            execution_result,
            "errors",
            [],
        )

        for error in errors:

            if not isinstance(error, str):
                error = str(error)

            diagnostics.append(
                self._classify_error(error)
            )

        steps = getattr(
            execution_result,
            "steps",
            [],
        )

        for step in steps:

            if getattr(
                step,
                "success",
                True,
            ):
                continue

            error = getattr(
                step,
                "error",
                None,
            )

            if error:
                diagnostics.append(
                    self._classify_error(
                        str(error)
                    )
                )

        return self._deduplicate(
            diagnostics
        )

    def _classify_error(
        self,
        error: str,
    ) -> Diagnostic:

        lowered = error.lower()

        if (
            "syntaxerror" in lowered
            or "indentationerror" in lowered
        ):
            return Diagnostic(
                category="syntax",
                message=error,
            )

        if (
            "importerror" in lowered
            or "modulenotfounderror" in lowered
        ):
            return Diagnostic(
                category="import",
                message=error,
            )

        if (
            "permission denied" in lowered
            or "access is denied" in lowered
        ):
            return Diagnostic(
                category="permission",
                message=error,
            )

        if (
            "filenotfounderror" in lowered
            or "no such file" in lowered
        ):
            return Diagnostic(
                category="filesystem",
                message=error,
            )

        if (
            "typeerror" in lowered
            or "attributeerror" in lowered
            or "nameerror" in lowered
        ):
            return Diagnostic(
                category="runtime",
                message=error,
            )

        if (
            "failed" in lowered
            or "return code" in lowered
        ):
            return Diagnostic(
                category="test",
                message=error,
            )

        return Diagnostic(
            category="unknown",
            message=error,
        )

    def _deduplicate(
        self,
        diagnostics: List[Diagnostic],
    ) -> List[Diagnostic]:

        result: List[Diagnostic] = []
        seen = set()

        for diagnostic in diagnostics:

            key = (
                diagnostic.category,
                diagnostic.message,
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(diagnostic)

        return result


class RepairPlanner:
    """
    Builds a safe repair plan from diagnostics.

    This layer does not modify files.
    """

    def build(
        self,
        diagnostics: List[Diagnostic],
    ) -> RepairPlan:

        if not diagnostics:

            return RepairPlan(
                success=False,
                errors=[
                    "No diagnostics available."
                ],
            )

        actions: List[str] = []

        for diagnostic in diagnostics:

            category = diagnostic.category

            if category == "syntax":
                actions.append(
                    "Inspect the reported syntax or indentation error."
                )

            elif category == "import":
                actions.append(
                    "Inspect imports and verify the referenced module exists."
                )

            elif category == "permission":
                actions.append(
                    "Check workspace permissions and protected paths."
                )

            elif category == "filesystem":
                actions.append(
                    "Verify that the referenced file or directory exists."
                )

            elif category == "runtime":
                actions.append(
                    "Inspect the failing runtime operation and its inputs."
                )

            elif category == "test":
                actions.append(
                    "Inspect the failing test output and reproduce the failure."
                )

            else:
                actions.append(
                    "Inspect the failure and gather additional diagnostics."
                )

        actions = self._deduplicate(
            actions
        )

        return RepairPlan(
            success=True,
            diagnostics=list(diagnostics),
            actions=actions,
        )

    def _deduplicate(
        self,
        items: List[str],
    ) -> List[str]:

        result = []
        seen = set()

        for item in items:

            if item in seen:
                continue

            seen.add(item)
            result.append(item)

        return result


class RepairEngine:
    """
    High-level diagnostic and repair-plan engine.

    It diagnoses failures and produces a safe repair plan.
    It does not automatically modify files yet.
    """

    def __init__(
        self,
        diagnoser: Optional[
            FailureDiagnoser
        ] = None,
        planner: Optional[
            RepairPlanner
        ] = None,
    ) -> None:

        self.diagnoser = (
            diagnoser
            or FailureDiagnoser()
        )

        self.planner = (
            planner
            or RepairPlanner()
        )

    def analyze(
        self,
        execution_result: Any,
    ) -> RepairPlan:

        diagnostics = self.diagnoser.diagnose(
            execution_result
        )

        return self.planner.build(
            diagnostics
        )


__all__ = [
    "Diagnostic",
    "RepairPlan",
    "FailureDiagnoser",
    "RepairPlanner",
    "RepairEngine",
]