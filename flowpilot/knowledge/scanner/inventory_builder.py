"""Inventory assembly for the FlowPilot Repository Scanner.
 
This module provides :class:`InventoryBuilder`, which orchestrates
:class:`~flowpilot.scanner.repository_detector.RepositoryDetector`,
:class:`~flowpilot.scanner.module_detector.ModuleDetector`, and
:class:`~flowpilot.scanner.statistics_builder.StatisticsBuilder` to
produce a complete :class:`~flowpilot.core.models.RepositoryInventory`
for a single repository, including per-file metadata with module
attribution.
"""
 
from __future__ import annotations
 
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
 
from flowpilot.core.exceptions import InventoryBuildError, RepositoryError
from flowpilot.core.models import (
    FileMetadata,
    FileType,
    ModuleMetadata,
    RepositoryInventory,
    ScanStatus,
)
from flowpilot.core.utils import configure_logger, recursive_files, sha256_file, utc_now
from flowpilot.knowledge.scanner.file_classifier import FileClassifier
from flowpilot.knowledge.scanner.module_detector import ModuleDetector
from flowpilot.knowledge.scanner.repository_detector import RepositoryDetector
from flowpilot.knowledge.scanner.statistics_builder import StatisticsBuilder
 
__all__ = ["InventoryBuilder"]
 
_PARSER_BY_FILE_TYPE: Dict[FileType, str] = {
    FileType.BLOCK_YML: "YAMLParser",
    FileType.TREE_YML: "YAMLParser",
    FileType.GRC: "GRCParser",
    FileType.PYTHON: "PythonParser",
    FileType.CPP_SOURCE: "CPPParser",
    FileType.CPP_HEADER: "CPPParser",
    FileType.MARKDOWN: "DocumentationParser",
    FileType.RESTRUCTURED_TEXT: "DocumentationParser",
}
 
 
class InventoryBuilder:
    """Combines detection and statistics subsystems into a repository inventory."""
 
    def __init__(
        self,
        *,
        repository_detector: Optional[RepositoryDetector] = None,
        module_detector: Optional[ModuleDetector] = None,
        statistics_builder: Optional[StatisticsBuilder] = None,
        file_classifier: Optional[FileClassifier] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """Initializes an :class:`InventoryBuilder`.
 
        Args:
            repository_detector: An optional :class:`RepositoryDetector`
                to reuse. A new instance is created if omitted.
            module_detector: An optional :class:`ModuleDetector` to
                reuse. A new instance is created if omitted.
            statistics_builder: An optional :class:`StatisticsBuilder`
                to reuse. A new instance is created if omitted.
            file_classifier: An optional :class:`FileClassifier` to
                reuse. A new instance is created if omitted.
            logger: An optional logger to use. If omitted, a
                module-level logger is created via
                :func:`~flowpilot.core.utils.configure_logger`.
        """
        self._logger = logger or configure_logger(__name__)
        self._classifier = file_classifier or FileClassifier()
        self._repository_detector = repository_detector or RepositoryDetector(
            logger=self._logger
        )
        self._module_detector = module_detector or ModuleDetector(logger=self._logger)
        self._statistics_builder = statistics_builder or StatisticsBuilder(
            file_classifier=self._classifier, logger=self._logger
        )
 
    def build(self, repository_path: Path) -> RepositoryInventory:
        """Builds a complete :class:`RepositoryInventory` for one repository.
 
        Args:
            repository_path: The filesystem path to the repository root.
 
        Returns:
            A populated
            :class:`~flowpilot.core.models.RepositoryInventory`.
 
        Raises:
            RepositoryError: If the repository cannot be located or is
                structurally invalid.
            InventoryBuildError: If module detection or statistics
                computation fails unexpectedly.
        """
        repository_metadata = self._repository_detector.detect(repository_path)
 
        try:
            modules = self._module_detector.detect(
                repository_metadata.local_path, repository_metadata.repository_type
            )
        except RepositoryError:
            raise
        except Exception as exc:  # noqa: BLE001 - converted to a domain error below.
            raise InventoryBuildError(
                "module detection failed", repository=repository_path, cause=exc
            ) from exc
        repository_metadata.modules = modules
 
        files = self._build_file_metadata(repository_metadata.local_path, modules)
        block_count = sum(module.block_count for module in modules)
 
        try:
            statistics = self._statistics_builder.build(
                repository_metadata.local_path,
                module_count=len(modules),
                block_count=block_count,
            )
        except RepositoryError:
            raise
        except Exception as exc:  # noqa: BLE001 - converted to a domain error below.
            raise InventoryBuildError(
                "statistics computation failed", repository=repository_path, cause=exc
            ) from exc
 
        repository_metadata.scan_status = ScanStatus.COMPLETED
        repository_metadata.scanned_at = utc_now()
        repository_metadata.updated_at = utc_now()
 
        self._logger.info(
            "Built inventory for %s: %d files, %d modules",
            repository_metadata.name,
            len(files),
            len(modules),
        )
 
        return RepositoryInventory(
            repository=repository_metadata,
            files=files,
            statistics=statistics,
        )
 
    def _build_file_metadata(
        self, repository_root: Path, modules: List[ModuleMetadata]
    ) -> List[FileMetadata]:
        """Builds per-file metadata for every file in a repository.
 
        Args:
            repository_root: The filesystem path to the repository root.
            modules: The modules discovered within the repository, used
                to attribute each file to its owning module.
 
        Returns:
            A list of populated
            :class:`~flowpilot.core.models.FileMetadata` instances, one
            per file in the repository.
        """
        module_roots = self._resolve_module_roots(repository_root, modules)
        files: List[FileMetadata] = []
 
        for file_path in recursive_files(repository_root):
            file_type = self._classifier.classify(file_path)
            module_name = self._attribute_module(file_path, module_roots)
            size_bytes = self._safe_size(file_path)
            digest = self._safe_hash(file_path)
 
            files.append(
                FileMetadata(
                    path=file_path,
                    file_type=file_type,
                    size_bytes=size_bytes,
                    sha256=digest,
                    parser=_PARSER_BY_FILE_TYPE.get(file_type),
                    module_name=module_name,
                    is_binary=file_type is FileType.IMAGE,
                )
            )
        return files
 
    def _resolve_module_roots(
        self, repository_root: Path, modules: List[ModuleMetadata]
    ) -> List[Tuple[ModuleMetadata, Path]]:
        """Resolves each module's filesystem root, deepest paths first.
 
        Args:
            repository_root: The filesystem path to the repository root.
            modules: The modules to resolve roots for.
 
        Returns:
            A list of ``(module, module_root)`` pairs sorted by root
            path depth in descending order, so that the most specific
            module root is matched first during attribution.
        """
        resolved: List[Tuple[ModuleMetadata, Path]] = []
        for module in modules:
            candidate_root = repository_root / module.name
            module_root = candidate_root if candidate_root.is_dir() else repository_root
            resolved.append((module, module_root))
        resolved.sort(key=lambda pair: len(pair[1].parts), reverse=True)
        return resolved
 
    def _attribute_module(
        self, file_path: Path, module_roots: List[Tuple[ModuleMetadata, Path]]
    ) -> Optional[str]:
        """Attributes a file to the most specific module that owns it.
 
        Args:
            file_path: The file to attribute.
            module_roots: The ``(module, module_root)`` pairs to match
                against, sorted deepest-first.
 
        Returns:
            The owning module's name, or ``None`` if no module claims
            the file.
        """
        for module, module_root in module_roots:
            if file_path == module_root or module_root in file_path.parents:
                return module.name
        return None
 
    def _safe_size(self, path: Path) -> int:
        """Safely retrieves a file's size in bytes.
 
        Args:
            path: The file to inspect.
 
        Returns:
            The file's size in bytes, or ``0`` if it could not be
            determined.
        """
        try:
            return path.stat().st_size
        except OSError as exc:
            self._logger.warning("Unable to stat %s: %s", path, exc)
            return 0
 
    def _safe_hash(self, path: Path) -> Optional[str]:
        """Safely computes a file's SHA-256 digest.
 
        Args:
            path: The file to hash.
 
        Returns:
            The lowercase hexadecimal SHA-256 digest, or ``None`` if it
            could not be computed.
        """
        try:
            return sha256_file(path)
        except OSError as exc:
            self._logger.warning("Unable to hash %s: %s", path, exc)
            return None