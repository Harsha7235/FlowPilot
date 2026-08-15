
"""Shared utility functions for the FlowPilot Agentic AI Platform.
 
This module collects small, dependency-light, stateless helper functions
that are reused across FlowPilot's subsystems: the Repository Scanner,
the Autonomous Knowledge Acquisition System (AKAS), the Repository
Discovery Engine, the various parsers, the Knowledge Warehouse, the
Neo4j Knowledge Graph, the Embedding Engine, the Planner, the Generator,
the Validator, the API layer, and the Frontend.
 
Every function here is intentionally free of business logic and free of
platform-specific assumptions beyond what the standard library and
:mod:`pathlib` provide. Functions in this module are safe to import from
anywhere in the codebase without introducing circular dependencies.
 
Typical usage example:
 
    logger = configure_logger("flowpilot.scanner")
    digest = sha256_file(Path("README.md"))
    save_json(Path("out/report.json"), {"digest": digest})
"""
 
from __future__ import annotations
 
import hashlib
import json
import logging
import mimetypes
import sys
from datetime import datetime, timezone
from logging import Logger
from pathlib import Path
from typing import Any, Iterator, Optional, Type, Union
 
__all__ = [
    "configure_logger",
    "save_json",
    "load_json",
    "sha256_file",
    "utc_now",
    "normalize_path",
    "ensure_exists",
    "recursive_files",
    "recursive_directories",
    "detect_mime",
    "file_extension",
    "safe_mkdir",
    "format_size",
    "is_git_repository",
    "repository_name",
]
 
_DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DEFAULT_LOG_DATEFMT = "%Y-%m-%dT%H:%M:%S%z"
_HASH_CHUNK_SIZE = 1024 * 1024
_SIZE_UNITS = ("B", "KB", "MB", "GB", "TB", "PB", "EB")
 
 
# =====================================================================
# LOGGING
# =====================================================================
 
 
def configure_logger(
    name: str,
    *,
    level: int = logging.INFO,
    log_file: Optional[Union[str, Path]] = None,
    propagate: bool = False,
) -> Logger:
    """Configures and returns a named :class:`~logging.Logger`.
 
    Attaches a stream handler writing to ``stdout`` and, optionally, a
    file handler writing to ``log_file``. Calling this function multiple
    times with the same ``name`` will not duplicate handlers; existing
    handlers on the logger are removed and replaced.
 
    Args:
        name: The dotted logger name (e.g. ``"flowpilot.scanner"``).
        level: The minimum severity level the logger will emit. Defaults
            to :data:`logging.INFO`.
        log_file: An optional path to a file that log records should
            also be written to. Parent directories are created if they
            do not already exist.
        propagate: Whether log records should propagate to ancestor
            loggers. Defaults to ``False`` to avoid duplicate output when
            the root logger is also configured.
 
    Returns:
        A fully configured :class:`~logging.Logger` instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = propagate
 
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
 
    formatter = logging.Formatter(fmt=_DEFAULT_LOG_FORMAT, datefmt=_DEFAULT_LOG_DATEFMT)
 
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
 
    if log_file is not None:
        resolved_log_file = normalize_path(log_file)
        safe_mkdir(resolved_log_file.parent)
        file_handler = logging.FileHandler(resolved_log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
 
    return logger
 
 
# =====================================================================
# JSON I/O
# =====================================================================
 
 
def save_json(
    path: Union[str, Path],
    data: Any,
    *,
    indent: Optional[int] = 2,
    sort_keys: bool = False,
    encoder: Optional[Type[json.JSONEncoder]] = None,
) -> Path:
    """Serializes ``data`` to JSON and writes it to disk.
 
    Parent directories of ``path`` are created automatically if they do
    not already exist.
 
    Args:
        path: The destination file path.
        data: A JSON-serializable object, or an object serializable by
            ``encoder`` (e.g. FlowPilot's ``ModelEncoder``).
        indent: The indentation level passed to :func:`json.dumps`.
            Defaults to ``2``. Pass ``None`` for compact output.
        sort_keys: Whether to sort dictionary keys alphabetically.
        encoder: An optional :class:`json.JSONEncoder` subclass used to
            serialize non-natively-serializable objects (e.g. FlowPilot
            model instances containing ``Path``, ``datetime``, or
            ``Enum`` fields).
 
    Returns:
        The resolved :class:`~pathlib.Path` the JSON payload was written
        to.
    """
    resolved_path = normalize_path(path)
    safe_mkdir(resolved_path.parent)
    payload = json.dumps(data, indent=indent, sort_keys=sort_keys, cls=encoder)
    resolved_path.write_text(payload, encoding="utf-8")
    return resolved_path
 
 
def load_json(path: Union[str, Path]) -> Any:
    """Reads and parses a JSON file from disk.
 
    Args:
        path: The path to the JSON file to load.
 
    Returns:
        The parsed JSON content (typically a ``dict`` or ``list``).
 
    Raises:
        FileNotFoundError: If ``path`` does not exist.
        json.JSONDecodeError: If the file does not contain valid JSON.
    """
    resolved_path = ensure_exists(path)
    with resolved_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
 
 
# =====================================================================
# HASHING
# =====================================================================
 
 
def sha256_file(path: Union[str, Path]) -> str:
    """Computes the SHA-256 hex digest of a file's contents.
 
    The file is read in fixed-size chunks so that arbitrarily large
    files can be hashed without loading their entire contents into
    memory.
 
    Args:
        path: The path to the file to hash.
 
    Returns:
        The lowercase hexadecimal SHA-256 digest of the file's contents.
 
    Raises:
        FileNotFoundError: If ``path`` does not exist.
        IsADirectoryError: If ``path`` refers to a directory.
    """
    resolved_path = ensure_exists(path)
    if resolved_path.is_dir():
        raise IsADirectoryError(f"Cannot hash a directory: {resolved_path}")
 
    digest = hashlib.sha256()
    with resolved_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()
 
 
# =====================================================================
# TIME
# =====================================================================
 
 
def utc_now() -> datetime:
    """Returns the current UTC time as a timezone-aware ``datetime``.
 
    Returns:
        The current timezone-aware :class:`~datetime.datetime` in UTC.
    """
    return datetime.now(timezone.utc)
 
 
# =====================================================================
# PATH HELPERS
# =====================================================================
 
 
def normalize_path(path: Union[str, Path]) -> Path:
    """Normalizes a path into an absolute, user-expanded :class:`Path`.
 
    Expands a leading ``~`` to the user's home directory and resolves
    the path to an absolute form without requiring the path to exist.
 
    Args:
        path: A path string or :class:`~pathlib.Path` instance.
 
    Returns:
        The normalized, absolute :class:`~pathlib.Path`.
    """
    return Path(path).expanduser().resolve()
 
 
def ensure_exists(path: Union[str, Path]) -> Path:
    """Normalizes a path and verifies that it exists on disk.
 
    Args:
        path: A path string or :class:`~pathlib.Path` instance.
 
    Returns:
        The normalized, absolute :class:`~pathlib.Path`.
 
    Raises:
        FileNotFoundError: If the normalized path does not exist.
    """
    resolved_path = normalize_path(path)
    if not resolved_path.exists():
        raise FileNotFoundError(f"Path does not exist: {resolved_path}")
    return resolved_path
 
 
def safe_mkdir(path: Union[str, Path]) -> Path:
    """Creates a directory (and any missing parents), idempotently.
 
    Does not raise if the directory already exists.
 
    Args:
        path: The directory path to create.
 
    Returns:
        The normalized, absolute :class:`~pathlib.Path` of the created
        (or already-existing) directory.
 
    Raises:
        FileExistsError: If ``path`` already exists as a non-directory
            file.
    """
    resolved_path = normalize_path(path)
    if resolved_path.exists() and not resolved_path.is_dir():
        raise FileExistsError(f"Path exists and is not a directory: {resolved_path}")
    resolved_path.mkdir(parents=True, exist_ok=True)
    return resolved_path
 
 
def recursive_files(
    root: Union[str, Path],
    *,
    pattern: str = "*",
    include_hidden: bool = False,
) -> Iterator[Path]:
    """Recursively yields every file beneath ``root`` matching ``pattern``.
 
    Args:
        root: The directory to walk.
        pattern: A glob pattern applied to each candidate path via
            :meth:`~pathlib.Path.match`. Defaults to ``"*"`` (all files).
        include_hidden: Whether to include files whose name, or whose
            containing directory name, begins with a dot.
 
    Yields:
        Each matching file, as a :class:`~pathlib.Path`, in the order
        returned by :meth:`~pathlib.Path.rglob`.
 
    Raises:
        FileNotFoundError: If ``root`` does not exist.
        NotADirectoryError: If ``root`` is not a directory.
    """
    resolved_root = ensure_exists(root)
    if not resolved_root.is_dir():
        raise NotADirectoryError(f"Not a directory: {resolved_root}")
 
    for candidate in resolved_root.rglob(pattern):
        if not candidate.is_file():
            continue
        if not include_hidden and _has_hidden_component(candidate, resolved_root):
            continue
        yield candidate
 
 
def recursive_directories(
    root: Union[str, Path],
    *,
    include_hidden: bool = False,
) -> Iterator[Path]:
    """Recursively yields every directory beneath ``root``.
 
    Args:
        root: The directory to walk.
        include_hidden: Whether to include directories whose name, or
            whose containing directory name, begins with a dot.
 
    Yields:
        Each matching subdirectory, as a :class:`~pathlib.Path`, in the
        order returned by :meth:`~pathlib.Path.rglob`.
 
    Raises:
        FileNotFoundError: If ``root`` does not exist.
        NotADirectoryError: If ``root`` is not a directory.
    """
    resolved_root = ensure_exists(root)
    if not resolved_root.is_dir():
        raise NotADirectoryError(f"Not a directory: {resolved_root}")
 
    for candidate in resolved_root.rglob("*"):
        if not candidate.is_dir():
            continue
        if not include_hidden and _has_hidden_component(candidate, resolved_root):
            continue
        yield candidate
 
 
def _has_hidden_component(path: Path, root: Path) -> bool:
    """Determines whether any path component relative to ``root`` is hidden.
 
    Args:
        path: The path to inspect.
        root: The ancestor path that ``path`` is relative to.
 
    Returns:
        ``True`` if any component of ``path`` (relative to ``root``)
        begins with a dot.
    """
    relative = path.relative_to(root)
    return any(part.startswith(".") for part in relative.parts)
 
 
# =====================================================================
# FILE TYPE / SIZE HELPERS
# =====================================================================
 
 
def detect_mime(path: Union[str, Path]) -> str:
    """Guesses the MIME type of a file based on its name and extension.
 
    Args:
        path: The path (need not exist on disk) whose MIME type should
            be guessed.
 
    Returns:
        The guessed MIME type string, or ``"application/octet-stream"``
        if no type could be determined.
    """
    mime_type, _ = mimetypes.guess_type(str(Path(path)), strict=False)
    return mime_type or "application/octet-stream"
 
 
def file_extension(path: Union[str, Path], *, lowercase: bool = True) -> str:
    """Extracts the file extension (without the leading dot) from a path.
 
    Handles compound suffixes such as ``.block.yml`` or ``.tar.gz`` by
    returning only the final suffix component, consistent with
    :attr:`pathlib.Path.suffix`.
 
    Args:
        path: The path to inspect.
        lowercase: Whether to lowercase the returned extension. Defaults
            to ``True``.
 
    Returns:
        The file extension without its leading dot (e.g. ``"py"``), or
        an empty string if the path has no suffix.
    """
    suffix = Path(path).suffix.lstrip(".")
    return suffix.lower() if lowercase else suffix
 
 
def format_size(size_bytes: int) -> str:
    """Formats a byte count as a human-readable string.
 
    Args:
        size_bytes: The size, in bytes, to format. Must be non-negative.
 
    Returns:
        A human-readable string such as ``"1.5 MB"`` or ``"512 B"``.
 
    Raises:
        ValueError: If ``size_bytes`` is negative.
    """
    if size_bytes < 0:
        raise ValueError(f"size_bytes must be non-negative, got {size_bytes}")
 
    size = float(size_bytes)
    for unit in _SIZE_UNITS:
        if size < 1024.0 or unit == _SIZE_UNITS[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} {_SIZE_UNITS[-1]}"  # pragma: no cover - unreachable safeguard
 
 
# =====================================================================
# GIT REPOSITORY HELPERS
# =====================================================================
 
 
def is_git_repository(path: Union[str, Path]) -> bool:
    """Determines whether ``path`` is (or is inside) a Git repository.
 
    A directory is considered a Git repository if it, or any of its
    ancestors, contains a ``.git`` entry (either a directory, for a
    standard clone, or a file, for a Git worktree or submodule).
 
    Args:
        path: The path to inspect.
 
    Returns:
        ``True`` if ``path`` is inside a Git repository, ``False``
        otherwise (including when ``path`` does not exist).
    """
    resolved_path = normalize_path(path)
    if not resolved_path.exists():
        return False
 
    current = resolved_path if resolved_path.is_dir() else resolved_path.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return True
    return False
 
 
def repository_name(path: Union[str, Path]) -> str:
    """Derives a repository's canonical name from its path.
 
    If ``path`` points to a Git repository, the name of the repository
    root directory is returned. Otherwise, the name of ``path`` itself
    is returned. Any trailing ``.git`` suffix is stripped.
 
    Args:
        path: The path to a repository clone (or any directory).
 
    Returns:
        The derived repository name.
 
    Raises:
        FileNotFoundError: If ``path`` does not exist.
    """
    resolved_path = ensure_exists(path)
    current = resolved_path if resolved_path.is_dir() else resolved_path.parent
 
    root = current
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            root = candidate
            break
 
    name = root.name
    if name.endswith(".git"):
        name = name[: -len(".git")]
    return name