from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .document_store import (
    DocumentSection,
    MarkdownDocumentStore,
)


@dataclass
class DocumentMatch:
    section: DocumentSection
    score: float


@dataclass
class DocumentRetrievalResult:
    query: str
    matches: List[DocumentMatch]
    success: bool
    errors: List[str]


class ThesisDocumentRetriever:
    """
    Lightweight local retriever for FlowPilot thesis chapters.

    No API.
    No embeddings.
    No external model.
    """

    STOPWORDS = {
        "the",
        "is",
        "are",
        "was",
        "were",
        "what",
        "how",
        "why",
        "does",
        "do",
        "of",
        "a",
        "an",
        "and",
        "or",
        "to",
        "in",
        "for",
        "on",
        "with",
        "from",
        "within",
        "this",
        "that",
        "it",
        "flowpilot",
    }

    def __init__(
        self,
        root: str | Path = "docs/thesis",
    ) -> None:

        self.store = (
            MarkdownDocumentStore(root)
        )

        self.loaded = False

    def load(self) -> None:

        self.store.load()
        self.loaded = True

    def retrieve(
        self,
        query: str,
        limit: int = 5,
    ) -> DocumentRetrievalResult:

        query = query.strip()

        if not query:

            return DocumentRetrievalResult(
                query="",
                matches=[],
                success=False,
                errors=[
                    "Query is empty."
                ],
            )

        try:

            if not self.loaded:
                self.load()

            if not self.store.sections:

                return DocumentRetrievalResult(
                    query=query,
                    matches=[],
                    success=False,
                    errors=[
                        "No thesis sections found."
                    ],
                )

            query_terms = self._terms(
                query
            )

            matches = []

            for section in (
                self.store.sections
            ):

                score = self._score(
                    query_terms,
                    section,
                )

                if score <= 0:
                    continue

                matches.append(
                    DocumentMatch(
                        section=section,
                        score=score,
                    )
                )

            matches.sort(
                key=lambda item: item.score,
                reverse=True,
            )

            return DocumentRetrievalResult(
                query=query,
                matches=matches[:limit],
                success=True,
                errors=[],
            )

        except Exception as exc:

            return DocumentRetrievalResult(
                query=query,
                matches=[],
                success=False,
                errors=[
                    f"{type(exc).__name__}: {exc}"
                ],
            )

    def _terms(
        self,
        query: str,
    ) -> List[str]:

        terms = re.findall(
            r"[A-Za-z0-9_]+",
            query.lower(),
        )

        return [
            term
            for term in terms
            if term not in self.STOPWORDS
            and len(term) > 1
        ]

    def _score(
        self,
        query_terms: List[str],
        section: DocumentSection,
    ) -> float:

        if not query_terms:
            return 0.0

        title = section.title.lower()

        path = " ".join(
            section.section_path
        ).lower()

        content = (
            section.content.lower()
        )

        score = 0.0

        for term in query_terms:

            if term in title:
                score += 10.0

            if term in path:
                score += 5.0

            occurrences = content.count(
                term
            )

            score += min(
                occurrences,
                5,
            )

        # Exact phrase gets additional weight.
        query_phrase = " ".join(
            query_terms
        )

        if query_phrase in content:
            score += 10.0

        return score