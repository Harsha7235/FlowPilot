"""GNU Radio Companion Block YAML Parser.

This module provides :class:`BlockYamlParser`, the first knowledge
extraction component for the Autonomous Knowledge Acquisition System
(AKAS). It parses GNU Radio Companion ``*.block.yml`` (and legacy
``*.block.yaml``) files into structured
:class:`~flowpilot.knowledge.parser.block_models.BlockDefinition`
objects, tolerant of the schema variation seen across GNU Radio
versions and independently-maintained out-of-tree (OOT) modules.

The parser integrates directly with the existing Repository Scanner
output: given a
:class:`~flowpilot.core.models.RepositoryInventory` or
:class:`~flowpilot.core.models.InventoryReport`, it locates every file
already classified as :attr:`~flowpilot.core.models.FileType.BLOCK_YML`
and parses it, reusing the repository, module, and version attribution
the scanner already computed rather than re-deriving it.

When a caller has no scanner inventory available and parses a file
path directly, :meth:`BlockYamlParser.parse_file` falls back to
deterministic, path-based repository/module resolution, reusing the
Repository Scanner's own repository-root heuristic (see
:func:`~flowpilot.knowledge.scanner.repository_detector.looks_like_repository_root`)
so the inference always matches what the scanner itself would have
attributed.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml

from flowpilot.core.models import FileType, InventoryReport, ModelEncoder, RepositoryInventory
from flowpilot.core.utils import configure_logger, ensure_exists, normalize_path, safe_mkdir, save_json
from flowpilot.knowledge.parser.block_models import (
    BlockDefinition,
    BlockParameter,
    BlockPort,
    ParseStatus,
)
from flowpilot.knowledge.scanner.repository_detector import looks_like_repository_root

__all__ = ["BlockYamlParser"]

_KNOWN_PARAMETER_KEYS = frozenset({"id", "label", "dtype", "default", "options"})
_KNOWN_PORT_KEYS = frozenset({"label", "domain", "dtype", "vlen", "multiplicity", "optional"})
_FILENAME_SAFE_CHARACTERS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
)


class BlockYamlParser:
    """Parses GNU Radio Companion block YAML files into structured knowledge.

    Every public parsing method is designed to never raise for a
    malformed or unusual input file: failures are captured in the
    returned :class:`~flowpilot.knowledge.parser.block_models.BlockDefinition`'s
    ``parse_status`` and ``parse_errors`` fields instead, so that one
    bad file can never abort a larger batch.
    """

    def __init__(self, *, logger: Optional[logging.Logger] = None) -> None:
        """Initializes a :class:`BlockYamlParser`.

        Args:
            logger: An optional logger to use. If omitted, a
                module-level logger is created via
                :func:`~flowpilot.core.utils.configure_logger`.
        """
        self._logger = logger or configure_logger(__name__)

    def parse_file(
        self,
        path: Union[str, Path],
        *,
        repository: Optional[str] = None,
        module: Optional[str] = None,
        version: Optional[str] = None,
    ) -> BlockDefinition:
        """Parses a single ``*.block.yml`` file into a :class:`BlockDefinition`.

        Args:
            path: The path to the block YAML file.
            repository: The name of the repository the file belongs to,
                if known.
            module: The name of the module the file belongs to, if
                known.
            version: The version of the repository the file was
                scanned at, if known.

        Returns:
            A populated
            :class:`~flowpilot.knowledge.parser.block_models.BlockDefinition`.
            On failure, ``source_file`` is still populated and
            ``parse_status`` is :attr:`~flowpilot.knowledge.parser.block_models.ParseStatus.FAILED`
            with a human-readable explanation in ``parse_errors``; no
            exception is raised.
        """
        original_path = Path(path)

        if repository is None or module is None:
            inferred_repository, inferred_module = self._infer_repository_and_module(
                normalize_path(original_path)
            )
            if repository is None:
                repository = inferred_repository
            if module is None:
                module = inferred_module

        try:
            resolved_path = ensure_exists(original_path)
        except FileNotFoundError as exc:
            return self._failed(original_path, repository, module, version, f"File not found: {exc}")

        try:
            raw_text = resolved_path.read_text(encoding="utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            return self._failed(
                resolved_path, repository, module, version, f"File is not valid UTF-8: {exc}"
            )
        except OSError as exc:
            return self._failed(
                resolved_path, repository, module, version, f"Unable to read file: {exc}"
            )

        try:
            document = yaml.safe_load(raw_text)
        except yaml.YAMLError as exc:
            return self._failed(
                resolved_path, repository, module, version, f"YAML syntax error: {exc}"
            )

        if document is None:
            return self._failed(resolved_path, repository, module, version, "File is empty")

        if not isinstance(document, dict):
            return self._failed(
                resolved_path,
                repository,
                module,
                version,
                f"Top-level YAML must be a mapping, got {type(document).__name__}",
            )

        return self._build_block_definition(
            document,
            source_file=resolved_path,
            repository=repository,
            module=module,
            version=version,
        )

    def parse_repository_inventory(self, inventory: RepositoryInventory) -> List[BlockDefinition]:
        """Parses every block YAML file referenced in a repository inventory.

        Args:
            inventory: A
                :class:`~flowpilot.core.models.RepositoryInventory`
                produced by the Repository Scanner. Its ``files`` list
                is filtered to entries classified as
                :attr:`~flowpilot.core.models.FileType.BLOCK_YML`.

        Returns:
            A list of :class:`BlockDefinition` instances, one per
            discovered block YAML file, in scanner file order.
        """
        block_files = [
            file_metadata
            for file_metadata in inventory.files
            if file_metadata.file_type == FileType.BLOCK_YML
        ]
        self._logger.info(
            "Parsing %d block YAML file(s) for repository %s",
            len(block_files),
            inventory.repository.name,
        )

        definitions: List[BlockDefinition] = []
        for file_metadata in block_files:
            definition = self.parse_file(
                file_metadata.path,
                repository=inventory.repository.name,
                module=file_metadata.module_name,
                version=inventory.repository.version,
            )
            if definition.parse_status != ParseStatus.SUCCESS:
                self._logger.warning(
                    "%s while parsing %s",
                    definition.parse_status.value,
                    file_metadata.path,
                )
            definitions.append(definition)
        return definitions

    def parse_inventory_report(self, report: InventoryReport) -> List[BlockDefinition]:
        """Parses every block YAML file referenced across an entire inventory report.

        Args:
            report: An :class:`~flowpilot.core.models.InventoryReport`
                produced by the Repository Scanner, covering one or
                more repositories.

        Returns:
            A list of :class:`BlockDefinition` instances across every
            repository in the report, in repository order.
        """
        definitions: List[BlockDefinition] = []
        for inventory in report.inventories:
            definitions.extend(self.parse_repository_inventory(inventory))
        return definitions

    def save_definitions(
        self, definitions: List[BlockDefinition], output_directory: Union[str, Path]
    ) -> List[Path]:
        """Persists parsed block definitions as individual JSON documents.

        Each block is written to its own file, named from its
        repository, module, and block id, so downstream subsystems
        (embeddings, the knowledge graph, the planner) can load
        individual blocks without reading the entire corpus.

        Args:
            definitions: The block definitions to persist.
            output_directory: The directory JSON files are written to.
                Created if it does not already exist.

        Returns:
            The paths written to, in the same order as ``definitions``.

        Raises:
            StorageError: If the output directory cannot be created.
        """
        resolved_output = safe_mkdir(output_directory)
        written_paths: List[Path] = []
        for definition in definitions:
            output_path = resolved_output / self._build_output_filename(definition)
            save_json(output_path, definition.to_dict(), encoder=ModelEncoder)
            written_paths.append(output_path)
        self._logger.info(
            "Wrote %d block definition file(s) to %s", len(written_paths), resolved_output
        )
        return written_paths

    @staticmethod
    def summarize(definitions: List[BlockDefinition]) -> Dict[str, Any]:
        """Builds a summary report for a batch of parsed block definitions.

        Args:
            definitions: The block definitions to summarize.

        Returns:
            A dictionary with ``total``, ``succeeded``, ``partial``,
            and ``failed`` counts, plus an ``errors`` mapping from
            source file path to that file's ``parse_errors``, included
            only for definitions with at least one error.
        """
        succeeded = sum(1 for item in definitions if item.parse_status == ParseStatus.SUCCESS)
        partial = sum(1 for item in definitions if item.parse_status == ParseStatus.PARTIAL)
        failed = sum(1 for item in definitions if item.parse_status == ParseStatus.FAILED)
        errors = {
            str(item.source_file): item.parse_errors for item in definitions if item.parse_errors
        }
        return {
            "total": len(definitions),
            "succeeded": succeeded,
            "partial": partial,
            "failed": failed,
            "errors": errors,
        }

    def _infer_repository_and_module(self, path: Path) -> Tuple[Optional[str], Optional[str]]:
        """Deterministically infers repository and module names from a file's location.

        This is only used as a fallback for the fields a caller did not
        explicitly supply to :meth:`parse_file` — for example, when
        parsing a bare path with no
        :class:`~flowpilot.core.models.RepositoryInventory` available.

        The primary signal is the GNU Radio Companion convention that
        every block YAML file lives somewhere beneath a ``grc``
        directory owned by its module — either directly inside it, or
        nested further within a subdirectory of it (some real modules,
        e.g. ``gr-satellites``, group related blocks under
        ``grc/<subgroup>/*.block.yml``). The nearest ancestor named
        ``grc``, at any depth, is therefore located first, and its
        *parent* is treated as the module. Whether that module is
        itself the repository root (a single-module OOT repository) or
        is nested one level inside a larger repository (an in-tree
        module) is then resolved with a single, targeted check — using
        the Repository Scanner's own
        :func:`~flowpilot.knowledge.scanner.repository_detector.looks_like_repository_root`
        marker check on exactly *one* specific candidate directory (the
        module's parent) — rather than an unbounded upward walk. An
        unbounded walk is deliberately avoided: real CMake projects
        commonly give *every* subdirectory, including ``grc/`` and its
        own subdirectories, its own small ``CMakeLists.txt`` for
        install rules, which would otherwise be misread as additional
        repository boundaries.

        If no ``grc`` ancestor is found at all, this falls back to the
        closest ancestor that looks like a repository root (per the
        same scanner marker check), leaving ``module`` as ``None``
        rather than guessing an unreliable nesting depth.

        Args:
            path: The (not necessarily existing) file path to infer
                repository and module context for.

        Returns:
            A ``(repository, module)`` tuple of names. Either or both
            may be ``None`` if no attribution could be determined.
        """
        for ancestor in path.parents:
            if ancestor.name == "grc" and ancestor.parent != ancestor:
                module_dir = ancestor.parent
                repository_dir = module_dir.parent
                if repository_dir != module_dir and looks_like_repository_root(repository_dir):
                    return repository_dir.name, module_dir.name
                return module_dir.name, module_dir.name

        for ancestor in path.parents:
            if looks_like_repository_root(ancestor):
                return ancestor.name, None

        return None, None

    def _failed(
        self,
        source_file: Path,
        repository: Optional[str],
        module: Optional[str],
        version: Optional[str],
        reason: str,
    ) -> BlockDefinition:
        """Builds a :class:`BlockDefinition` representing a failed parse.

        Args:
            source_file: The file that failed to parse.
            repository: The repository the file belongs to, if known.
            module: The module the file belongs to, if known.
            version: The repository version, if known.
            reason: A human-readable explanation of the failure.

        Returns:
            A :class:`BlockDefinition` with
            :attr:`~flowpilot.knowledge.parser.block_models.ParseStatus.FAILED`
            status and ``reason`` recorded in ``parse_errors``.
        """
        return BlockDefinition(
            source_file=source_file,
            repository=repository,
            module=module,
            version=version,
            parse_status=ParseStatus.FAILED,
            parse_errors=[reason],
        )

    def _build_block_definition(
        self,
        document: Dict[str, Any],
        *,
        source_file: Path,
        repository: Optional[str],
        module: Optional[str],
        version: Optional[str],
    ) -> BlockDefinition:
        """Converts a parsed YAML mapping into a :class:`BlockDefinition`.

        Args:
            document: The parsed top-level YAML mapping.
            source_file: The file the mapping was parsed from.
            repository: The repository the file belongs to, if known.
            module: The module the file belongs to, if known.
            version: The repository version, if known.

        Returns:
            A populated :class:`BlockDefinition`, with ``parse_status``
            reflecting whether a block id was found and whether any
            structural issues were encountered.
        """
        errors: List[str] = []

        block_id = self._coerce_str(document.get("id"))
        if not block_id:
            errors.append("Missing required 'id' field")

        label = self._coerce_str(document.get("label"))
        name = self._coerce_str(document.get("name")) or label or block_id
        category = self._coerce_category(document.get("category"))
        description = self._coerce_str(document.get("description") or document.get("desc"))
        documentation = self._coerce_str(document.get("documentation"))

        parameters = self._parse_parameters(document.get("parameters"), errors)
        inputs = self._parse_ports(document.get("inputs"), errors, "inputs")
        outputs = self._parse_ports(document.get("outputs"), errors, "outputs")

        data_types = self._collect_data_types(parameters, inputs, outputs)
        domain = self._collect_domains(inputs, outputs)
        implementation = self._coerce_str_list(document.get("flags"))

        if not block_id:
            parse_status = ParseStatus.FAILED
        elif errors:
            parse_status = ParseStatus.PARTIAL
        else:
            parse_status = ParseStatus.SUCCESS

        return BlockDefinition(
            block_id=block_id,
            name=name,
            label=label,
            category=category,
            description=description,
            documentation=documentation,
            parameters=parameters,
            inputs=inputs,
            outputs=outputs,
            data_types=data_types,
            domain=domain,
            implementation=implementation,
            source_file=source_file,
            repository=repository,
            module=module,
            version=version,
            raw_metadata=document,
            parse_status=parse_status,
            parse_errors=errors,
        )

    def _parse_parameters(self, raw_parameters: Any, errors: List[str]) -> List[BlockParameter]:
        """Parses the ``parameters`` section of a block YAML document.

        Args:
            raw_parameters: The raw value of the ``parameters`` key, or
                ``None`` if absent.
            errors: A list to append human-readable structural warnings
                to, in place.

        Returns:
            A list of :class:`BlockParameter` instances. Empty if
            ``raw_parameters`` was absent or malformed.
        """
        if raw_parameters is None:
            return []
        if not isinstance(raw_parameters, list):
            errors.append(f"'parameters' expected a list, got {type(raw_parameters).__name__}")
            return []

        parameters: List[BlockParameter] = []
        for index, entry in enumerate(raw_parameters):
            if not isinstance(entry, dict):
                errors.append(f"parameters[{index}] is not a mapping; skipped")
                continue
            parameters.append(
                BlockParameter(
                    id=self._coerce_str(entry.get("id")),
                    label=self._coerce_str(entry.get("label")),
                    dtype=self._coerce_str(entry.get("dtype")),
                    default=entry.get("default"),
                    options=list(entry.get("options") or []),
                    extra={
                        key: value
                        for key, value in entry.items()
                        if key not in _KNOWN_PARAMETER_KEYS
                    },
                )
            )
        return parameters

    def _parse_ports(
        self, raw_ports: Any, errors: List[str], field_name: str
    ) -> List[BlockPort]:
        """Parses an ``inputs`` or ``outputs`` section of a block YAML document.

        Args:
            raw_ports: The raw value of the ``inputs``/``outputs`` key,
                or ``None`` if absent.
            errors: A list to append human-readable structural warnings
                to, in place.
            field_name: The name of the field being parsed (``"inputs"``
                or ``"outputs"``), used in warning messages.

        Returns:
            A list of :class:`BlockPort` instances. Empty if
            ``raw_ports`` was absent or malformed.
        """
        if raw_ports is None:
            return []
        if not isinstance(raw_ports, list):
            errors.append(f"'{field_name}' expected a list, got {type(raw_ports).__name__}")
            return []

        ports: List[BlockPort] = []
        for index, entry in enumerate(raw_ports):
            if not isinstance(entry, dict):
                errors.append(f"{field_name}[{index}] is not a mapping; skipped")
                continue
            ports.append(
                BlockPort(
                    label=self._coerce_str(entry.get("label")),
                    domain=self._coerce_str(entry.get("domain")),
                    dtype=self._coerce_str(entry.get("dtype")),
                    vlen=entry.get("vlen"),
                    multiplicity=self._coerce_str(entry.get("multiplicity")),
                    optional=bool(entry.get("optional", False)),
                    extra={
                        key: value for key, value in entry.items() if key not in _KNOWN_PORT_KEYS
                    },
                )
            )
        return ports

    @staticmethod
    def _coerce_str(value: Any) -> Optional[str]:
        """Coerces an arbitrary YAML value into a stripped string, or ``None``.

        Args:
            value: The value to coerce.

        Returns:
            A non-empty stripped string, or ``None`` if ``value`` was
            ``None`` or an empty/whitespace-only string.
        """
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return str(value)

    @staticmethod
    def _coerce_category(value: Any) -> Optional[str]:
        """Normalizes a ``category`` value into a single ``/``-joined string.

        GNU Radio block YAML declares ``category`` either as a single
        string (e.g. ``"[Core]/IQ Correction"``) or, in some schemas, as
        a list of path segments. Both forms are normalized to the same
        string representation.

        Args:
            value: The raw ``category`` value.

        Returns:
            A normalized category string, or ``None`` if ``value`` was
            absent or empty.
        """
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        if isinstance(value, list):
            parts = [str(item).strip() for item in value if str(item).strip()]
            return "/".join(parts) if parts else None
        return str(value)

    @staticmethod
    def _coerce_str_list(value: Any) -> List[str]:
        """Normalizes a scalar-or-list YAML value into a list of strings.

        Args:
            value: The raw value (``None``, a scalar, or a list).

        Returns:
            A list of strings. Empty if ``value`` was ``None`` or an
            empty string.
        """
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value.strip() else []
        if isinstance(value, (list, tuple)):
            return [str(item) for item in value if item is not None]
        return [str(value)]

    @staticmethod
    def _collect_data_types(
        parameters: List[BlockParameter], inputs: List[BlockPort], outputs: List[BlockPort]
    ) -> List[str]:
        """Collects the distinct, non-empty ``dtype`` values across a block.

        Args:
            parameters: The block's parsed parameters.
            inputs: The block's parsed input ports.
            outputs: The block's parsed output ports.

        Returns:
            A sorted list of distinct ``dtype`` strings.
        """
        found = {parameter.dtype for parameter in parameters if parameter.dtype}
        found.update(port.dtype for port in (*inputs, *outputs) if port.dtype)
        return sorted(found)

    @staticmethod
    def _collect_domains(inputs: List[BlockPort], outputs: List[BlockPort]) -> List[str]:
        """Collects the distinct, non-empty ``domain`` values across a block's ports.

        Args:
            inputs: The block's parsed input ports.
            outputs: The block's parsed output ports.

        Returns:
            A sorted list of distinct ``domain`` strings (e.g.
            ``["message", "stream"]``).
        """
        found = {port.domain for port in (*inputs, *outputs) if port.domain}
        return sorted(found)

    @staticmethod
    def _build_output_filename(definition: BlockDefinition) -> str:
        """Builds a filesystem-safe output filename for a block definition.

        Args:
            definition: The block definition to name a file for.

        Returns:
            A filename of the form
            ``<repository>__<module>__<block_id>.json``, with every
            component sanitized to filesystem-safe characters.
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
        safe_parts = [_sanitize_filename_part(part) for part in parts]
        return "__".join(safe_parts) + ".json"


def _sanitize_filename_part(part: str) -> str:
    """Replaces characters unsafe for filenames with underscores.

    Args:
        part: The raw filename component to sanitize.

    Returns:
        ``part`` with every character outside the safe set replaced by
        an underscore.
    """
    return "".join(char if char in _FILENAME_SAFE_CHARACTERS else "_" for char in str(part))