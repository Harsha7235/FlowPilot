"""Repository statistics computation for the FlowPilot Repository Scanner.
 
This module provides :class:`StatisticsBuilder`, which performs a
single-pass walk of a repository's files to compute aggregate counts,
size totals, and line-count metrics for
:class:`~flowpilot.core.models.RepositoryStatistics`.
"""
 
from __future__ import annotations
 
import logging
import time
from pathlib import Path
from typing import Dict, Optional
 
from flowpilot.core.models import FileType, RepositoryStatistics
from flowpilot.core.utils import (
    configure_logger,
    ensure_exists,
    recursive_directories,
    recursive_files,
)
from flowpilot.knowledge.scanner.file_classifier import FileClassifier
 
__all__ = ["StatisticsBuilder"]
 
_LANGUAGE_PYTHON = "python"
_LANGUAGE_CPP = "cpp"
_BUCKET_EXAMPLES = "examples"
_BUCKET_TESTS = "tests"
 
 
class StatisticsBuilder:
    """Computes aggregate :class:`RepositoryStatistics` for a repository.
 
    Files are counted per :class:`~flowpilot.core.models.FileType` under
    ``files_by_type``, alongside two convenience aggregate buckets,
    ``"examples"`` and ``"tests"``, that count files residing in
    conventional example and test directories regardless of their
    :class:`~flowpilot.core.models.FileType`.
    """
 
    def __init__(
        self,
        *,
        file_classifier: Optional[FileClassifier] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """Initializes a :class:`StatisticsBuilder`.
 
        Args:
            file_classifier: An optional :class:`FileClassifier` to
                reuse. A new instance is created if omitted.
            logger: An optional logger to use. If omitted, a
                module-level logger is created via
                :func:`~flowpilot.core.utils.configure_logger`.
        """
        self._classifier = file_classifier or FileClassifier()
        self._logger = logger or configure_logger(__name__)
 
    def build(
        self,
        repository_path: Path,
        *,
        module_count: int = 0,
        block_count: int = 0,
    ) -> RepositoryStatistics:
        """Builds aggregate statistics for a repository via a single file pass.
 
        Args:
            repository_path: The filesystem path to the repository root.
            module_count: The number of modules discovered by
                :class:`~flowpilot.scanner.module_detector.ModuleDetector`,
                recorded verbatim on the returned statistics.
            block_count: The total number of GNU Radio Companion blocks
                discovered across all modules, recorded verbatim on the
                returned statistics.
 
        Returns:
            A populated
            :class:`~flowpilot.core.models.RepositoryStatistics`
            instance.
 
        Raises:
            FileNotFoundError: If ``repository_path`` does not exist.
            NotADirectoryError: If ``repository_path`` is not a
                directory.
        """
        start_time = time.perf_counter()
        resolved_root = ensure_exists(repository_path)
        if not resolved_root.is_dir():
            raise NotADirectoryError(f"Not a directory: {resolved_root}")
 
        files_by_type: Dict[str, int] = {}
        line_count_by_language: Dict[str, int] = {_LANGUAGE_PYTHON: 0, _LANGUAGE_CPP: 0}
        total_size_bytes = 0
        total_files = 0
        example_count = 0
        test_count = 0
 
        for file_path in recursive_files(resolved_root):
            total_files += 1
            file_type = self._classifier.classify(file_path)
            files_by_type[file_type.value] = files_by_type.get(file_type.value, 0) + 1
 
            total_size_bytes += self._safe_size(file_path)
 
            if self._classifier.is_example(file_path):
                example_count += 1
            if self._classifier.is_test(file_path):
                test_count += 1
 
            if file_type is FileType.PYTHON:
                line_count_by_language[_LANGUAGE_PYTHON] += self._count_lines(file_path)
            elif file_type in (FileType.CPP_SOURCE, FileType.CPP_HEADER):
                line_count_by_language[_LANGUAGE_CPP] += self._count_lines(file_path)
 
        files_by_type[_BUCKET_EXAMPLES] = example_count
        files_by_type[_BUCKET_TESTS] = test_count
 
        total_directories = sum(1 for _ in recursive_directories(resolved_root))
        elapsed_seconds = time.perf_counter() - start_time
 
        self._logger.info(
            "Computed statistics for %s: %d files, %d directories in %.3fs",
            resolved_root,
            total_files,
            total_directories,
            elapsed_seconds,
        )
 
        return RepositoryStatistics(
            total_files=total_files,
            total_directories=total_directories,
            total_size_bytes=total_size_bytes,
            files_by_type=files_by_type,
            module_count=module_count,
            block_count=block_count,
            line_count_by_language=line_count_by_language,
            scan_duration_seconds=elapsed_seconds,
        )
 
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
 
    def _count_lines(self, path: Path) -> int:
        """Counts the number of lines in a text file.
 
        Args:
            path: The file to count lines in.
 
        Returns:
            The number of lines in the file, or ``0`` if it could not be
            read.
        """
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                return sum(1 for _ in handle)
        except OSError as exc:
            self._logger.warning("Unable to read %s for line counting: %s", path, exc)
            return 0