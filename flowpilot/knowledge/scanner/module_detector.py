"""Module discovery for the FlowPilot Repository Scanner.
 
This module provides :class:`ModuleDetector`, which discovers the GNU
Radio modules contained within a repository. In-tree GNU Radio
repositories may contain many modules (e.g. ``gr-analog``,
``gr-digital``); out-of-tree (OOT) repositories and other repository
types are treated as a single module rooted at the repository root.
"""
 
from __future__ import annotations
 
import logging
import re
from pathlib import Path
from typing import List, Optional
 
from flowpilot.core.models import ModuleMetadata, RepositoryType
from flowpilot.core.utils import configure_logger, recursive_files
 
__all__ = ["ModuleDetector"]
 
_MODULE_DIRECTORY_PREFIX = "gr-"
_MODULE_STRUCTURE_MARKERS = ("grc", "include", "python", "lib", "swig", "bindings")
_DEPENDENCY_PATTERN = re.compile(r"find_package\s*\(\s*([A-Za-z0-9_\-]+)", re.IGNORECASE)
 
 
class ModuleDetector:
    """Discovers GNU Radio modules within a repository based on its structure."""
 
    def __init__(self, *, logger: Optional[logging.Logger] = None) -> None:
        """Initializes a :class:`ModuleDetector`.
 
        Args:
            logger: An optional logger to use. If omitted, a
                module-level logger is created via
                :func:`~flowpilot.core.utils.configure_logger`.
        """
        self._logger = logger or configure_logger(__name__)
 
    def detect(
        self, repository_path: Path, repository_type: RepositoryType
    ) -> List[ModuleMetadata]:
        """Discovers the modules contained within a repository.
 
        Args:
            repository_path: The filesystem path to the repository root.
            repository_type: The repository's classified
                :class:`~flowpilot.core.models.RepositoryType`, used to
                decide whether to search for multiple in-tree modules.
 
        Returns:
            A list of discovered
            :class:`~flowpilot.core.models.ModuleMetadata` instances.
            Always contains at least one entry.
        """
        if repository_type == RepositoryType.GNU_RADIO:
            in_tree_modules = self._detect_in_tree_modules(repository_path)
            if in_tree_modules:
                return in_tree_modules
            self._logger.warning(
                "No in-tree gr-* modules found under %s; treating repository as a single module",
                repository_path,
            )
 
        return [self._build_module_metadata(repository_path)]
 
    def _detect_in_tree_modules(self, repository_path: Path) -> List[ModuleMetadata]:
        """Finds in-tree ``gr-*`` module directories beneath a repository root.
 
        Args:
            repository_path: The filesystem path to the repository root.
 
        Returns:
            A list of :class:`~flowpilot.core.models.ModuleMetadata`
            instances, one per discovered module directory, sorted by
            name.
        """
        modules: List[ModuleMetadata] = []
        for candidate in sorted(repository_path.glob(f"{_MODULE_DIRECTORY_PREFIX}*")):
            if candidate.is_dir() and self._looks_like_module(candidate):
                modules.append(self._build_module_metadata(candidate))
        return modules
 
    def _looks_like_module(self, candidate: Path) -> bool:
        """Determines whether a directory has the structure of a GNU Radio module.
 
        A directory is considered a module if it contains a
        ``CMakeLists.txt`` file and at least one conventional module
        subdirectory (e.g. ``grc``, ``include``, ``python``, ``lib``).
        Relying on structure rather than the ``gr-`` name alone avoids
        misclassifying incidental directories that merely share the
        naming convention.
 
        Args:
            candidate: The directory to inspect.
 
        Returns:
            ``True`` if the directory looks like a GNU Radio module.
        """
        has_cmake = (candidate / "CMakeLists.txt").exists()
        has_structure = any(
            (candidate / marker).is_dir() for marker in _MODULE_STRUCTURE_MARKERS
        )
        return has_cmake and has_structure
 
    def _build_module_metadata(self, module_root: Path) -> ModuleMetadata:
        """Builds a :class:`ModuleMetadata` record for a module directory.
 
        Args:
            module_root: The filesystem path to the module's root
                directory.
 
        Returns:
            A populated :class:`~flowpilot.core.models.ModuleMetadata`
            instance.
        """
        name = module_root.name
        namespace = (
            name[len(_MODULE_DIRECTORY_PREFIX) :]
            if name.startswith(_MODULE_DIRECTORY_PREFIX)
            else name
        )
 
        block_yml_files = sorted(recursive_files(module_root, pattern="*.block.yml"))
        python_files = sorted(recursive_files(module_root, pattern="*.py"))
        cpp_files = sorted(
            set(recursive_files(module_root, pattern="*.cc"))
            | set(recursive_files(module_root, pattern="*.cpp"))
            | set(recursive_files(module_root, pattern="*.h"))
            | set(recursive_files(module_root, pattern="*.hpp"))
        )
        dependencies = self._extract_dependencies(module_root)
 
        return ModuleMetadata(
            name=name,
            namespace=namespace,
            block_count=len(block_yml_files),
            block_yml_files=block_yml_files,
            python_files=python_files,
            cpp_files=cpp_files,
            dependencies=dependencies,
        )
 
    def _extract_dependencies(self, module_root: Path) -> List[str]:
        """Extracts CMake ``find_package`` dependencies for a module.
 
        Args:
            module_root: The filesystem path to the module's root
                directory.
 
        Returns:
            A sorted list of unique dependency names referenced via
            ``find_package(...)`` in the module's top-level
            ``CMakeLists.txt``. Empty if the file is absent or
            unreadable.
        """
        cmake_file = module_root / "CMakeLists.txt"
        if not cmake_file.exists():
            return []
        try:
            text = cmake_file.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            self._logger.warning("Unable to read %s: %s", cmake_file, exc)
            return []
        return sorted({match.group(1) for match in _DEPENDENCY_PATTERN.finditer(text)})
