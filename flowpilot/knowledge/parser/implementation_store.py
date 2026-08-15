"""
FlowPilot Implementation Knowledge Store.

This module provides persistent storage for ImplementationKnowledge
records produced by SourceCodeAnalyzer.

Pipeline:

    BlockDefinition
        |
        v
    SourceReference
        |
        v
    SourceCodeAnalyzer
        |
        v
    ImplementationKnowledge
        |
        v
    ImplementationStore
        |
        v
    JSON knowledge records

The store intentionally does NOT perform source-code analysis and does
NOT rediscover source references. Its only responsibility is persistence
and retrieval of already-produced ImplementationKnowledge objects.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Union

from flowpilot.core.models import ModelEncoder
from flowpilot.core.utils import (
    configure_logger,
    load_json,
    normalize_path,
    safe_mkdir,
    save_json,
)
from flowpilot.knowledge.parser.source_code_analyzer import (
    ImplementationKnowledge,
)


# ---------------------------------------------------------------------------
# Default storage location
# ---------------------------------------------------------------------------

_DEFAULT_STORAGE_DIR = (
    Path(__file__).resolve().parent.parent / "implementations"
)


class ImplementationStore:
    """
    Persistent storage for ImplementationKnowledge records.

    Each ImplementationKnowledge object is stored as one JSON file.

    Default layout:

        flowpilot/
        └── knowledge/
            ├── blocks/
            └── implementations/
                ├── gnuradio-main__gr-analog__analog_agc_xx.json
                ├── gnuradio-main__gr-digital__digital_costas_loop_cc.json
                └── ...

    The filename is derived from:

        repository + module + block_id

    This keeps implementation knowledge separate from:

        *.json
            BlockDefinition records

        *.sources.json
            SourceReference records

    The store does not create or modify those other knowledge records.
    """

    def __init__(
        self,
        storage_dir: Union[str, Path] = _DEFAULT_STORAGE_DIR,
        *,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Initialize the implementation knowledge store.

        Parameters
        ----------
        storage_dir:
            Directory where ImplementationKnowledge JSON files are stored.

        logger:
            Optional logger. If omitted, the project logging configuration
            is used.
        """

        self.storage_dir = normalize_path(storage_dir)

        safe_mkdir(self.storage_dir)

        self.logger = logger or configure_logger(__name__)

    # ------------------------------------------------------------------
    # Path / filename helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_part(value: object) -> str:
        """
        Convert a repository/module/block identifier into a filesystem-safe
        filename component.

        This intentionally keeps the transformation deterministic.

        Examples
        --------
        gr-analog
            -> gr-analog

        some/module
            -> some_module

        C:\\repo\\module
            -> C__repo_module
        """

        text = str(value)

        return (
            text
            .replace("\\", "_")
            .replace("/", "_")
            .replace(":", "_")
            .replace("*", "_")
            .replace("?", "_")
            .replace('"', "_")
            .replace("<", "_")
            .replace(">", "_")
            .replace("|", "_")
            .replace(" ", "_")
        )

    def _filename(
        self,
        repository: str,
        module: str,
        block_id: str,
    ) -> str:
        """
        Build the deterministic filename for one knowledge record.
        """

        return (
            f"{self._safe_part(repository)}__"
            f"{self._safe_part(module)}__"
            f"{self._safe_part(block_id)}.json"
        )

    def _path_for(
        self,
        repository: str,
        module: str,
        block_id: str,
    ) -> Path:
        """
        Return the storage path for one implementation knowledge record.
        """

        return self.storage_dir / self._filename(
            repository,
            module,
            block_id,
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_knowledge(
        knowledge: ImplementationKnowledge,
    ) -> None:
        """
        Validate the minimum identity information required for storage.

        A knowledge record must have a block ID.

        Repository and module may technically be missing because the
        analyzer model allows Optional values, but storing them under
        deterministic 'unknown' identifiers is preferable to generating
        an invalid filename.
        """

        if knowledge is None:
            raise ValueError(
                "ImplementationKnowledge cannot be None"
            )

        if not isinstance(
            knowledge,
            ImplementationKnowledge,
        ):
            raise TypeError(
                "knowledge must be an ImplementationKnowledge instance"
            )

        if not knowledge.block_id:
            raise ValueError(
                "ImplementationKnowledge.block_id is required"
            )

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    def store(
        self,
        knowledge: ImplementationKnowledge,
    ) -> Path:
        """
        Persist one ImplementationKnowledge record.

        Returns
        -------
        Path
            Path of the written JSON file.
        """

        self._validate_knowledge(knowledge)

        repository = (
            knowledge.repository
            if knowledge.repository
            else "unknown"
        )

        module = (
            knowledge.module
            if knowledge.module
            else "unknown"
        )

        path = self._path_for(
            repository,
            module,
            knowledge.block_id,
        )

        # Recompute statistics before persistence so the stored summary
        # always reflects the actual source_files list.
        knowledge.recompute_statistics()

        payload = knowledge.to_dict()

        save_json(
            path,
            payload,
            encoder=ModelEncoder,
        )

        self.logger.info(
            "Stored implementation knowledge for %s at %s",
            knowledge.block_id,
            path,
        )

        return path

    def store_many(
        self,
        knowledge_records: List[ImplementationKnowledge],
    ) -> List[Path]:
        """
        Persist multiple ImplementationKnowledge records.

        Processing is sequential and deterministic.

        A failure in one record is allowed to propagate because callers
        should know that a requested record was not persisted.
        """

        paths: List[Path] = []

        for knowledge in knowledge_records:
            paths.append(
                self.store(knowledge)
            )

        return paths

    # ------------------------------------------------------------------
    # Loading one record
    # ------------------------------------------------------------------

    def get(
        self,
        repository: str,
        module: str,
        block_id: str,
    ) -> Optional[ImplementationKnowledge]:
        """
        Load one specific ImplementationKnowledge record.

        Returns
        -------
        ImplementationKnowledge | None
            The restored record, or None if it does not exist or cannot
            be reconstructed.
        """

        path = self._path_for(
            repository,
            module,
            block_id,
        )

        if not path.exists():
            return None

        if not path.is_file():
            self.logger.warning(
                "Implementation storage path is not a file: %s",
                path,
            )
            return None

        try:
            data = load_json(path)

            if not isinstance(data, dict):
                self.logger.warning(
                    "Invalid implementation JSON object in %s",
                    path,
                )
                return None

            knowledge = (
                ImplementationKnowledge.from_dict(data)
            )

            # Recompute statistics after deserialization to keep the
            # derived counters synchronized with source_files.
            knowledge.recompute_statistics()

            return knowledge

        except Exception as exc:
            self.logger.warning(
                "Failed to load implementation record %s: %s",
                path,
                exc,
            )

            return None

    # ------------------------------------------------------------------
    # Loading by block ID
    # ------------------------------------------------------------------

    def get_by_id(
        self,
        block_id: str,
    ) -> List[ImplementationKnowledge]:
        """
        Load all implementation records having the given block ID.

        This is useful when the same block ID exists in more than one
        repository/module context.
        """

        if not block_id:
            return []

        results: List[ImplementationKnowledge] = []

        for path in self._iter_stored():
            try:
                data = load_json(path)

                if not isinstance(data, dict):
                    continue

                if data.get("block_id") != block_id:
                    continue

                knowledge = (
                    ImplementationKnowledge.from_dict(data)
                )

                knowledge.recompute_statistics()

                results.append(knowledge)

            except Exception as exc:
                self.logger.warning(
                    "Failed to load implementation record %s: %s",
                    path,
                    exc,
                )

        return results

    # ------------------------------------------------------------------
    # Repository queries
    # ------------------------------------------------------------------

    def list_by_repository(
        self,
        repository: str,
    ) -> List[ImplementationKnowledge]:
        """
        Return all implementation records belonging to a repository.
        """

        if not repository:
            return []

        results: List[ImplementationKnowledge] = []

        for record in self._iter_records():
            if record.repository == repository:
                results.append(record)

        return results

    # ------------------------------------------------------------------
    # Module queries
    # ------------------------------------------------------------------

    def list_by_module(
        self,
        repository: str,
        module: str,
    ) -> List[ImplementationKnowledge]:
        """
        Return all implementation records belonging to a repository/module.
        """

        if not repository or not module:
            return []

        results: List[ImplementationKnowledge] = []

        for record in self._iter_records():
            if (
                record.repository == repository
                and record.module == module
            ):
                results.append(record)

        return results

    # ------------------------------------------------------------------
    # Existence
    # ------------------------------------------------------------------

    def exists(
        self,
        repository: str,
        module: str,
        block_id: str,
    ) -> bool:
        """
        Check whether a specific implementation record exists.

        This checks the expected deterministic file path. It does not
        deserialize the record.
        """

        path = self._path_for(
            repository,
            module,
            block_id,
        )

        return path.is_file()

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete(
        self,
        repository: str,
        module: str,
        block_id: str,
    ) -> bool:
        """
        Delete one implementation knowledge record.

        Returns
        -------
        bool
            True if a file was deleted, otherwise False.
        """

        path = self._path_for(
            repository,
            module,
            block_id,
        )

        if not path.exists():
            return False

        if not path.is_file():
            return False

        try:
            path.unlink()

            self.logger.info(
                "Deleted implementation knowledge for %s",
                block_id,
            )

            return True

        except Exception as exc:
            self.logger.warning(
                "Failed to delete implementation record %s: %s",
                path,
                exc,
            )

            return False

    # ------------------------------------------------------------------
    # Iteration over stored JSON files
    # ------------------------------------------------------------------

    def _iter_stored(
        self,
    ) -> Iterator[Path]:
        """
        Iterate over implementation JSON files.

        Only *.json files directly inside storage_dir are considered.

        This prevents unrelated nested directories from accidentally
        becoming part of the implementation knowledge dataset.
        """

        if not self.storage_dir.exists():
            return

        if not self.storage_dir.is_dir():
            self.logger.warning(
                "Implementation storage path is not a directory: %s",
                self.storage_dir,
            )
            return

        for path in sorted(
            self.storage_dir.glob("*.json")
        ):
            if path.is_file():
                yield path

    # ------------------------------------------------------------------
    # Deserialize all records
    # ------------------------------------------------------------------

    def _iter_records(
        self,
    ) -> Iterator[ImplementationKnowledge]:
        """
        Iterate over valid ImplementationKnowledge records.

        Invalid/corrupted files are logged and skipped so that one bad
        knowledge record does not stop repository-wide queries.
        """

        for path in self._iter_stored():
            try:
                data = load_json(path)

                if not isinstance(data, dict):
                    self.logger.warning(
                        "Skipping non-object JSON file: %s",
                        path,
                    )
                    continue

                block_id = data.get("block_id")

                if not block_id:
                    self.logger.warning(
                        "Skipping implementation record without "
                        "block_id: %s",
                        path,
                    )
                    continue

                knowledge = (
                    ImplementationKnowledge.from_dict(data)
                )

                knowledge.recompute_statistics()

                yield knowledge

            except Exception as exc:
                self.logger.warning(
                    "Failed to load implementation record %s: %s",
                    path,
                    exc,
                )

    # ------------------------------------------------------------------
    # Summary / statistics
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, object]:
        """
        Return storage statistics.

        Example:

            {
                "total": 578,
                "repositories": 1,
                "modules": 20,
                "by_repository": {
                    "gnuradio-main": 578
                },
                "by_module": {
                    "gnuradio-main/gr-analog": 34,
                    ...
                },
                "analyzed_files": 1234,
                "successful_files": 1230,
                "failed_files": 4,
                "unsupported_files": 0,
                "classes_found": 500,
                "methods_found": 2000,
                "functions_found": 800,
                "bindings_found": 300
            }
        """

        records = list(
            self._iter_records()
        )

        by_repository: Dict[str, int] = {}
        by_module: Dict[str, int] = {}

        analyzed_files = 0
        successful_files = 0
        failed_files = 0
        unsupported_files = 0

        classes_found = 0
        methods_found = 0
        functions_found = 0
        bindings_found = 0

        for record in records:
            repository = (
                record.repository
                or "unknown"
            )

            module = (
                record.module
                or "unknown"
            )

            by_repository[repository] = (
                by_repository.get(repository, 0)
                + 1
            )

            module_key = (
                f"{repository}/{module}"
            )

            by_module[module_key] = (
                by_module.get(module_key, 0)
                + 1
            )

            analyzed_files += (
                record.analyzed_file_count
            )

            successful_files += (
                record.successful_file_count
            )

            failed_files += (
                record.failed_file_count
            )

            unsupported_files += (
                record.unsupported_file_count
            )

            classes_found += (
                record.classes_found
            )

            methods_found += (
                record.methods_found
            )

            functions_found += (
                record.functions_found
            )

            bindings_found += (
                record.bindings_found
            )

        return {
            "total": len(records),
            "repositories": len(by_repository),
            "modules": len(by_module),
            "by_repository": by_repository,
            "by_module": by_module,
            "analyzed_files": analyzed_files,
            "successful_files": successful_files,
            "failed_files": failed_files,
            "unsupported_files": unsupported_files,
            "classes_found": classes_found,
            "methods_found": methods_found,
            "functions_found": functions_found,
            "bindings_found": bindings_found,
        }

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def count(self) -> int:
        """
        Return the number of valid implementation records.
        """

        return int(
            self.summary()["total"]
        )

    def clear(self) -> int:
        """
        Delete all implementation JSON records.

        Returns
        -------
        int
            Number of files successfully removed.

        This is intentionally explicit and only removes *.json files
        directly inside the implementation storage directory.
        """

        deleted = 0

        for path in list(
            self._iter_stored()
        ):
            try:
                path.unlink()

                deleted += 1

            except Exception as exc:
                self.logger.warning(
                    "Failed to delete implementation record %s: %s",
                    path,
                    exc,
                )

        self.logger.info(
            "Cleared %d implementation knowledge record(s)",
            deleted,
        )

        return deleted