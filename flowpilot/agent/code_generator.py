from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from flowpilot.agent.inference import (
    InferenceEngine,
)


@dataclass
class GeneratedFile:
    path: str
    content: str
    language: str = "text"
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "content": self.content,
            "language": self.language,
            "reason": self.reason,
        }


@dataclass
class GenerationResult:
    success: bool
    request: str
    files: List[GeneratedFile] = field(
        default_factory=list
    )
    explanation: str = ""
    errors: List[str] = field(
        default_factory=list
    )

    def summary(self) -> dict:
        return {
            "success": self.success,
            "request": self.request,
            "files": len(self.files),
            "errors": len(self.errors),
        }

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "request": self.request,
            "files": [
                file.to_dict()
                for file in self.files
            ],
            "explanation": self.explanation,
            "errors": list(self.errors),
        }


class CodeGenerator:
    """
    Provider-independent FlowPilot code generator.

    Flow:

        Request
           ↓
        Prompt
           ↓
        InferenceEngine
           ↓
        Generated text
           ↓
        GeneratedFile objects
    """

    SYSTEM_PROMPT = """
You are the FlowPilot code generation engine.

Generate technically correct software based on the
user request and supplied knowledge context.

Rules:

1. Use the supplied context as the primary source.
2. Do not invent APIs or implementation details.
3. Produce complete code when enough information exists.
4. Clearly separate explanations from code.
5. Prefer small, maintainable changes.
6. Include tests when requested.
7. Do not modify files that were not requested.
8. Never claim that code was tested unless it actually
   passed a test.
""".strip()

    def __init__(
        self,
        inference: Optional[
            InferenceEngine
        ] = None,
    ) -> None:

        self.inference = (
            inference
            or InferenceEngine()
        )

    def generate(
        self,
        request: str,
        context: str = "",
        instructions: str = "",
    ) -> GenerationResult:

        request = request.strip()

        if not request:

            return GenerationResult(
                success=False,
                request=request,
                errors=[
                    "Generation request is empty."
                ],
            )

        prompt = self._build_prompt(
            request=request,
            context=context,
            instructions=instructions,
        )

        result = self.inference.generate(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
            metadata={
                "task": "code_generation",
                "request": request,
            },
        )

        if not result.success:

            return GenerationResult(
                success=False,
                request=request,
                explanation="",
                errors=[
                    result.error
                    or "Inference failed."
                ],
            )

        text = result.text.strip()

        if not text:

            return GenerationResult(
                success=False,
                request=request,
                errors=[
                    "Inference returned empty output."
                ],
            )

        files = self._parse_generated_files(
            text
        )

        return GenerationResult(
            success=True,
            request=request,
            files=files,
            explanation=text,
        )

    def _build_prompt(
        self,
        request: str,
        context: str,
        instructions: str,
    ) -> str:

        parts = [
            "USER REQUEST:",
            request,
            "",
        ]

        if instructions.strip():

            parts.extend(
                [
                    "ADDITIONAL INSTRUCTIONS:",
                    instructions.strip(),
                    "",
                ]
            )

        if context.strip():

            parts.extend(
                [
                    "FLOWPILOT KNOWLEDGE CONTEXT:",
                    context.strip(),
                    "",
                ]
            )

        parts.extend(
            [
                "TASK:",
                (
                    "Generate the requested implementation. "
                    "When files are required, return each "
                    "file using this format:"
                ),
                "",
                "FILE: relative/path/to/file.py",
                "```python",
                "# complete file contents",
                "```",
                "",
                "After all files, provide a short explanation.",
            ]
        )

        return "\n".join(parts)

    def _parse_generated_files(
        self,
        text: str,
    ) -> List[GeneratedFile]:

        files: List[GeneratedFile] = []

        lines = text.splitlines()

        current_path: Optional[str] = None
        current_language = "text"
        current_content: List[str] = []
        inside_code = False

        for line in lines:

            stripped = line.strip()

            if stripped.startswith("FILE:"):

                if current_path is not None:

                    files.append(
                        GeneratedFile(
                            path=current_path,
                            content="\n".join(
                                current_content
                            ).rstrip()
                            + "\n",
                            language=current_language,
                        )
                    )

                current_path = (
                    stripped[5:].strip()
                )

                current_language = "text"
                current_content = []
                inside_code = False

                continue

            if (
                stripped.startswith("```")
                and current_path is not None
            ):

                if not inside_code:

                    language = (
                        stripped[3:].strip()
                    )

                    if language:
                        current_language = language

                    inside_code = True

                else:

                    inside_code = False

                continue

            if (
                current_path is not None
                and inside_code
            ):

                current_content.append(line)

        if current_path is not None:

            files.append(
                GeneratedFile(
                    path=current_path,
                    content="\n".join(
                        current_content
                    ).rstrip()
                    + "\n",
                    language=current_language,
                )
            )

        return files


__all__ = [
    "GeneratedFile",
    "GenerationResult",
    "CodeGenerator",
]