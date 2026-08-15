from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from flowpilot.knowledge.unified_retriever import (
    UnifiedKnowledgeRetriever,
    UnifiedRetrievalResult,
)

from flowpilot.knowledge.parser.knowledge_context_renderer import (
    KnowledgeContextRenderer,
)


@dataclass
class UnifiedPromptResult:
    query: str = ""
    success: bool = False
    prompt: str = ""
    context_text: str = ""
    errors: List[str] = field(
        default_factory=list
    )
    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


class UnifiedPromptBuilder:
    """
    Builds one grounded prompt from:

    - GNU Radio knowledge graph/source context
    - FlowPilot thesis/document context

    This class does not call an LLM.
    """

    DEFAULT_SYSTEM_INSTRUCTIONS = """
You are FlowPilot, a specialized GNU Radio, SDR,
and FlowPilot engineering assistant.

Use the supplied evidence as the primary source.

Rules:

1. Answer using the supplied evidence.
2. Do not invent implementation details.
3. Prefer exact source-code evidence when available.
4. Prefer the FlowPilot thesis when answering questions
   about FlowPilot's own architecture and components.
5. Clearly distinguish supported facts from inference.
6. If the supplied evidence is insufficient, say so.
7. Keep answers direct and technically precise.
8. Do not claim to have inspected source code unless
   source-code evidence is actually supplied.
""".strip()

    def __init__(
        self,
        retriever: UnifiedKnowledgeRetriever | None = None,
        renderer: KnowledgeContextRenderer | None = None,
        system_instructions: str | None = None,
    ) -> None:

        self.retriever = (
            retriever
            or UnifiedKnowledgeRetriever()
        )

        self.renderer = (
            renderer
            or KnowledgeContextRenderer()
        )

        self.system_instructions = (
            system_instructions.strip()
            if system_instructions
            else self.DEFAULT_SYSTEM_INSTRUCTIONS
        )

    def build(
        self,
        query: str,
    ) -> UnifiedPromptResult:

        result = UnifiedPromptResult(
            query=query or ""
        )

        query = query.strip()

        if not query:

            result.errors.append(
                "Query is empty."
            )

            return result

        try:

            retrieval = (
                self.retriever.retrieve(
                    query
                )
            )

        except Exception as exc:

            result.errors.append(
                f"Retrieval failed: {exc}"
            )

            return result

        if not retrieval.success:

            result.errors.extend(
                retrieval.errors
            )

        try:

            context_text = (
                self._render_context(
                    retrieval
                )
            )

        except Exception as exc:

            result.errors.append(
                f"Context rendering failed: {exc}"
            )

            return result

        if not context_text.strip():

            result.errors.append(
                "Retrieved context is empty."
            )

            return result

        result.context_text = (
            context_text
        )

        result.prompt = (
            self._build_prompt(
                query,
                context_text,
            )
        )

        result.metadata = (
            self._metadata(
                retrieval
            )
        )

        result.success = (
            bool(result.prompt)
            and not result.errors
        )

        return result

    def _render_context(
        self,
        retrieval: UnifiedRetrievalResult,
    ) -> str:

        parts: List[str] = []

        # =====================================================
        # GNU RADIO
        # =====================================================

        if retrieval.gnuradio is not None:

            gnuradio = (
                retrieval.gnuradio
            )

            try:

                if (
                    gnuradio.block is not None
                    or gnuradio.source_files
                    or gnuradio.classes
                    or gnuradio.methods
                    or gnuradio.functions
                    or gnuradio.bindings
                    or gnuradio.parameters
                    or gnuradio.references
                ):

                    context = gnuradio.to_context()

                    parts.append(
                        "============================================================"
                    )

                    parts.append(
                        "GNU RADIO KNOWLEDGE"
                    )

                    parts.append(
                        "============================================================"
                    )

                    parts.append(
                        self._format_dict(
                            context
                        )
                    )

            except Exception as exc:

                parts.append(
                    f"GNU Radio context formatting error: {exc}"
                )

        # =====================================================
        # THESIS
        # =====================================================

        if retrieval.thesis is not None:

            thesis_matches = (
                retrieval.thesis.matches
            )

            if thesis_matches:

                parts.append(
                    ""
                )

                parts.append(
                    "============================================================"
                )

                parts.append(
                    "FLOWPILOT THESIS KNOWLEDGE"
                )

                parts.append(
                    "============================================================"
                )

                for index, match in enumerate(
                    thesis_matches,
                    1,
                ):

                    section = (
                        match.section
                    )

                    parts.append(
                        f"\n[THESIS RESULT {index}]"
                    )

                    parts.append(
                        f"Document: {section.document}"
                    )

                    parts.append(
                        f"Section: {section.title}"
                    )

                    parts.append(
                        "Section Path: "
                        + " > ".join(
                            section.section_path
                        )
                    )

                    parts.append(
                        f"Relevance Score: {match.score:.2f}"
                    )

                    parts.append(
                        "Content:"
                    )

                    parts.append(
                        section.content
                    )

        return "\n".join(parts).strip()

    def _build_prompt(
        self,
        query: str,
        context_text: str,
    ) -> str:

        return "\n".join(
            [
                self.system_instructions,
                "",
                "============================================================",
                "USER QUESTION",
                "============================================================",
                "",
                query,
                "",
                "============================================================",
                "RETRIEVED EVIDENCE",
                "============================================================",
                "",
                context_text,
                "",
                "============================================================",
                "ANSWER REQUIREMENTS",
                "============================================================",
                "",
                "Answer the user's question using the retrieved evidence.",
                "Prefer exact implementation evidence over assumptions.",
                "For FlowPilot architecture questions, use the thesis evidence.",
                "For GNU Radio implementation questions, use source/graph evidence.",
                "If evidence is insufficient, explicitly state what is missing.",
            ]
        )

    @staticmethod
    def _format_dict(
        value: Any,
        indent: int = 0,
    ) -> str:

        if isinstance(value, dict):

            lines = []

            for key, item in value.items():

                if isinstance(
                    item,
                    (dict, list),
                ):

                    lines.append(
                        " " * indent
                        + f"{key}:"
                    )

                    lines.append(
                        UnifiedPromptBuilder._format_dict(
                            item,
                            indent + 2,
                        )
                    )

                else:

                    lines.append(
                        " " * indent
                        + f"{key}: {item}"
                    )

            return "\n".join(lines)

        if isinstance(value, list):

            lines = []

            for item in value:

                lines.append(
                    " " * indent
                    + "- "
                    + UnifiedPromptBuilder._format_dict(
                        item,
                        indent + 2,
                    )
                )

            return "\n".join(lines)

        return " " * indent + str(value)

    @staticmethod
    def _metadata(
        retrieval: UnifiedRetrievalResult,
    ) -> Dict[str, Any]:

        return {
            "retrieval": "unified",
            "gnuradio": (
                retrieval.gnuradio.summary()
                if retrieval.gnuradio
                else None
            ),
            "thesis_matches": (
                len(
                    retrieval.thesis.matches
                )
                if retrieval.thesis
                else 0
            ),
        }


__all__ = [
    "UnifiedPromptResult",
    "UnifiedPromptBuilder",
]