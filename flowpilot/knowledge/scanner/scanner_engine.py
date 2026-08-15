"""Top-level orchestration for the FlowPilot Repository Scanner.
 
This module provides :class:`ScannerEngine`, which discovers repository
clones beneath a ``third_party/`` directory, builds a
:class:`~flowpilot.core.models.RepositoryInventory` for each one via
:class:`~flowpilot.scanner.inventory_builder.InventoryBuilder`,
aggregates the results into an
:class:`~flowpilot.core.models.InventoryReport`, and persists that
report to disk as JSON.
 
Not every immediate child of ``third_party/`` is a single repository.
Some (e.g. ``third_party/oot/``) are *container* directories that
collect several independent repositories side by side (``gr-lora``,
``gr-satellites``, etc.), with no repository markers of their own.
:meth:`ScannerEngine.discover_repositories` expands such containers into
their individual member repositories before scanning; ordinary
wrapper directories that merely nest a single repository one level
deeper (e.g. ``gnuradio-main/gnuradio-main/``) are left for
:class:`~flowpilot.scanner.repository_detector.RepositoryDetector` to
resolve.
"""
 
from __future__ import annotations
 
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union
 
from flowpilot.core.exceptions import (
    FlowPilotError,
    InvalidRepositoryError,
    RepositoryError,
    RepositoryNotFoundError,
    StorageError,
)
from flowpilot.core.models import InventoryReport, ModelEncoder, ScanStatus
from flowpilot.core.utils import configure_logger, normalize_path, save_json, utc_now
from flowpilot.knowledge.scanner.inventory_builder import InventoryBuilder
from flowpilot.knowledge.scanner.repository_detector import looks_like_repository_root
 
__all__ = ["ScannerEngine"]
 
_DEFAULT_OUTPUT_FILENAME = "repository_inventory.json"
_CONTAINER_MAX_DEPTH = 4
 
 
class ScannerEngine:
    """Orchestrates a full repository scan across a ``third_party/`` directory."""
 
    def __init__(
        self,
        third_party_dir: Union[str, Path],
        *,
        output_path: Union[str, Path] = Path(_DEFAULT_OUTPUT_FILENAME),
        inventory_builder: Optional[InventoryBuilder] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """Initializes a :class:`ScannerEngine`.
 
        Args:
            third_party_dir: The directory containing third-party
                repository clones (and, potentially, container
                directories collecting several repositories) to scan.
            output_path: The path the aggregated
                :class:`~flowpilot.core.models.InventoryReport` will be
                saved to as JSON.
            inventory_builder: An optional :class:`InventoryBuilder` to
                reuse. A new instance is created if omitted.
            logger: An optional logger to use. If omitted, a
                module-level logger is created via
                :func:`~flowpilot.core.utils.configure_logger`.
        """
        self._logger = logger or configure_logger(__name__)
        self._third_party_dir = normalize_path(third_party_dir)
        self._output_path = normalize_path(output_path)
        self._inventory_builder = inventory_builder or InventoryBuilder(logger=self._logger)
 
    def discover_repositories(self) -> List[Path]:
        """Discovers candidate repository directories beneath ``third_party_dir``.
 
        Each immediate, non-hidden subdirectory of ``third_party_dir``
        is classified as either:
 
        * A repository (possibly wrapping its actual root one or more
          levels deeper — see
          :class:`~flowpilot.scanner.repository_detector.RepositoryDetector`),
          contributing exactly one candidate path, or
        * A *container* directory with no repository markers of its own
          and more than one subdirectory, whose subdirectories are each
          expanded recursively using the same rule, contributing one
          candidate per independent repository they contain.
 
        Returns:
            A sorted list of repository candidate directories. A single
            ``third_party_dir`` entry may contribute zero, one, or
            several candidates.
 
        Raises:
            RepositoryNotFoundError: If ``third_party_dir`` does not
                exist.
            InvalidRepositoryError: If ``third_party_dir`` exists but is
                not a directory.
        """
        if not self._third_party_dir.exists():
            raise RepositoryNotFoundError(self._third_party_dir)
        if not self._third_party_dir.is_dir():
            raise InvalidRepositoryError(
                self._third_party_dir, "third-party path is not a directory"
            )
 
        candidates: List[Path] = []
        for entry in sorted(self._third_party_dir.iterdir()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            candidates.extend(self._expand_repository_candidates(entry))
 
        return sorted(candidates)
 
    def _expand_repository_candidates(self, path: Path, *, depth: int = 0) -> List[Path]:
        """Expands one ``third_party`` entry into one or more repository roots.
 
        A directory that already looks like a repository root (see
        :func:`~flowpilot.scanner.repository_detector.looks_like_repository_root`)
        is returned as a single candidate; any further nesting (e.g. a
        single-child extraction wrapper) is left for
        :class:`~flowpilot.scanner.repository_detector.RepositoryDetector`
        to resolve when it is scanned.
 
        A directory that does *not* look like a repository root but
        contains more than one subdirectory is treated as a container
        of independent repositories (e.g. ``third_party/oot/``): each
        subdirectory is expanded recursively, and every result is
        included as its own candidate.
 
        A directory that does not look like a repository root and has
        zero or exactly one subdirectory is ambiguous at the discovery
        level (it may be an empty repository, or a wrapper nesting a
        single repository) and is returned as-is, deferring to
        :class:`RepositoryDetector` for further resolution.
 
        Args:
            path: The directory to classify and expand.
            depth: The current recursion depth. Callers should omit
                this; it is used internally to enforce
                ``_CONTAINER_MAX_DEPTH``.
 
        Returns:
            A list of one or more repository candidate directories.
        """
        if depth >= _CONTAINER_MAX_DEPTH or looks_like_repository_root(path):
            return [path]
 
        try:
            subdirectories = sorted(
                child
                for child in path.iterdir()
                if child.is_dir() and not child.name.startswith(".")
            )
        except OSError as exc:
            self._logger.warning("Unable to list %s during discovery: %s", path, exc)
            return [path]
 
        if len(subdirectories) <= 1:
            return [path]
 
        self._logger.info(
            "Treating %s as a container of %d independent repositories",
            path,
            len(subdirectories),
        )
        expanded: List[Path] = []
        for subdirectory in subdirectories:
            expanded.extend(self._expand_repository_candidates(subdirectory, depth=depth + 1))
        return expanded
 
    def scan(self) -> InventoryReport:
        """Runs a full scan across every repository under ``third_party_dir``.
 
        Individual repository failures are recorded in the report's
        ``errors`` list and do not abort the overall scan. The resulting
        report is always saved to ``output_path``, even if every
        repository fails.
 
        Returns:
            The aggregated :class:`~flowpilot.core.models.InventoryReport`.
        """
        started_at = utc_now()
        report = InventoryReport(
            report_id=self._generate_report_id(started_at),
            overall_status=ScanStatus.RUNNING,
            started_at=started_at,
        )
 
        try:
            repositories = self.discover_repositories()
        except RepositoryError as exc:
            self._logger.error("Repository discovery failed: %s", exc)
            report.errors.append(str(exc))
            report.overall_status = ScanStatus.FAILED
            report.completed_at = utc_now()
            self._save_report(report)
            return report
 
        self._logger.info(
            "Discovered %d candidate repositories under %s",
            len(repositories),
            self._third_party_dir,
        )
 
        for repository_path in repositories:
            self._scan_one(repository_path, report)
 
        report.total_repositories = len(report.inventories)
        report.overall_status = ScanStatus.COMPLETED if report.inventories else ScanStatus.FAILED
        report.completed_at = utc_now()
 
        self._save_report(report)
        self._logger.info(
            "Scan complete: %d succeeded, %d failed",
            report.total_repositories,
            len(report.errors),
        )
        return report
 
    def _scan_one(self, repository_path: Path, report: InventoryReport) -> None:
        """Scans a single repository and records the outcome onto ``report``.
 
        Args:
            repository_path: The filesystem path to the repository to
                scan.
            report: The in-progress :class:`InventoryReport` to append
                results or errors to.
        """
        self._logger.info("Scanning repository: %s", repository_path)
        try:
            inventory = self._inventory_builder.build(repository_path)
        except FlowPilotError as exc:
            self._logger.error("Failed to scan %s: %s", repository_path, exc)
            report.errors.append(f"{repository_path}: {exc}")
            return
        except Exception as exc:  # noqa: BLE001 - last-resort guard around a single repo.
            self._logger.exception("Unexpected error scanning %s", repository_path)
            report.errors.append(f"{repository_path}: {exc}")
            return
 
        report.inventories.append(inventory)
 
    def _generate_report_id(self, started_at: datetime) -> str:
        """Generates a stable, sortable identifier for a scan report.
 
        Args:
            started_at: The timestamp the scan began at.
 
        Returns:
            A report identifier of the form
            ``scan-YYYYMMDDTHHMMSSffffff``.
        """
        return f"scan-{started_at.strftime('%Y%m%dT%H%M%S%f')}"
 
    def _save_report(self, report: InventoryReport) -> Path:
        """Persists an :class:`InventoryReport` to ``output_path`` as JSON.
 
        Args:
            report: The report to persist.
 
        Returns:
            The resolved path the report was written to.
 
        Raises:
            StorageError: If the report could not be written to disk.
        """
        try:
            saved_path = save_json(self._output_path, report.to_dict(), encoder=ModelEncoder)
        except OSError as exc:
            raise StorageError(
                "Failed to save inventory report", path=self._output_path, cause=exc
            ) from exc
        self._logger.info("Saved inventory report to %s", saved_path)
        return saved_path