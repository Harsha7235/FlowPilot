"""Repository type and Git metadata detection for the FlowPilot Repository Scanner.
 
This module provides :class:`RepositoryDetector`, which inspects a
repository's on-disk structure and Git history to classify it as a GNU
Radio core repository, an out-of-tree (OOT) module, a hardware SDK, or an
unknown repository type, and to collect its top-level identifying
metadata.
 
Two structural problems are handled explicitly, because third-party
sources are rarely laid out as a bare, single-level Git clone:
 
* **Wrapper directories.** Archive extraction (e.g. a GitHub source
  tarball) often nests the actual project one level deeper, producing
  paths such as ``third_party/gnuradio-main/gnuradio-main/``. A
  directory with exactly one subdirectory and none of its own
  repository markers is treated as a wrapper, and detection descends
  into it (repeating as needed) until an actual repository root is
  found.
* **Ancestor Git bleed.** Repository identity and Git metadata are
  derived *only* from the resolved repository root itself, never by
  walking upward through parent directories. A directory that has no
  ``.git`` of its own reports no branch, remote, or commit hash, rather
  than silently inheriting a parent repository's (e.g. FlowPilot's own)
  Git metadata.
"""
 
from __future__ import annotations
 
import logging
import re
import subprocess
from pathlib import Path
from typing import List, Optional
 
from flowpilot.core.exceptions import InvalidRepositoryError, RepositoryNotFoundError
from flowpilot.core.models import RepositoryMetadata, RepositoryType
from flowpilot.core.utils import configure_logger, ensure_exists
 
__all__ = ["RepositoryDetector", "looks_like_repository_root"]
 
_GIT_TIMEOUT_SECONDS = 10
_CMAKE_SCAN_DEPTH = 2
_MAX_CMAKE_FILES = 25
_WRAPPER_MAX_DEPTH = 5
 
_ROOT_MARKER_FILES = (
    "CMakeLists.txt",
    "setup.py",
    "pyproject.toml",
    "setup.cfg",
    "package.xml",
)
 
_GNU_RADIO_NAME_MARKERS = ("gnuradio", "gnu-radio", "gnu_radio")
_GNU_RADIO_CMAKE_MARKERS = ("project(gnuradio", "gnuradio-runtime", "gr_add_component")
_OOT_CMAKE_MARKERS = ("find_package(gnuradio", "gr_register_component", "gr_modtool")
_OOT_NAME_PREFIXES = ("gr-",)
_HARDWARE_SDK_MARKERS = (
    "uhd",
    "soapysdr",
    "bladerf",
    "limesdr",
    "rtl-sdr",
    "rtlsdr",
    "hackrf",
    "airspy",
)
 
_VERSION_PATTERNS = (
    re.compile(r"project\s*\([^)]*VERSION\s+([0-9]+(?:\.[0-9]+){1,2})", re.IGNORECASE),
    re.compile(r"set\s*\(\s*VERSION\s+\"?([0-9]+(?:\.[0-9]+){1,2})\"?\s*\)", re.IGNORECASE),
    re.compile(
        r"set\s*\(\s*VERSION_INFO_MAJOR_VERSION\s+\"?([0-9]+)\"?\s*\)", re.IGNORECASE
    ),
)
 
 
def looks_like_repository_root(path: Path) -> bool:
    """Determines whether a directory itself looks like a repository root.
 
    A directory is considered a repository root if it directly contains
    a ``.git`` entry or a well-known project marker file (e.g.
    ``CMakeLists.txt``, ``setup.py``, ``pyproject.toml``). Only the
    directory itself is inspected; ancestors and descendants are never
    consulted, so this check cannot be fooled by a parent repository
    (such as FlowPilot's own checkout) or by markers buried several
    levels below.
 
    This function is shared with
    :mod:`flowpilot.scanner.scanner_engine`, which uses it to decide
    whether a ``third_party/`` entry is itself a repository or a
    container of several independent repositories.
 
    Args:
        path: The directory to inspect.
 
    Returns:
        ``True`` if ``path`` directly contains a ``.git`` entry or a
        recognized project marker file.
    """
    if (path / ".git").exists():
        return True
    return any((path / marker).exists() for marker in _ROOT_MARKER_FILES)
 
 
class RepositoryDetector:
    """Detects a repository's type and collects its top-level metadata."""
 
    def __init__(self, *, logger: Optional[logging.Logger] = None) -> None:
        """Initializes a :class:`RepositoryDetector`.
 
        Args:
            logger: An optional logger to use. If omitted, a
                module-level logger is created via
                :func:`~flowpilot.core.utils.configure_logger`.
        """
        self._logger = logger or configure_logger(__name__)
 
    def detect(self, repository_path: Path) -> RepositoryMetadata:
        """Detects a repository's type and builds its metadata record.
 
        If ``repository_path`` does not itself look like a repository
        root (see :func:`looks_like_repository_root`) but wraps a single
        nested subdirectory that does, detection transparently descends
        into that nested directory and treats it as the actual
        repository root. All identity and Git metadata are then derived
        strictly from that resolved root, never from its ancestors.
 
        Args:
            repository_path: The filesystem path to the repository
                candidate. This may be the actual repository root, or a
                wrapper directory nesting the actual root one or more
                levels deeper.
 
        Returns:
            A populated
            :class:`~flowpilot.core.models.RepositoryMetadata` instance,
            with ``local_path`` set to the *resolved* repository root
            (not necessarily ``repository_path`` itself). Its ``modules``
            field is left empty; module detection is the responsibility
            of :class:`~flowpilot.scanner.module_detector.ModuleDetector`.
 
        Raises:
            RepositoryNotFoundError: If ``repository_path`` does not
                exist.
            InvalidRepositoryError: If ``repository_path`` exists but is
                not a directory.
        """
        try:
            resolved_path = ensure_exists(repository_path)
        except FileNotFoundError as exc:
            raise RepositoryNotFoundError(repository_path, cause=exc) from exc
 
        if not resolved_path.is_dir():
            raise InvalidRepositoryError(resolved_path, "path is not a directory")
 
        actual_root = self._resolve_actual_root(resolved_path)
        if actual_root != resolved_path:
            self._logger.info(
                "Resolved nested repository root: %s -> %s", resolved_path, actual_root
            )
 
        name = actual_root.name
        cmake_corpus = self._read_cmake_corpus(actual_root)
        repository_type = self._detect_type(name, cmake_corpus)
        version = self._detect_version(actual_root, cmake_corpus)
        branch = self._git_command(actual_root, "rev-parse", "--abbrev-ref", "HEAD")
        commit_hash = self._git_command(actual_root, "rev-parse", "HEAD")
        remote_url = self._git_command(actual_root, "remote", "get-url", "origin")
 
        self._logger.info(
            "Detected repository %s as %s (branch=%s)", name, repository_type.value, branch
        )
 
        return RepositoryMetadata(
            repository_id=name,
            name=name,
            repository_type=repository_type,
            local_path=actual_root,
            remote_url=remote_url,
            version=version,
            branch=branch,
            commit_hash=commit_hash,
        )
 
    def _resolve_actual_root(self, path: Path, *, depth: int = 0) -> Path:
        """Descends through single-child wrapper directories to find the real root.
 
        A directory that does not itself look like a repository root
        (see :func:`looks_like_repository_root`) but contains exactly
        one subdirectory is assumed to be an extraction or packaging
        artifact (e.g. ``gnuradio-main/gnuradio-main/``); resolution
        recurses into that subdirectory. Recursion stops as soon as a
        directory looks like a repository root, once a directory has
        zero or multiple subdirectories (ambiguous — left as-is), or
        once ``_WRAPPER_MAX_DEPTH`` levels have been descended, to bound
        the cost of pathological directory chains.
 
        Args:
            path: The directory to resolve.
            depth: The current recursion depth. Callers should omit
                this; it is used internally to enforce the depth bound.
 
        Returns:
            The resolved repository root. Equal to ``path`` if no
            single-child wrapper chain was found.
        """
        if depth >= _WRAPPER_MAX_DEPTH or looks_like_repository_root(path):
            return path
 
        try:
            subdirectories = [
                child
                for child in path.iterdir()
                if child.is_dir() and not child.name.startswith(".")
            ]
        except OSError as exc:
            self._logger.warning(
                "Unable to list %s while resolving repository root: %s", path, exc
            )
            return path
 
        if len(subdirectories) != 1:
            return path
 
        return self._resolve_actual_root(subdirectories[0], depth=depth + 1)
 
    def _detect_type(self, name: str, cmake_corpus: str) -> RepositoryType:
        """Classifies the repository type using name and CMake heuristics.
 
        Args:
            name: The repository's derived name.
            cmake_corpus: The lowercased, concatenated contents of the
                repository's top-level ``CMakeLists.txt`` files.
 
        Returns:
            The classified :class:`~flowpilot.core.models.RepositoryType`.
        """
        lowered_name = name.lower()
 
        if any(marker in lowered_name for marker in _GNU_RADIO_NAME_MARKERS) or any(
            marker in cmake_corpus for marker in _GNU_RADIO_CMAKE_MARKERS
        ):
            return RepositoryType.GNU_RADIO
 
        if lowered_name.startswith(_OOT_NAME_PREFIXES) or any(
            marker in cmake_corpus for marker in _OOT_CMAKE_MARKERS
        ):
            return RepositoryType.OOT_MODULE
 
        if any(marker in lowered_name for marker in _HARDWARE_SDK_MARKERS) or any(
            marker in cmake_corpus for marker in _HARDWARE_SDK_MARKERS
        ):
            return RepositoryType.HARDWARE_SDK
 
        return RepositoryType.UNKNOWN
 
    def _read_cmake_corpus(self, path: Path) -> str:
        """Reads and concatenates nearby ``CMakeLists.txt`` files for pattern matching.
 
        Only files within ``_CMAKE_SCAN_DEPTH`` directory levels of the
        repository root are read, and at most ``_MAX_CMAKE_FILES`` files
        are considered, to bound the cost of this heuristic on very
        large repositories.
 
        Args:
            path: The resolved repository root path.
 
        Returns:
            The lowercased, concatenated contents of the discovered
            ``CMakeLists.txt`` files. Empty if none were found or
            readable.
        """
        chunks: List[str] = []
        discovered = 0
        for cmake_file in sorted(path.rglob("CMakeLists.txt")):
            relative_depth = len(cmake_file.relative_to(path).parts)
            if relative_depth > _CMAKE_SCAN_DEPTH:
                continue
            try:
                chunks.append(cmake_file.read_text(encoding="utf-8", errors="ignore"))
            except OSError as exc:
                self._logger.warning("Unable to read %s: %s", cmake_file, exc)
                continue
            discovered += 1
            if discovered >= _MAX_CMAKE_FILES:
                break
        return "\n".join(chunks).lower()
 
    def _detect_version(self, path: Path, cmake_corpus: str) -> Optional[str]:
        """Determines the repository's version string.
 
        Attempts to extract a version from the CMake corpus first,
        falling back to ``git describe`` if the repository has its own
        Git metadata.
 
        Args:
            path: The resolved repository root path.
            cmake_corpus: The lowercased, concatenated CMake contents.
 
        Returns:
            The detected version string, or ``None`` if no version could
            be determined.
        """
        for pattern in _VERSION_PATTERNS:
            match = pattern.search(cmake_corpus)
            if match:
                return match.group(1)
        return self._git_command(path, "describe", "--tags", "--always")
 
    def _has_own_git(self, path: Path) -> bool:
        """Determines whether ``path`` directly contains its own ``.git`` entry.
 
        Unlike a generic "is this path inside a Git repository" check,
        this deliberately does *not* walk up through parent directories,
        so a repository without its own ``.git`` never inherits a parent
        repository's Git metadata (e.g. FlowPilot's own checkout).
 
        Args:
            path: The resolved repository root to inspect.
 
        Returns:
            ``True`` if ``path`` directly contains a ``.git`` file or
            directory.
        """
        return (path / ".git").exists()
 
    def _git_command(self, path: Path, *args: str) -> Optional[str]:
        """Runs a Git subcommand within ``path`` and returns its trimmed output.
 
        The command is only executed if ``path`` itself owns a ``.git``
        entry (see :meth:`_has_own_git`); otherwise ``None`` is returned
        immediately, without ever invoking Git, so there is no
        opportunity for Git's own upward repository search to escape
        ``path`` and pick up an ancestor repository.
 
        Args:
            path: The resolved repository root to run the command
                against.
            *args: The Git subcommand and its arguments (e.g.
                ``"rev-parse"``, ``"HEAD"``).
 
        Returns:
            The trimmed standard output of the command, or ``None`` if
            the repository has no Git metadata of its own or the
            command failed.
        """
        if not self._has_own_git(path):
            return None
        try:
            result = subprocess.run(
                ["git", "-C", str(path), *args],
                capture_output=True,
                text=True,
                timeout=_GIT_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            self._logger.warning("Git command failed for %s: %s", path, exc)
            return None
 
        if result.returncode != 0:
            self._logger.debug(
                "Git command %s exited with %d: %s",
                args,
                result.returncode,
                result.stderr.strip(),
            )
            return None
 
        output = result.stdout.strip()
        return output or None
 