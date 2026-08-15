from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class DocumentSection:
    document: str
    title: str
    content: str
    level: int
    section_path: List[str] = field(
        default_factory=list
    )

    def searchable_text(self) -> str:
        return (
            self.title
            + "\n"
            + " ".join(self.section_path)
            + "\n"
            + self.content
        )


class MarkdownDocumentStore:
    """
    Loads Markdown documents and splits them by headings.
    """

    def __init__(
        self,
        root: str | Path,
    ) -> None:

        self.root = Path(root)
        self.sections: List[
            DocumentSection
        ] = []

    def load(self) -> None:

        self.sections.clear()

        if not self.root.exists():
            return

        for path in sorted(
            self.root.glob("Chap_*.md")
        ):

            self._load_file(path)

    def _load_file(
        self,
        path: Path,
    ) -> None:

        text = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        lines = text.splitlines()

        current_title = path.stem
        current_level = 1
        current_content: List[str] = []
        section_path: List[str] = []

        def flush() -> None:

            content = "\n".join(
                current_content
            ).strip()

            if not content:
                return

            self.sections.append(
                DocumentSection(
                    document=path.name,
                    title=current_title,
                    content=content,
                    level=current_level,
                    section_path=list(
                        section_path
                    ),
                )
            )

        for line in lines:

            stripped = line.strip()

            if (
                stripped.startswith("#")
                and not stripped.startswith(
                    "### "
                )
            ):

                if stripped.startswith(
                    "## "
                ):
                    level = 2

                elif stripped.startswith(
                    "# "
                ):
                    level = 1

                else:
                    continue

                flush()

                current_title = (
                    stripped[level + 1:]
                    .strip()
                )

                current_level = level

                if level == 1:
                    section_path = [
                        current_title
                    ]

                else:
                    section_path = (
                        section_path[:1]
                        + [current_title]
                    )

                current_content.clear()

            elif stripped.startswith(
                "### "
            ):

                flush()

                current_title = (
                    stripped[4:].strip()
                )

                current_level = 3

                section_path = (
                    section_path[:2]
                    + [current_title]
                )

                current_content.clear()

            else:

                current_content.append(
                    line
                )

        flush()

    def count(self) -> int:
        return len(self.sections)

    def documents(self) -> List[str]:

        return sorted(
            {
                section.document
                for section in self.sections
            }
        )