from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from flowpilot.knowledge.parser.knowledge_retriever import (
    KnowledgeRetriever,
    RetrievalResult,
)

from flowpilot.knowledge.documents import (
    ThesisDocumentRetriever,
    DocumentRetrievalResult,
)


@dataclass
class UnifiedRetrievalResult:
    """
    Combined retrieval result from:

    1. GNU Radio knowledge graph/source
    2. FlowPilot thesis/document knowledge
    """

    query: str = ""

    gnuradio: RetrievalResult | None = None

    thesis: DocumentRetrievalResult | None = None

    success: bool = False

    errors: List[str] = field(
        default_factory=list
    )

    def summary(self) -> Dict[str, Any]:

        return {
            "success": self.success,
            "query": self.query,
            "gnuradio": (
                self.gnuradio.summary()
                if self.gnuradio
                else None
            ),
            "thesis_matches": (
                len(self.thesis.matches)
                if self.thesis
                else 0
            ),
            "errors": len(self.errors),
        }


class UnifiedKnowledgeRetriever:
    """
    Coordinates FlowPilot's technical knowledge sources.

    GNU Radio:
        Knowledge graph + implementation/source knowledge.

    Thesis:
        FlowPilot's 18 architecture chapters.
    """

    def __init__(
        self,
        gnuradio: KnowledgeRetriever | None = None,
        thesis: ThesisDocumentRetriever | None = None,
    ) -> None:

        self.gnuradio = (
            gnuradio
            or KnowledgeRetriever()
        )

        self.thesis = (
            thesis
            or ThesisDocumentRetriever()
        )

        self._loaded = False

    def load(self) -> None:

        self.thesis.load()

        self._loaded = True

    def retrieve(
        self,
        query: str,
        block_id: str | None = None,
        thesis_limit: int = 5,
    ) -> UnifiedRetrievalResult:

        query = query.strip()

        result = UnifiedRetrievalResult(
            query=query
        )

        if not query:

            result.errors.append(
                "Query is empty."
            )

            return result

        try:

            if not self._loaded:
                self.load()

            # -------------------------------------------------
            # GNU RADIO RETRIEVAL
            # -------------------------------------------------

            gnuradio_result = (
                self.gnuradio.retrieve(
                    query_text=query,
                    block_id=block_id,
                )
            )

            result.gnuradio = (
                gnuradio_result
            )

            # -------------------------------------------------
            # THESIS RETRIEVAL
            # -------------------------------------------------

            thesis_result = (
                self.thesis.retrieve(
                    query=query,
                    limit=thesis_limit,
                )
            )

            result.thesis = thesis_result

            # -------------------------------------------------
            # SUCCESS
            # -------------------------------------------------

            if (
                gnuradio_result.success
                or thesis_result.success
                and bool(
                    thesis_result.matches
                )
            ):
                result.success = True

            # Thesis retrieval can legitimately return
            # no matches for a GNU Radio-only question.
            if (
                not gnuradio_result.success
                and not thesis_result.success
            ):

                result.errors.extend(
                    gnuradio_result.errors
                )

                result.errors.extend(
                    thesis_result.errors
                )

        except Exception as exc:

            result.errors.append(
                f"{type(exc).__name__}: {exc}"
            )

            result.success = False

        return result

    def to_context(
        self,
        result: UnifiedRetrievalResult,
    ) -> Dict[str, Any]:

        context: Dict[str, Any] = {
            "query": result.query,
            "gnuradio": None,
            "thesis": [],
        }

        # -----------------------------------------------------
        # GNU RADIO
        # -----------------------------------------------------

        if result.gnuradio is not None:

            context["gnuradio"] = (
                result.gnuradio.to_context()
            )

        # -----------------------------------------------------
        # THESIS
        # -----------------------------------------------------

        if result.thesis is not None:

            context["thesis"] = []

            for match in (
                result.thesis.matches
            ):

                section = match.section

                context["thesis"].append(
                    {
                        "document": (
                            section.document
                        ),
                        "title": (
                            section.title
                        ),
                        "score": (
                            match.score
                        ),
                        "section_path": list(
                            section.section_path
                        ),
                        "content": (
                            section.content
                        ),
                    }
                )

        return context