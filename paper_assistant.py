"""
FlowPilot Research Paper Assistant
-----------------------------------

Uses deterministic Python text search.

Features:
- Paper overview
- Keyword matching
- Relevant passage retrieval
- Page-number references
- Section lookup

No language model or machine learning is used.
"""

import re

from collections import Counter


STOP_WORDS = {

    "the", "and", "for", "that", "with",
    "this", "from", "into", "are", "was",
    "were", "have", "has", "had", "you",
    "your", "what", "when", "where", "which",
    "who", "why", "how", "does", "did",
    "can", "could", "would", "should", "about",
    "their", "there", "then", "than", "they",
    "them", "its", "our", "not", "but",
    "paper", "please", "explain", "show",
    "find", "using", "use", "give"

}


def tokenize(text: str) -> list[str]:

    words = re.findall(
        r"[A-Za-z][A-Za-z0-9_-]{2,}",
        text.lower()
    )

    return [
        word
        for word in words
        if word not in STOP_WORDS
    ]


class PaperAssistant:

    def __init__(self):

        self.paper = None

        self.sections = []

    # --------------------------------------------------
    # Attach a paper
    # --------------------------------------------------

    def set_paper(
        self,
        paper: dict,
        sections=None
    ) -> None:

        self.paper = paper

        self.sections = (
            sections
            if sections is not None
            else []
        )

    # --------------------------------------------------
    # Overview
    # --------------------------------------------------

    def overview(self) -> str:

        if not self.paper:

            return (
                "No research paper is loaded.\n"
                "Import a PDF to begin."
            )

        paper = self.paper

        text = paper.get(
            "full_text",
            ""
        )

        paragraphs = [

            re.sub(
                r"\s+",
                " ",
                paragraph
            ).strip()

            for paragraph in re.split(
                r"\n\s*\n",
                text
            )

            if len(paragraph.strip()) > 80

        ]

        opening_text = (

            "\n\n".join(
                paragraphs[:3]
            )[:2500]

            if paragraphs

            else text[:1800]

        )

        section_titles = [

            getattr(
                section,
                "title",
                str(section)
            )

            for section in self.sections

        ]

        return (
            "RESEARCH PAPER OVERVIEW\n"
            "=======================\n\n"

            f"Title: {paper.get('title') or paper.get('file_name', 'Unknown')}\n"

            f"Author: {paper.get('author', 'Unknown')}\n"

            f"Pages: {paper.get('page_count', 0)}\n"

            f"Extracted words: {paper.get('word_count', 0)}\n\n"

            "OPENING EXTRACTED TEXT\n"
            "----------------------\n"

            f"{opening_text}\n\n"

            "DETECTED SECTIONS\n"
            "-----------------\n"

            + (
                "\n".join(
                    f"- {title}"
                    for title in section_titles
                )

                if section_titles

                else "No sections detected yet."
            )

            + "\n\nThis overview is based on extracted PDF text. "
            "It is not an AI-generated summary."
        )

    # --------------------------------------------------
    # Search paper
    # --------------------------------------------------

    def search(
        self,
        query: str,
        limit: int = 5
    ) -> list[dict]:

        if not self.paper:

            return []

        query_words = set(
            tokenize(query)
        )

        if not query_words:

            return []

        results = []

        for page in self.paper.get(
            "pages",
            []
        ):

            page_number = page.get(
                "page_number",
                "?"
            )

            page_text = page.get(
                "text",
                ""
            )

            paragraphs = re.split(
                r"\n\s*\n",
                page_text
            )

            for paragraph in paragraphs:

                paragraph = paragraph.strip()

                if not paragraph:
                    continue

                word_counts = Counter(
                    tokenize(paragraph)
                )

                score = sum(
                    word_counts[word]
                    for word in query_words
                )

                if score > 0:

                    results.append({

                        "page": page_number,

                        "score": score,

                        "text": paragraph

                    })

        results.sort(
            key=lambda result: (
                -result["score"],
                str(result["page"])
            )
        )

        return results[:max(1, limit)]

    # --------------------------------------------------
    # Answer questions using retrieved evidence
    # --------------------------------------------------

    def answer(
        self,
        question: str
    ) -> str:

        if not self.paper:

            return (
                "Please import a research-paper PDF first."
            )

        question = question.strip()

        if not question:

            return "Please enter a question."

        lower_question = question.lower()

        overview_terms = (
            "overview",
            "summary",
            "summarize",
            "main idea",
            "about this paper"
        )

        if any(
            term in lower_question
            for term in overview_terms
        ):

            return self.overview()

        results = self.search(
            question,
            limit=5
        )

        if not results:

            return (
                "No relevant passage was found using "
                "the current keyword-matching method.\n\n"

                "Try using terminology directly from "
                "the research paper."
            )

        output = [

            "PAPER SEARCH RESULTS",

            "These passages were retrieved from "
            "the loaded PDF using deterministic Python search.",

            ""

        ]

        for index, result in enumerate(
            results,
            start=1
        ):

            text = re.sub(
                r"\s+",
                " ",
                result["text"]
            )

            output.append(

                f"[{index}] Page {result['page']}\n"

                f"Match score: {result['score']}\n"

                f"{text[:1200]}\n"

            )

        return "\n".join(output)

    # --------------------------------------------------
    # Section lookup
    # --------------------------------------------------

    def list_sections(self) -> str:

        if not self.sections:

            return (
                "No sections detected. "
                "Import a paper and run section analysis."
            )

        return "\n".join(

            f"{section.title}: "
            f"pages {section.start_page}-"
            f"{section.end_page}"

            for section in self.sections

        )