"""Storage and retrieval for structured GNU Radio block knowledge.
 
This module provides :class:`BlockStore`, the minimal persistence layer
that organizes already-parsed
:class:`~flowpilot.knowledge.parser.block_models.BlockDefinition`
objects (produced by
:class:`~flowpilot.knowledge.parser.block_yaml_parser.BlockYamlParser`)
into the ``flowpilot/knowledge/blocks/`` knowledge directory.
 
:class:`BlockStore` does no YAML parsing and defines no new knowledge
model: it is purely responsible for writing
:class:`~flowpilot.knowledge.parser.block_models.BlockDefinition`
instances to disk as individual JSON documents, and for reading them
back by repository, module, or block id. Keeping storage separate from
parsing lets the same store serve GNU Radio's in-tree modules today and
out-of-tree (OOT) repositories later, without any change to this
module.
"""
 
from __future__ import annotations
 
import logging
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union
 
from flowpilot.core.models import ModelEncoder
from flowpilot.core.utils import configure_logger, load_json, normalize_path, safe_mkdir, save_json
from flowpilot.knowledge.parser.block_models import BlockDefinition
 
__all__ = ["BlockStore"]
 
_DEFAULT_STORAGE_DIR = Path(__file__).resolve().parent.parent / "blocks"
_SAFE_FILENAME_CHARACTERS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
)
 
 
class BlockStore:
    """Persists and queries structured GNU Radio block knowledge as JSON.
 
    Blocks are stored as individual JSON documents beneath a storage
    directory (``flowpilot/knowledge/blocks/`` by default), one file per
    block, named deterministically from its repository, module, and
    block id so that repeated runs over unchanged input produce
    identical filenames.
    """
 
    def __init__(
        self,
        storage_dir: Union[str, Path] = _DEFAULT_STORAGE_DIR,
        *,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """Initializes a :class:`BlockStore`.
 
        Args:
            storage_dir: The directory block JSON documents are read
                from and written to. Defaults to the existing
                ``flowpilot/knowledge/blocks/`` directory, resolved
                relative to this module's own location so the default
                does not depend on the caller's working directory.
            logger: An optional logger to use. If omitted, a
                module-level logger is created via
                :func:`~flowpilot.core.utils.configure_logger`.
        """
        self._storage_dir = normalize_path(storage_dir)
        self._logger = logger or configure_logger(__name__)
 
    def store(self, definitions: List[BlockDefinition]) -> List[Path]:
        """Persists a batch of block definitions as individual JSON documents.
 
        Every field already extracted by
        :class:`~flowpilot.knowledge.parser.block_yaml_parser.BlockYamlParser`
        is preserved verbatim; this method only serializes
        ``definition.to_dict()`` to disk, it does not modify or
        reinterpret any field.
 
        If two definitions in the same call would produce the same
        storage key (repository, module, and block id all equal — a
        genuine duplicate block id within one module), the later one is
        given a numeric suffix and a warning is logged, so neither
        block is ever silently discarded or overwritten.
 
        Args:
            definitions: The block definitions to persist.
 
        Returns:
            The paths written to, in the same order as ``definitions``.
 
        Raises:
            StorageError: If the storage directory cannot be created.
        """
        resolved_dir = safe_mkdir(self._storage_dir)
        occurrences: Dict[str, int] = {}
        written_paths: List[Path] = []
 
        for definition in definitions:
            key = self._build_key(definition)
            occurrence = occurrences.get(key, 0) + 1
            occurrences[key] = occurrence
 
            filename = f"{key}.json" if occurrence == 1 else f"{key}__{occurrence}.json"
            if occurrence > 1:
                self._logger.warning(
                    "Duplicate block key '%s' (repository=%s, module=%s, block_id=%s); "
                    "storing as %s instead of overwriting the earlier block",
                    key,
                    definition.repository,
                    definition.module,
                    definition.block_id,
                    filename,
                )
 
            output_path = resolved_dir / filename
            save_json(output_path, definition.to_dict(), encoder=ModelEncoder)
            written_paths.append(output_path)
 
        self._logger.info(
            "Stored %d block definition(s) in %s", len(written_paths), resolved_dir
        )
        return written_paths
 
    def get_by_id(
        self,
        block_id: str,
        *,
        repository: Optional[str] = None,
        module: Optional[str] = None,
    ) -> List[BlockDefinition]:
        """Loads every stored block matching a block id.
 
        Block ids are not guaranteed globally unique across
        repositories and modules, so this returns every match rather
        than guessing which one the caller intended. Pass ``repository``
        and/or ``module`` to disambiguate down to a single result.
 
        Args:
            block_id: The block id to search for.
            repository: If given, only blocks from this repository are
                returned.
            module: If given, only blocks from this module are
                returned. Typically combined with ``repository``.
 
        Returns:
            A list of matching :class:`BlockDefinition` instances. Empty
            if no stored block matches.
        """
        return [
            definition
            for definition in self._iter_stored()
            if definition.block_id == block_id
            and (repository is None or definition.repository == repository)
            and (module is None or definition.module == module)
        ]
 
    def list_by_repository(self, repository: str) -> List[BlockDefinition]:
        """Lists every stored block belonging to a repository.
 
        Args:
            repository: The repository name to filter by.
 
        Returns:
            A list of matching :class:`BlockDefinition` instances, in
            filename order. Empty if the repository has no stored
            blocks.
        """
        return [
            definition
            for definition in self._iter_stored()
            if definition.repository == repository
        ]
 
    def list_by_module(self, repository: str, module: str) -> List[BlockDefinition]:
        """Lists every stored block belonging to a specific module.
 
        Args:
            repository: The repository name to filter by.
            module: The module name to filter by.
 
        Returns:
            A list of matching :class:`BlockDefinition` instances, in
            filename order. Empty if the module has no stored blocks.
        """
        return [
            definition
            for definition in self._iter_stored()
            if definition.repository == repository and definition.module == module
        ]
 
    def summary(self) -> Dict[str, Any]:
        """Builds a summary of everything currently in the store.
 
        Returns:
            A dictionary with the total block count, the number of
            distinct repositories and modules represented, and
            per-repository and per-module breakdowns.
        """
        by_repository: Dict[str, int] = {}
        by_module: Dict[str, int] = {}
        total = 0
 
        for definition in self._iter_stored():
            total += 1
            repository_key = definition.repository or "unknown_repository"
            by_repository[repository_key] = by_repository.get(repository_key, 0) + 1
            module_key = f"{repository_key}/{definition.module or 'unknown_module'}"
            by_module[module_key] = by_module.get(module_key, 0) + 1
 
        return {
            "total": total,
            "repositories": len(by_repository),
            "modules": len(by_module),
            "by_repository": dict(sorted(by_repository.items())),
            "by_module": dict(sorted(by_module.items())),
        }
 
    def _iter_stored(self) -> Iterator[BlockDefinition]:
        """Iterates over every block definition currently on disk.
 
        Unreadable or non-block JSON files are skipped with a logged
        warning rather than aborting the whole iteration.
 
        Yields:
            Each stored :class:`BlockDefinition`, in filename order.
        """
        if not self._storage_dir.exists():
            return
        for path in sorted(self._storage_dir.glob("*.json")):
            # Skip source reference files
            if path.name.endswith('.sources.json'):
                continue
            try:
                yield BlockDefinition.from_dict(load_json(path))
            except (OSError, ValueError, KeyError, TypeError) as exc:
                self._logger.warning("Skipping unreadable block file %s: %s", path, exc)
 
    @staticmethod
    def _build_key(definition: BlockDefinition) -> str:
        """Builds the deterministic storage key for a block definition.
 
        Args:
            definition: The block definition to build a key for.
 
        Returns:
            A filesystem-safe ``<repository>__<module>__<block_id>``
            string (without extension).
        """
        block_component = definition.block_id
        if not block_component:
            block_component = (
                definition.source_file.stem if definition.source_file else "unknown_block"
            )
 
        parts = [
            definition.repository or "unknown_repository",
            definition.module or "unknown_module",
            block_component,
        ]
        return "__".join(_sanitize_filename_part(str(part)) for part in parts)
 
 
def _sanitize_filename_part(part: str) -> str:
    """Replaces characters unsafe for filenames with underscores.
 
    Args:
        part: The raw filename component to sanitize.
 
    Returns:
        ``part`` with every character outside the safe set replaced by
        an underscore.
    """
    return "".join(char if char in _SAFE_FILENAME_CHARACTERS else "_" for char in part)