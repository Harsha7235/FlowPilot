from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from flowpilot.agent.code_generator import (
    CodeGenerator,
    GenerationResult,
)

from flowpilot.knowledge.unified_prompt_builder import (
    UnifiedPromptBuilder,
)


@dataclass
class GenerationRequest:
    query: str
    prompt: str
    block_id: Optional[str] = None
    context_length: int = 0

    def summary(self) -> dict:
        return {
            "query": self.query,
            "block_id": self.block_id,
            "prompt_length": len(self.prompt),
            "context_length": self.context_length,
        }


@dataclass
class GenerationPipelineResult:
    success: bool
    request: str
    generation_request: Optional[
        GenerationRequest
    ] = None

    generation: Optional[
        GenerationResult
    ] = None

    errors: List[str] = field(
        default_factory=list
    )

    def summary(self) -> dict:
        return {
            "success": self.success,
            "request": self.request,
            "prompt_ready": (
                self.generation_request
                is not None
            ),
            "generated": (
                self.generation
                is not None
            ),
            "errors": len(
                self.errors
            ),
        }


class GenerationPipeline:
    """
    Main FlowPilot answer-generation pipeline.

    Pipeline:

        User request
             ↓
        UnifiedPromptBuilder
             ↓
        GNU Radio knowledge
             +
        FlowPilot thesis knowledge
             ↓
        GenerationRequest
             ↓
        CodeGenerator
             ↓
        InferenceEngine
             ↓
        FlowPilot model
    """

    def __init__(
        self,
        prompt_builder: Optional[
            UnifiedPromptBuilder
        ] = None,
        generator: Optional[
            CodeGenerator
        ] = None,
    ) -> None:

        self.prompt_builder = (
            prompt_builder
            or UnifiedPromptBuilder()
        )

        self.generator = (
            generator
            or CodeGenerator()
        )

    def prepare(
        self,
        query: str,
    ) -> GenerationPipelineResult:

        query = query.strip()

        if not query:

            return GenerationPipelineResult(
                success=False,
                request=query,
                errors=[
                    "Generation query is empty."
                ],
            )

        try:

            prompt_result = (
                self.prompt_builder.build(
                    query
                )
            )

            if not prompt_result.success:

                return GenerationPipelineResult(
                    success=False,
                    request=query,
                    errors=list(
                        prompt_result.errors
                    ),
                )

            prompt = (
                prompt_result.prompt
            )

            if not prompt.strip():

                return GenerationPipelineResult(
                    success=False,
                    request=query,
                    errors=[
                        "Generated prompt is empty."
                    ],
                )

            metadata = (
                prompt_result.metadata
                or {}
            )

            block_id = None

            gnuradio_metadata = (
                metadata.get(
                    "gnuradio"
                )
            )

            if isinstance(
                gnuradio_metadata,
                dict,
            ):

                block_id = (
                    gnuradio_metadata
                    .get("block_id")
                )

            generation_request = (
                GenerationRequest(
                    query=query,
                    prompt=prompt,
                    block_id=block_id,
                    context_length=len(
                        prompt
                    ),
                )
            )

            return GenerationPipelineResult(
                success=True,
                request=query,
                generation_request=(
                    generation_request
                ),
            )

        except Exception as exc:

            return GenerationPipelineResult(
                success=False,
                request=query,
                errors=[
                    f"{type(exc).__name__}: {exc}"
                ],
            )

    def generate(
        self,
        query: str,
    ) -> GenerationPipelineResult:

        prepared = self.prepare(
            query
        )

        if not prepared.success:

            return prepared

        generation_request = (
            prepared.generation_request
        )

        if generation_request is None:

            return GenerationPipelineResult(
                success=False,
                request=query,
                errors=[
                    "Generation request was not created."
                ],
            )

        try:

            generation = (
                self.generator.generate(
                    request=(
                        generation_request.query
                    ),
                    context=(
                        generation_request.prompt
                    ),
                )
            )

            return GenerationPipelineResult(
                success=generation.success,
                request=query,
                generation_request=(
                    generation_request
                ),
                generation=generation,
                errors=list(
                    generation.errors
                ),
            )

        except Exception as exc:

            return GenerationPipelineResult(
                success=False,
                request=query,
                generation_request=(
                    generation_request
                ),
                errors=[
                    f"{type(exc).__name__}: {exc}"
                ],
            )


__all__ = [
    "GenerationRequest",
    "GenerationPipelineResult",
    "GenerationPipeline",
]