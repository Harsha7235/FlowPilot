from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from flowpilot.agent.executor import (
    CodingExecutor,
    ExecutionResult,
)
from flowpilot.agent.generation_pipeline import (
    GenerationPipeline,
)
from flowpilot.agent.planner import (
    CodingPlanner,
)
from flowpilot.agent.repair import (
    RepairEngine,
    RepairPlan,
)
from flowpilot.agent.repair_generator import (
    RepairGenerator,
    RepairGenerationResult,
)


@dataclass
class AgentIteration:
    iteration: int
    phase: str
    success: bool
    output: Any = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "iteration": self.iteration,
            "phase": self.phase,
            "success": self.success,
            "output": self.output,
            "error": self.error,
        }


@dataclass
class AgentRunResult:
    success: bool
    request: str
    iterations: List[AgentIteration] = field(
        default_factory=list
    )
    plan: Any = None
    generation: Any = None
    execution: Optional[ExecutionResult] = None
    repair: Optional[RepairPlan] = None
    repair_generation: Optional[
        RepairGenerationResult
    ] = None
    errors: List[str] = field(
        default_factory=list
    )

    def summary(self) -> dict:
        return {
            "success": self.success,
            "request": self.request,
            "iterations": len(self.iterations),
            "has_plan": self.plan is not None,
            "has_generation": (
                self.generation is not None
            ),
            "has_execution": (
                self.execution is not None
            ),
            "has_repair": (
                self.repair is not None
            ),
            "has_repair_generation": (
                self.repair_generation is not None
            ),
            "errors": len(self.errors),
        }

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "request": self.request,
            "iterations": [
                item.to_dict()
                for item in self.iterations
            ],
            "errors": list(self.errors),
        }


class CodingAgent:
    """
    Main FlowPilot coding-agent orchestrator.

    Pipeline:

        request
          ↓
        planner
          ↓
        generation
          ↓
        validation / editing
          ↓
        testing
          ↓
        failure?
          ↓
        diagnosis
          ↓
        repair generation
          ↓
        corrected files
          ↓
        execution again
    """

    def __init__(
        self,
        workspace: str = ".",
        planner: Optional[
            CodingPlanner
        ] = None,
        generator: Optional[
            GenerationPipeline
        ] = None,
        executor: Optional[
            CodingExecutor
        ] = None,
        repair_engine: Optional[
            RepairEngine
        ] = None,
        repair_generator: Optional[
            RepairGenerator
        ] = None,
        max_iterations: int = 3,
    ) -> None:

        self.workspace = workspace

        self.planner = (
            planner
            or CodingPlanner()
        )

        self.generator = (
            generator
            or GenerationPipeline()
        )

        self.executor = (
            executor
            or CodingExecutor(workspace)
        )

        self.repair_engine = (
            repair_engine
            or RepairEngine()
        )

        self.repair_generator = (
            repair_generator
            or RepairGenerator()
        )

        self.max_iterations = max(
            1,
            max_iterations,
        )

    def run(
        self,
        request: str,
    ) -> AgentRunResult:

        request = request.strip()

        if not request:
            return AgentRunResult(
                success=False,
                request=request,
                errors=[
                    "Agent request is empty."
                ],
            )

        iterations: List[
            AgentIteration
        ] = []

        errors: List[str] = []

        # ---------------------------------------------
        # 1. PLAN
        # ---------------------------------------------

        plan = self.planner.plan(
            request
        )

        iterations.append(
            AgentIteration(
                iteration=1,
                phase="plan",
                success=plan.success,
                output=(
                    plan.summary()
                    if hasattr(
                        plan,
                        "summary",
                    )
                    else None
                ),
                error=(
                    plan.errors[0]
                    if getattr(
                        plan,
                        "errors",
                        [],
                    )
                    else None
                ),
            )
        )

        if not plan.success:

            errors.extend(
                getattr(
                    plan,
                    "errors",
                    [],
                )
            )

            return AgentRunResult(
                success=False,
                request=request,
                iterations=iterations,
                plan=plan,
                errors=errors,
            )

        # ---------------------------------------------
        # 2. INITIAL GENERATION
        # ---------------------------------------------

        generation = self.generator.generate(
            request
        )

        iterations.append(
            AgentIteration(
                iteration=2,
                phase="generate",
                success=generation.success,
                output=(
                    generation.summary()
                    if hasattr(
                        generation,
                        "summary",
                    )
                    else None
                ),
                error=(
                    generation.errors[0]
                    if generation.errors
                    else None
                ),
            )
        )

        if not generation.success:

            errors.extend(
                generation.errors
            )

            return AgentRunResult(
                success=False,
                request=request,
                iterations=iterations,
                plan=plan,
                generation=generation,
                errors=errors,
            )

        self._attach_generated_files(
            plan,
            generation,
        )

        # ---------------------------------------------
        # 3. EXECUTION / REPAIR LOOP
        # ---------------------------------------------

        execution = None
        repair = None
        repair_generation = None

        for attempt in range(
            1,
            self.max_iterations + 1,
        ):

            execution = self.executor.execute(
                plan
            )

            iterations.append(
                AgentIteration(
                    iteration=2 + attempt,
                    phase="execute",
                    success=execution.success,
                    output=execution.summary(),
                    error=(
                        execution.errors[0]
                        if execution.errors
                        else None
                    ),
                )
            )

            if execution.success:

                return AgentRunResult(
                    success=True,
                    request=request,
                    iterations=iterations,
                    plan=plan,
                    generation=generation,
                    execution=execution,
                    repair=repair,
                    repair_generation=(
                        repair_generation
                    ),
                    errors=[],
                )

            # -----------------------------------------
            # 4. DIAGNOSE FAILURE
            # -----------------------------------------

            repair = (
                self.repair_engine.analyze(
                    execution
                )
            )

            iterations.append(
                AgentIteration(
                    iteration=2 + attempt,
                    phase="diagnose",
                    success=repair.success,
                    output=repair.summary(),
                    error=(
                        repair.errors[0]
                        if repair.errors
                        else None
                    ),
                )
            )

            if not repair.success:

                errors.extend(
                    repair.errors
                )

                break

            # -----------------------------------------
            # 5. GENERATE REPAIR
            # -----------------------------------------

            repair_generation = (
                self.repair_generator.generate(
                    request=request,
                    repair_plan=repair,
                    context=self._generation_context(
                        generation
                    ),
                )
            )

            iterations.append(
                AgentIteration(
                    iteration=2 + attempt,
                    phase="repair_generate",
                    success=(
                        repair_generation.success
                    ),
                    output=(
                        repair_generation.summary()
                    ),
                    error=(
                        repair_generation.errors[0]
                        if repair_generation.errors
                        else None
                    ),
                )
            )

            if not repair_generation.success:

                errors.extend(
                    repair_generation.errors
                )

                break

            # -----------------------------------------
            # 6. REPLACE GENERATED FILES
            # -----------------------------------------

            replacement_files = list(
                repair_generation.files
            )

            if not replacement_files:

                errors.append(
                    "Repair generation returned "
                    "no files."
                )

                break

            try:

                plan.generated_files = (
                    replacement_files
                )

            except Exception as exc:

                errors.append(
                    "Unable to attach repair files: "
                    + str(exc)
                )

                break

            iterations.append(
                AgentIteration(
                    iteration=2 + attempt,
                    phase="repair_ready",
                    success=True,
                    output={
                        "files": len(
                            replacement_files
                        ),
                        "paths": [
                            item.path
                            for item in replacement_files
                        ],
                    },
                )
            )

        return AgentRunResult(
            success=False,
            request=request,
            iterations=iterations,
            plan=plan,
            generation=generation,
            execution=execution,
            repair=repair,
            repair_generation=(
                repair_generation
            ),
            errors=errors,
        )

    @staticmethod
    def _attach_generated_files(
        plan: Any,
        generation: Any,
    ) -> None:

        files = []

        if (
            generation is not None
            and generation.generation is not None
        ):
            files = list(
                generation.generation.files
            )

        plan.generated_files = files

    @staticmethod
    def _generation_context(
        generation: Any,
    ) -> str:

        if generation is None:
            return ""

        context = getattr(
            generation,
            "context",
            None,
        )

        if context:
            return str(context)

        return ""


__all__ = [
    "AgentIteration",
    "AgentRunResult",
    "CodingAgent",
]