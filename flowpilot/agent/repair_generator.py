from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from flowpilot.agent.code_generator import (
    CodeGenerator,
    GeneratedFile,
    GenerationResult,
)
from flowpilot.agent.repair import (
    Diagnostic,
    RepairPlan,
)


@dataclass
class RepairGenerationResult:
    success: bool
    original_request: str
    repair_prompt: str = ""
    generation: Optional[GenerationResult] = None
    files: List[GeneratedFile] = field(
        default_factory=list
    )
    errors: List[str] = field(
        default_factory=list
    )

    def summary(self) -> dict:
        return {
            "success": self.success,
            "original_request": self.original_request,
            "prompt_length": len(
                self.repair_prompt
            ),
            "files": len(self.files),
            "has_generation": (
                self.generation is not None
            ),
            "errors": len(self.errors),
        }


class RepairGenerator:
    """
    Generates a corrected implementation from a
    failed execution and its diagnostics.

    This class does not write files.
    """

    def __init__(
        self,
        generator: Optional[
            CodeGenerator
        ] = None,
    ) -> None:

        self.generator = (
            generator
            or CodeGenerator()
        )

    def generate(
        self,
        request: str,
        repair_plan: RepairPlan,
        context: str = "",
    ) -> RepairGenerationResult:

        request = request.strip()

        if not request:

            return RepairGenerationResult(
                success=False,
                original_request=request,
                errors=[
                    "Original request is empty."
                ],
            )

        if repair_plan is None:

            return RepairGenerationResult(
                success=False,
                original_request=request,
                errors=[
                    "Repair plan is missing."
                ],
            )

        if not repair_plan.success:

            return RepairGenerationResult(
                success=False,
                original_request=request,
                errors=[
                    "Repair plan is not valid."
                ],
            )

        prompt = self._build_repair_prompt(
            request=request,
            repair_plan=repair_plan,
        )

        combined_context = self._combine_context(
            context=context,
            repair_plan=repair_plan,
        )

        generation = self.generator.generate(
            request=prompt,
            context=combined_context,
            instructions=(
                "Generate only the corrected "
                "implementation needed to resolve "
                "the diagnosed failure. Preserve "
                "working behavior and avoid "
                "unrelated changes."
            ),
        )

        if not generation.success:

            return RepairGenerationResult(
                success=False,
                original_request=request,
                repair_prompt=prompt,
                generation=generation,
                errors=list(
                    generation.errors
                ),
            )

        files = list(
            generation.files
        )

        return RepairGenerationResult(
            success=True,
            original_request=request,
            repair_prompt=prompt,
            generation=generation,
            files=files,
            errors=[],
        )

    def _build_repair_prompt(
        self,
        request: str,
        repair_plan: RepairPlan,
    ) -> str:

        lines = [
            "FLOWPILOT REPAIR REQUEST",
            "",
            "ORIGINAL USER REQUEST:",
            request,
            "",
            "DIAGNOSTICS:",
        ]

        for diagnostic in (
            repair_plan.diagnostics
        ):

            lines.append(
                self._format_diagnostic(
                    diagnostic
                )
            )

        lines.extend(
            [
                "",
                "REPAIR ACTIONS:",
            ]
        )

        for action in repair_plan.actions:
            lines.append(
                f"- {action}"
            )

        lines.extend(
            [
                "",
                "REPAIR REQUIREMENTS:",
                (
                    "1. Fix the diagnosed failure."
                ),
                (
                    "2. Preserve unrelated working code."
                ),
                (
                    "3. Do not introduce unnecessary files."
                ),
                (
                    "4. Return complete file contents "
                    "for every changed file."
                ),
                (
                    "5. Use the format:"
                ),
                "",
                "FILE: relative/path/to/file.py",
                "```python",
                "# complete corrected file",
                "```",
                "",
                (
                    "6. Do not claim that tests passed "
                    "unless they actually ran."
                ),
            ]
        )

        return "\n".join(lines)

    def _format_diagnostic(
        self,
        diagnostic: Diagnostic,
    ) -> str:

        location = ""

        if diagnostic.file:
            location += (
                f" file={diagnostic.file}"
            )

        if diagnostic.line is not None:
            location += (
                f" line={diagnostic.line}"
            )

        return (
            f"- category={diagnostic.category}"
            f"{location}: "
            f"{diagnostic.message}"
        )

    def _combine_context(
        self,
        context: str,
        repair_plan: RepairPlan,
    ) -> str:

        parts = []

        if context.strip():

            parts.append(
                context.strip()
            )

        parts.append(
            "FLOWPILOT REPAIR DIAGNOSTICS:"
        )

        for diagnostic in (
            repair_plan.diagnostics
        ):

            parts.append(
                self._format_diagnostic(
                    diagnostic
                )
            )

        return "\n".join(parts)


__all__ = [
    "RepairGenerationResult",
    "RepairGenerator",
]