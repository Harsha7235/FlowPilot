from pathlib import Path

import pymupdf


class PDFReader:
    """Extract text from PDF research papers while preserving page numbers."""

    def read(self, pdf_path: str) -> dict:
        path = Path(pdf_path)

        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")

        if path.suffix.lower() != ".pdf":
            raise ValueError("Please select a PDF file.")

        pages = []

        with pymupdf.open(path) as document:
            if document.page_count == 0:
                raise ValueError("The selected PDF contains no pages.")

            metadata = document.metadata or {}

            for index, page in enumerate(document):
                text = page.get_text("text", sort=True).strip()

                pages.append({
                    "page_number": index + 1,
                    "text": text,
                    "word_count": len(text.split()),
                    "has_text": bool(text),
                })

        full_text = "\n\n".join(
            f"[Page {page['page_number']}]\n{page['text']}"
            for page in pages
        )

        return {
            "file_path": str(path.resolve()),
            "file_name": path.name,
            "title": metadata.get("title") or path.stem,
            "author": metadata.get("author") or "Unknown",
            "page_count": len(pages),
            "word_count": sum(page["word_count"] for page in pages),
            "pages": pages,
            "full_text": full_text,
            "empty_pages": [
                page["page_number"]
                for page in pages
                if not page["has_text"]
            ],
        }