"""
FlowPilot Knowledge Prompt Builder.

Converts a KnowledgeContext into a deterministic prompt payload
for the downstream answer-generation layer.

Pipeline:

User Query
    ->
KnowledgeRetriever
    ->
KnowledgeContextBuilder
    ->
KnowledgeContextValidator
    ->
KnowledgeContextRenderer
    ->
KnowledgePromptBuilder
    ->
Answer Generator
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from flowpilot.knowledge.parser.knowledge_context_builder import (
    KnowledgeContext,
    KnowledgeContextBuilder,
)

from flowpilot.knowledge.parser.knowledge_context_renderer import (
    KnowledgeContextRenderer,
)


@dataclass
class KnowledgePromptResult:
    """Result produced by KnowledgePromptBuilder."""

    success: bool = False
    query: str = ""
    block_id: str = ""
    context_text: str = ""
    prompt: str = ""
    errors: list[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def summary(self) -> Dict[str, Any]:
        """Return a deterministic summary."""

        return {
            "success": self.success,
            "query": self.query,
            "block_id": self.block_id,
            "context_length": len(self.context_text),
            "prompt_length": len(self.prompt),
            "errors": len(self.errors),
        }


class KnowledgePromptBuilder:
    """
    Build an answer-generation prompt from FlowPilot knowledge.

    This class does not call an LLM.

    It only prepares the knowledge and instructions that a
    downstream model/agent can consume.
    """

    DEFAULT_SYSTEM_INSTRUCTIONS = """
You are the FlowPilot technical knowledge assistant.

Answer the user's question using the supplied FlowPilot knowledge
context as the primary source.

Rules:

1. Use the supplied knowledge context as the authoritative source.
2. Do not invent implementation details that are absent from the context.
3. Distinguish directly supported facts from reasonable inferences.
4. When implementation details are available, explain them clearly.
5. Mention relevant source files, classes, methods, functions,
   parameters, bindings, inheritance, and references when useful.
6. Keep the answer technically precise.
7. If the knowledge context does not contain enough information,
   explicitly say what information is missing.
8. Do not claim that code was inspected if the context does not
   contain that information.
""".strip()

    def __init__(
        self,
        context_builder: Optional[
            KnowledgeContextBuilder
        ] = None,
        renderer: Optional[
            KnowledgeContextRenderer
        ] = None,
        system_instructions: Optional[str] = None,
    ) -> None:

        self.context_builder = (
            context_builder
            if context_builder is not None
            else KnowledgeContextBuilder()
        )

        self.renderer = (
            renderer
            if renderer is not None
            else KnowledgeContextRenderer()
        )

        self.system_instructions = (
            system_instructions.strip()
            if system_instructions
            else self.DEFAULT_SYSTEM_INSTRUCTIONS
        )

    # ======================================================================
    # Public API
    # ======================================================================

    def build(
        self,
        query: str,
    ) -> KnowledgePromptResult:
        """
        Retrieve/build/render knowledge and create the final prompt.
        """

        result = KnowledgePromptResult(
            query=query or ""
        )

        if not query or not query.strip():
            result.errors.append(
                "Query is empty."
            )
            return result

        try:
            context_result = (
                self.context_builder.build(
                    query.strip()
                )
            )

        except Exception as exc:
            result.errors.append(
                f"Knowledge context build failed: {exc}"
            )
            return result

        if context_result is None:
            result.errors.append(
                "Knowledge context builder returned no result."
            )
            return result

        context = getattr(
            context_result,
            "context",
            None,
        )

        if context is None:
            result.errors.append(
                "Knowledge context is missing."
            )
            return result

        result.block_id = str(
            getattr(
                context,
                "block_id",
                "",
            )
            or ""
        )

        context_errors = list(
            getattr(
                context,
                "errors",
                [],
            )
            or []
        )

        if context_errors:
            result.errors.extend(
                str(error)
                for error in context_errors
            )

        try:
            context_text = (
                self.renderer.render(
                    context
                )
            )

        except Exception as exc:
            result.errors.append(
                f"Knowledge context rendering failed: {exc}"
            )
            return result

        if not context_text.strip():
            result.errors.append(
                "Rendered knowledge context is empty."
            )
            return result

        result.context_text = (
            context_text
        )

        result.prompt = (
            self._build_prompt(
                query=query.strip(),
                context=context,
                context_text=context_text,
            )
        )

        result.metadata = (
            self._build_metadata(
                context
            )
        )

        result.success = (
            len(result.errors) == 0
        )

        return result

    def build_from_context(
        self,
        query: str,
        context: KnowledgeContext,
    ) -> KnowledgePromptResult:
        """
        Build a prompt from an already-created KnowledgeContext.

        This avoids running retrieval/context building again.
        """

        result = KnowledgePromptResult(
            query=query or ""
        )

        if not query or not query.strip():
            result.errors.append(
                "Query is empty."
            )
            return result

        if context is None:
            result.errors.append(
                "Knowledge context is missing."
            )
            return result

        result.block_id = str(
            getattr(
                context,
                "block_id",
                "",
            )
            or ""
        )

        context_errors = list(
            getattr(
                context,
                "errors",
                [],
            )
            or []
        )

        if context_errors:
            result.errors.extend(
                str(error)
                for error in context_errors
            )

        try:
            context_text = (
                self.renderer.render(
                    context
                )
            )

        except Exception as exc:
            result.errors.append(
                f"Knowledge context rendering failed: {exc}"
            )
            return result

        result.context_text = (
            context_text
        )

        result.prompt = (
            self._build_prompt(
                query=query.strip(),
                context=context,
                context_text=context_text,
            )
        )

        result.metadata = (
            self._build_metadata(
                context
            )
        )

        result.success = (
            len(result.errors) == 0
        )

        return result

    # ======================================================================
    # Prompt construction
    # ======================================================================

    def _build_prompt(
        self,
        query: str,
        context: KnowledgeContext,
        context_text: str,
    ) -> str:

        block_found = bool(
            getattr(
                context,
                "block_found",
                False,
            )
        )

        block_id = str(
            getattr(
                context,
                "block_id",
                "",
            )
            or ""
        )

        parts = [
            self.system_instructions,
            "",
            "============================================================",
            "USER QUESTION",
            "============================================================",
            "",
            query,
            "",
            "============================================================",
            "FLOWPILOT KNOWLEDGE CONTEXT",
            "============================================================",
            "",
            context_text,
            "",
            "============================================================",
            "ANSWER REQUIREMENTS",
            "============================================================",
            "",
            f"Block found: {block_found}",
            f"Block ID: {block_id}",
            "",
            "Answer the user's question using the knowledge context.",
            "Prefer concrete implementation evidence.",
            "If the context is insufficient, state that explicitly.",
        ]

        return "\n".join(
            parts
        )

    # ======================================================================
    # Metadata
    # ======================================================================

    @staticmethod
    def _build_metadata(
        context: KnowledgeContext,
    ) -> Dict[str, Any]:

        return {
            "block_found": bool(
                getattr(
                    context,
                    "block_found",
                    False,
                )
            ),
            "source_files": len(
                getattr(
                    context,
                    "source_files",
                    [],
                )
                or []
            ),
            "classes": len(
                getattr(
                    context,
                    "classes",
                    [],
                )
                or []
            ),
            "methods": len(
                getattr(
                    context,
                    "methods",
                    [],
                )
                or []
            ),
            "functions": len(
                getattr(
                    context,
                    "functions",
                    [],
                )
                or []
            ),
            "bindings": len(
                getattr(
                    context,
                    "bindings",
                    [],
                )
                or []
            ),
            "parameters": len(
                getattr(
                    context,
                    "parameters",
                    [],
                )
                or []
            ),
            "inherited_classes": len(
                getattr(
                    context,
                    "inherited_classes",
                    [],
                )
                or []
            ),
            "references": len(
                getattr(
                    context,
                    "references",
                    [],
                )
                or []
            ),
        }


# ==========================================================================
# Convenience function
# ==========================================================================


def build_knowledge_prompt(
    query: str,
) -> KnowledgePromptResult:
    """
    Convenience wrapper for building a FlowPilot knowledge prompt.
    """

    return KnowledgePromptBuilder().build(
        query
    )


__all__ = [
    "KnowledgePromptBuilder",
    "KnowledgePromptResult",
    "build_knowledge_prompt",
]