from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class PlanStep:
    step_id: int
    title: str
    description: str
    action: str
    target: str = ""
    dependencies: List[int] = field(default_factory=list)
    completed: bool = False

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "title": self.title,
            "description": self.description,
            "action": self.action,
            "target": self.target,
            "dependencies": list(self.dependencies),
            "completed": self.completed,
        }


@dataclass
class CodingPlan:
    request: str
    objective: str
    steps: List[PlanStep] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "request": self.request,
            "objective": self.objective,
            "steps": [step.to_dict() for step in self.steps],
            "risks": list(self.risks),
            "success_criteria": list(self.success_criteria),
        }

    def summary(self) -> dict:
        return {
            "request": self.request,
            "objective": self.objective,
            "steps": len(self.steps),
            "risks": len(self.risks),
            "success_criteria": len(self.success_criteria),
        }


@dataclass
class PlannerResult:
    success: bool
    plan: CodingPlan | None = None
    errors: List[str] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "success": self.success,
            "steps": len(self.plan.steps) if self.plan else 0,
            "errors": len(self.errors),
        }


class CodingPlanner:
    """
    Creates a structured coding plan from a user's request.

    This version is deterministic and does not depend on a specific
    LLM provider. Later, the model layer can provide richer planning
    while keeping this plan format unchanged.
    """

    def plan(self, request: str) -> PlannerResult:
        if not request or not request.strip():
            return PlannerResult(
                success=False,
                errors=["Coding request cannot be empty."],
            )

        request = request.strip()

        objective = self._build_objective(request)

        steps = [
            PlanStep(
                step_id=1,
                title="Understand request",
                description=(
                    "Identify the requested functionality, affected "
                    "components, constraints, and expected result."
                ),
                action="analyze",
            ),
            PlanStep(
                step_id=2,
                title="Inspect repository",
                description=(
                    "Search the repository for relevant implementations, "
                    "source files, classes, functions, tests, and build files."
                ),
                action="search",
                dependencies=[1],
            ),
            PlanStep(
                step_id=3,
                title="Inspect FlowPilot knowledge",
                description=(
                    "Use the FlowPilot knowledge graph and retriever to "
                    "identify related implementation patterns."
                ),
                action="knowledge",
                dependencies=[1, 2],
            ),
            PlanStep(
                step_id=4,
                title="Create implementation plan",
                description=(
                    "Determine which files must be created or modified "
                    "and establish their dependency order."
                ),
                action="plan",
                dependencies=[2, 3],
            ),
            PlanStep(
                step_id=5,
                title="Implement changes",
                description=(
                    "Create or modify the required source files using "
                    "the available filesystem tools."
                ),
                action="edit",
                dependencies=[4],
            ),
            PlanStep(
                step_id=6,
                title="Validate changes",
                description=(
                    "Compile, build, and run relevant tests against the "
                    "implemented changes."
                ),
                action="test",
                dependencies=[5],
            ),
            PlanStep(
                step_id=7,
                title="Review result",
                description=(
                    "Inspect the final changes and report successful "
                    "work or remaining problems."
                ),
                action="review",
                dependencies=[6],
            ),
        ]

        risks = [
            "Existing repository behavior must not be broken.",
            "Changes should follow existing project conventions.",
            "Build and test failures must be inspected before completion.",
            "Destructive operations should require explicit authorization.",
        ]

        success_criteria = [
            "Requested functionality is implemented.",
            "Relevant files are correctly created or modified.",
            "Code passes applicable syntax or compilation checks.",
            "Relevant tests pass.",
            "Final changes can be reviewed through Git diff.",
        ]

        plan = CodingPlan(
            request=request,
            objective=objective,
            steps=steps,
            risks=risks,
            success_criteria=success_criteria,
        )

        return PlannerResult(
            success=True,
            plan=plan,
        )

    def _build_objective(self, request: str) -> str:
        return (
            "Implement the requested change while preserving existing "
            "repository behavior, following established implementation "
            f"patterns, and validating the result: {request}"
        )


__all__ = [
    "PlanStep",
    "CodingPlan",
    "PlannerResult",
    "CodingPlanner",
]