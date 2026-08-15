from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from flowpilot.agent.code_generator import GeneratedFile
from flowpilot.agent.code_validator import CodeValidator
from flowpilot.agent.planner import CodingPlan, PlanStep
from flowpilot.agent.tools.tool_factory import FlowPilotToolset


@dataclass
class StepResult:
    step_id: int
    title: str
    action: str
    success: bool
    output: Any = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "title": self.title,
            "action": self.action,
            "success": self.success,
            "output": self.output,
            "error": self.error,
        }


@dataclass
class ExecutionResult:
    success: bool
    request: str
    steps: List[StepResult] = field(
        default_factory=list
    )
    errors: List[str] = field(
        default_factory=list
    )

    def summary(self) -> dict:
        return {
            "success": self.success,
            "request": self.request,
            "steps_total": len(self.steps),
            "steps_successful": sum(
                1
                for step in self.steps
                if step.success
            ),
            "steps_failed": sum(
                1
                for step in self.steps
                if not step.success
            ),
            "errors": len(self.errors),
        }

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "request": self.request,
            "steps": [
                step.to_dict()
                for step in self.steps
            ],
            "errors": list(self.errors),
        }


class CodingExecutor:
    """
    Executes a FlowPilot coding plan.

    Generated files must pass CodeValidator before
    reaching the controlled editing layer.
    """

    SAFE_ACTIONS = {
        "analyze",
        "search",
        "knowledge",
        "plan",
        "edit",
        "test",
        "review",
    }

    def __init__(
        self,
        toolset: Optional[FlowPilotToolset] = None,
        workspace: str = ".",
        validator: Optional[CodeValidator] = None,
    ) -> None:

        if isinstance(toolset, str):
            workspace = toolset
            toolset = None

        self.toolset = (
            toolset
            or FlowPilotToolset(workspace)
        )

        self.validator = (
            validator
            or CodeValidator()
        )

    def execute(
        self,
        plan: CodingPlan,
    ) -> ExecutionResult:

        if plan is None:
            return ExecutionResult(
                success=False,
                request="",
                errors=[
                    "Coding plan cannot be None."
                ],
            )

        results: List[StepResult] = []
        errors: List[str] = []
        completed_steps = set()

        for step in plan.steps:

            missing = [
                dependency
                for dependency in step.dependencies
                if dependency not in completed_steps
            ]

            if missing:

                error = (
                    f"Step {step.step_id} has unmet "
                    f"dependencies: {missing}"
                )

                results.append(
                    StepResult(
                        step_id=step.step_id,
                        title=step.title,
                        action=step.action,
                        success=False,
                        error=error,
                    )
                )

                errors.append(error)
                break

            result = self._execute_step(
                step,
                plan,
            )

            results.append(result)

            if not result.success:

                if result.error:
                    errors.append(result.error)

                break

            completed_steps.add(
                step.step_id
            )

        success = (
            not errors
            and len(results) == len(plan.steps)
        )

        return ExecutionResult(
            success=success,
            request=plan.request,
            steps=results,
            errors=errors,
        )

    def _execute_step(
        self,
        step: PlanStep,
        plan: CodingPlan,
    ) -> StepResult:

        action = step.action.lower().strip()

        if action not in self.SAFE_ACTIONS:
            return StepResult(
                step_id=step.step_id,
                title=step.title,
                action=action,
                success=False,
                error=(
                    f"Action '{action}' is not enabled."
                ),
            )

        try:

            if action == "analyze":
                return self._analyze_step(
                    step,
                    plan,
                )

            if action == "search":
                return self._search_step(
                    step,
                    plan,
                )

            if action == "knowledge":
                return self._knowledge_step(
                    step,
                    plan,
                )

            if action == "plan":
                return self._plan_step(
                    step,
                    plan,
                )

            if action == "edit":
                return self._edit_step(
                    step,
                    plan,
                )

            if action == "test":
                return self._test_step(
                    step,
                    plan,
                )

            if action == "review":
                return self._review_step(
                    step,
                    plan,
                )

            return StepResult(
                step_id=step.step_id,
                title=step.title,
                action=action,
                success=False,
                error=(
                    f"Unsupported action: {action}"
                ),
            )

        except Exception as exc:

            return StepResult(
                step_id=step.step_id,
                title=step.title,
                action=action,
                success=False,
                error=str(exc),
            )

    def _analyze_step(
        self,
        step: PlanStep,
        plan: CodingPlan,
    ) -> StepResult:

        return StepResult(
            step_id=step.step_id,
            title=step.title,
            action=step.action,
            success=True,
            output={
                "request": plan.request,
                "objective": plan.objective,
            },
        )

    def _search_step(
        self,
        step: PlanStep,
        plan: CodingPlan,
    ) -> StepResult:

        query = self._extract_search_query(
            plan.request
        )

        result = self.toolset.call(
            "code_search",
            query=query,
        )

        if isinstance(result, dict):

            success = result.get(
                "success",
                True,
            )

            matches = result.get(
                "results",
                result.get(
                    "matches",
                    [],
                ),
            )

        else:

            success = True
            matches = result

        if matches is None:
            matches = []

        return StepResult(
            step_id=step.step_id,
            title=step.title,
            action=step.action,
            success=success,
            output={
                "query": query,
                "matches": matches[:50],
                "match_count": len(matches),
            },
            error=(
                None
                if success
                else "Code search failed."
            ),
        )

    def _knowledge_step(
        self,
        step: PlanStep,
        plan: CodingPlan,
    ) -> StepResult:

        return StepResult(
            step_id=step.step_id,
            title=step.title,
            action=step.action,
            success=True,
            output={
                "message": (
                    "Knowledge-engine integration "
                    "boundary reached."
                ),
                "query": plan.request,
            },
        )

    def _plan_step(
        self,
        step: PlanStep,
        plan: CodingPlan,
    ) -> StepResult:

        return StepResult(
            step_id=step.step_id,
            title=step.title,
            action=step.action,
            success=True,
            output={
                "objective": plan.objective,
                "risks": list(plan.risks),
                "success_criteria": list(
                    plan.success_criteria
                ),
            },
        )

    def _edit_step(
        self,
        step: PlanStep,
        plan: CodingPlan,
    ) -> StepResult:

        files = self._get_generated_files(
            plan
        )

        if not files:

            return StepResult(
                step_id=step.step_id,
                title=step.title,
                action=step.action,
                success=True,
                output={
                    "message": (
                        "No generated files were "
                        "provided. Edit layer is ready."
                    ),
                    "files": 0,
                },
            )

        validation = self.validator.validate(
            files
        )

        if not validation.success:

            issues = [
                issue.to_dict()
                for issue in validation.issues
                if issue.level == "error"
            ]

            return StepResult(
                step_id=step.step_id,
                title=step.title,
                action=step.action,
                success=False,
                output={
                    "validation": validation.summary(),
                    "issues": issues,
                },
                error=(
                    "Generated code failed "
                    "safety validation."
                ),
            )

        written = []

        for generated_file in validation.valid_files:

            result = self.toolset.call(
                "create_file",
                path=generated_file.path,
                content=generated_file.content,
            )

            if isinstance(result, dict):

                if not result.get(
                    "success",
                    False,
                ):

                    return StepResult(
                        step_id=step.step_id,
                        title=step.title,
                        action=step.action,
                        success=False,
                        output={
                            "written": written,
                            "failed_file": (
                                generated_file.path
                            ),
                            "result": result,
                        },
                        error=result.get(
                            "error",
                            "File creation failed.",
                        ),
                    )

            written.append(
                generated_file.path
            )

        return StepResult(
            step_id=step.step_id,
            title=step.title,
            action=step.action,
            success=True,
            output={
                "validation": validation.summary(),
                "written_files": written,
            },
        )

    def _test_step(
        self,
        step: PlanStep,
        plan: CodingPlan,
    ) -> StepResult:

        result = self.toolset.call(
            "run_command",
            command=(
                "py -m compileall -q flowpilot"
            ),
        )

        if not isinstance(result, dict):

            return StepResult(
                step_id=step.step_id,
                title=step.title,
                action=step.action,
                success=False,
                error=(
                    "Invalid command runner result."
                ),
            )

        success = result.get(
            "success",
            False,
        )

        return StepResult(
            step_id=step.step_id,
            title=step.title,
            action=step.action,
            success=success,
            output=result,
            error=(
                result.get("stderr")
                if not success
                else None
            ),
        )

    def _review_step(
        self,
        step: PlanStep,
        plan: CodingPlan,
    ) -> StepResult:

        status = self.toolset.call(
            "git_status"
        )

        diff = self.toolset.call(
            "git_diff"
        )

        return StepResult(
            step_id=step.step_id,
            title=step.title,
            action=step.action,
            success=True,
            output={
                "git_status": status,
                "git_diff": diff,
            },
        )

    def _get_generated_files(
        self,
        plan: CodingPlan,
    ) -> List[GeneratedFile]:

        generated = getattr(
            plan,
            "generated_files",
            None,
        )

        if generated is None:
            return []

        result = []

        for item in generated:

            if isinstance(
                item,
                GeneratedFile,
            ):
                result.append(item)

            elif isinstance(
                item,
                dict,
            ):

                result.append(
                    GeneratedFile(
                        path=item["path"],
                        content=item["content"],
                        language=item.get(
                            "language",
                            "text",
                        ),
                        reason=item.get(
                            "reason",
                            "",
                        ),
                    )
                )

        return result

    def _extract_search_query(
        self,
        request: str,
    ) -> str:

        known_terms = [
            "analog_agc_xx",
            "digital_costas_loop_cc",
            "blocks_add_xx",
            "blocks_divide_xx",
            "audio_sink",
        ]

        for term in known_terms:

            if term.lower() in request.lower():
                return term

        words = [
            word.strip(
                ".,!?;:\"'()[]{}"
            )
            for word in request.split()
        ]

        meaningful = [
            word
            for word in words
            if len(word) >= 4
        ]

        if meaningful:
            return meaningful[-1]

        return request


__all__ = [
    "StepResult",
    "ExecutionResult",
    "CodingExecutor",
]