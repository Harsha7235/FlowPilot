from pathlib import Path
from typing import List


DEFAULT_IGNORED = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "build",
    "dist",
}


def search_code(
    root: str,
    query: str,
    extensions: List[str] | None = None,
) -> List[dict]:
    """
    Search for text inside source-code files.

    Returns:
        [
            {
                "file": "...",
                "line": 10,
                "text": "matching line"
            }
        ]
    """

    root_path = Path(root)

    if not root_path.exists():
        raise FileNotFoundError(f"Directory not found: {root}")

    results = []

    if extensions:
        extensions = {
            ext if ext.startswith(".") else f".{ext}"
            for ext in extensions
        }

    for path in root_path.rglob("*"):

        if not path.is_file():
            continue

        # Ignore unwanted directories
        if any(part in DEFAULT_IGNORED for part in path.parts):
            continue

        # Filter extensions if requested
        if extensions and path.suffix not in extensions:
            continue

        try:
            content = path.read_text(
                encoding="utf-8",
                errors="ignore"
            )
        except Exception:
            continue

        for line_number, line in enumerate(
            content.splitlines(),
            start=1
        ):
            if query.lower() in line.lower():
                results.append(
                    {
                        "file": str(path),
                        "line": line_number,
                        "text": line.strip(),
                    }
                )

    return results