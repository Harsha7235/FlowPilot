"""
FlowPilot - Research Paper Section Extractor

AI-free section detection using Python rules and regular expressions.
Preserves page references and extracts text belonging to each section.
"""

import re
from dataclasses import asdict, dataclass


@dataclass
class PaperSection:
    title: str
    start_page: int
    end_page: int
    text: str


class SectionExtractor:
    """Detect and extract research-paper sections from PDF page text."""

    KNOWN_HEADINGS = {
        "abstract",
        "introduction",
        "background",
        "related work",
        "literature review",
        "problem statement",
        "system model",
        "methodology",
        "proposed method",
        "proposed methodology",
        "materials and methods",
        "methods",
        "experimental setup",
        "implementation",
        "results",
        "results and discussion",
        "discussion",
        "performance analysis",
        "performance evaluation",
        "simulation results",
        "experimental results",
        "conclusion",
        "conclusions",
        "future work",
        "limitations",
        "references",
        "acknowledgment",
        "acknowledgments",
        "acknowledgements",
        "appendix",
        "appendices",
    }

    NUMBER_PREFIX = re.compile(
        r"^\s*(?:"
        r"\d+(?:\.\d+)*\.?"
        r"|[IVXLCDM]+\.?"
        r")\s+(.+?)\s*$",
        re.IGNORECASE,
    )

    def normalize_heading(self, line: str) -> str:
        """Normalize heading text for comparisons."""
        line = re.sub(r"\s+", " ", line.strip())
        line = line.strip(" .:-–—")
        return line.casefold()

    def detect_heading(self, line: str):
        """
        Return a detected heading or None.

        Detection uses known section names, numbered headings,
        and conservative uppercase-heading rules.
        """

        cleaned = re.sub(r"\s+", " ", line.strip())

        if not cleaned or len(cleaned) > 120:
            return None

        normalized = self.normalize_heading(cleaned)

        # Known unnumbered headings.
        if normalized in self.KNOWN_HEADINGS:
            return cleaned

        # Known numbered headings, for example:
        # "1. Introduction"
        # "III. Methodology"
        match = self.NUMBER_PREFIX.match(cleaned)

        if match:
            candidate = match.group(1).strip()
            candidate_normalized = self.normalize_heading(candidate)

            if candidate_normalized in self.KNOWN_HEADINGS:
                return candidate

            # Recognize plausible numbered subsection headings.
            # Restrict length and punctuation to reduce false positives.
            if (
                len(candidate) <= 90
                and len(candidate.split()) <= 12
                and not candidate.endswith((".", ",", ";"))
                and not re.search(r"[=<>]{2,}", candidate)
            ):
                return candidate

        # Recognize uppercase headings such as:
        # "SYSTEM MODEL" or "EXPERIMENTAL RESULTS".
        if (
            cleaned.isupper()
            and len(cleaned.split()) <= 10
            and len(cleaned) <= 80
            and any(char.isalpha() for char in cleaned)
            and not cleaned.endswith((".", ",", ";"))
        ):
            return cleaned

        return None

    def extract(self, pages: list[dict]) -> list[PaperSection]:
        """
        Extract sections from a list of PDF pages.

        Expected input:
            [
                {"page_number": 1, "text": "..."},
                {"page_number": 2, "text": "..."}
            ]

        Each section contains its title, start page, end page,
        and extracted body text.

        Text before the first recognized heading is preserved in
        a section named "Opening Content" when it is non-empty.
        """

        sections = []
        current = None

        for page in pages:
            page_number = int(page["page_number"])
            page_text = page.get("text", "")

            for line in page_text.splitlines():
                heading = self.detect_heading(line)

                if heading is not None:
                    # Finish the previous section.
                    if current is not None:
                        current["end_page"] = page_number

                    current = {
                        "title": heading,
                        "start_page": page_number,
                        "end_page": page_number,
                        "text_lines": [],
                    }

                    sections.append(current)

                elif current is not None:
                    current["text_lines"].append(line)

                elif line.strip():
                    # Preserve the title, authors, and other content
                    # appearing before the first recognized heading.
                    current = {
                        "title": "Opening Content",
                        "start_page": page_number,
                        "end_page": page_number,
                        "text_lines": [line],
                    }
                    sections.append(current)

        # Convert the internal representation into dataclasses.
        result = []

        for index, item in enumerate(sections):
            start_page = item["start_page"]

            if index + 1 < len(sections):
                next_start_page = sections[index + 1]["start_page"]
                end_page = max(start_page, next_start_page)
            else:
                end_page = max(start_page, item["end_page"])

            result.append(
                PaperSection(
                    title=item["title"],
                    start_page=start_page,
                    end_page=end_page,
                    text="\n".join(item["text_lines"]).strip(),
                )
            )

        return result

    @staticmethod
    def to_dict(sections: list[PaperSection]) -> list[dict]:
        """Convert sections into dictionaries for JSON or database storage."""
        return [asdict(section) for section in sections]