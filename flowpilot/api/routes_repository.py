from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Query


router = APIRouter(
    prefix="/api/repository",
    tags=["Repository"],
)


# ---------------------------------------------------------
# Repository root
# ---------------------------------------------------------

def _repository_root() -> Path:
    """
    Resolve the FlowPilot project root.

    routes_repository.py
        -> api/
        -> flowpilot/
        -> project root
    """

    return Path(__file__).resolve().parents[2]


# ---------------------------------------------------------
# Repository information
# ---------------------------------------------------------

@router.get("")
def repository_info() -> Dict[str, Any]:
    """
    Return basic information about the FlowPilot
    repository and its important directories.
    """

    root = _repository_root()

    return {
        "success": True,
        "repository": root.name,
        "root": str(root),
        "exists": root.exists(),
        "directories": {
            "flowpilot": (
                root / "flowpilot"
            ).exists(),
            "knowledge": (
                root / "flowpilot" / "knowledge"
            ).exists(),
            "agent": (
                root / "flowpilot" / "agent"
            ).exists(),
            "api": (
                root / "flowpilot" / "api"
            ).exists(),
        },
    }


# ---------------------------------------------------------
# Python source files
# ---------------------------------------------------------

@router.get("/files")
def repository_files(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
) -> Dict[str, Any]:
    """
    List Python source files in the FlowPilot
    project.

    This endpoint is intentionally limited to
    the FlowPilot source tree.
    """

    root = _repository_root()
    source_root = root / "flowpilot"

    if not source_root.exists():
        return {
            "success": False,
            "files": [],
            "count": 0,
            "error": "flowpilot directory not found.",
        }

    files: List[str] = []

    for path in source_root.rglob("*.py"):

        if "__pycache__" in path.parts:
            continue

        try:
            relative = path.relative_to(root)
            files.append(
                str(relative)
            )

        except ValueError:
            continue

    files.sort()

    limited = files[:limit]

    return {
        "success": True,
        "count": len(files),
        "returned": len(limited),
        "files": limited,
    }


# ---------------------------------------------------------
# File information
# ---------------------------------------------------------

@router.get("/file")
def file_info(
    path: str = Query(
        ...,
        min_length=1,
    ),
) -> Dict[str, Any]:
    """
    Return metadata for a source file.

    Only files inside the FlowPilot project are
    accepted.
    """

    root = _repository_root()

    requested = (
        root / path
    ).resolve()

    try:
        requested.relative_to(
            root.resolve()
        )

    except ValueError:

        return {
            "success": False,
            "error": (
                "Requested file is outside "
                "the FlowPilot workspace."
            ),
        }

    if not requested.exists():

        return {
            "success": False,
            "error": "File not found.",
            "path": path,
        }

    if not requested.is_file():

        return {
            "success": False,
            "error": "Path is not a file.",
            "path": path,
        }

    try:
        size = requested.stat().st_size

        line_count = 0

        if requested.suffix.lower() == ".py":

            with requested.open(
                "r",
                encoding="utf-8",
                errors="replace",
            ) as handle:

                line_count = sum(
                    1
                    for _ in handle
                )

        return {
            "success": True,
            "path": str(
                requested.relative_to(root)
            ),
            "name": requested.name,
            "extension": requested.suffix,
            "size_bytes": size,
            "line_count": line_count,
        }

    except OSError as exc:

        return {
            "success": False,
            "error": str(exc),
        }