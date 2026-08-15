"""Shared data models for the FlowPilot Agentic AI Platform.
 
This module defines every core data structure that is shared across the
FlowPilot platform's subsystems, including the Repository Scanner, the
Autonomous Knowledge Acquisition System (AKAS), the Repository Discovery
Engine, the YAML/GRC/Python/C++/Documentation parsers, the Knowledge
Warehouse, the Neo4j Knowledge Graph, the Embedding Engine, the Planner,
the Generator, the Validator, the API layer, and the Frontend.
 
These models intentionally contain no business logic. They are pure data
containers with serialization helpers so that every subsystem can rely on
a single, consistent contract for exchanging information.
 
Typical usage example:
 
    metadata = RepositoryMetadata(
        repository_id="grc-3.10",
        name="gnuradio",
        repository_type=RepositoryType.GNU_RADIO,
    )
    payload = metadata.to_json_dict()
"""
 
from __future__ import annotations
 
import json
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Type, TypeVar, Union
 
__all__ = [
    "RepositoryType",
    "FileType",
    "KnowledgeSourceType",
    "ScanStatus",
    "ModelEncoder",
    "BaseModel",
    "FileMetadata",
    "ModuleMetadata",
    "RepositoryStatistics",
    "RepositoryMetadata",
    "KnowledgeSource",
    "RepositoryInventory",
    "InventoryReport",
]
 
T = TypeVar("T", bound="BaseModel")
 
 
# =====================================================================
# ENUMS
# =====================================================================
 
 
class RepositoryType(str, Enum):
    """Classification of a repository discovered or scanned by FlowPilot.
 
    Attributes:
        GNU_RADIO: The core GNU Radio repository itself.
        OOT_MODULE: An out-of-tree (OOT) GNU Radio module.
        HARDWARE_SDK: A hardware vendor SDK (e.g. UHD, SoapySDR, BladeRF).
        USER_PROJECT: A user-authored project that consumes GNU Radio.
        UNKNOWN: The repository type could not be determined.
    """
 
    GNU_RADIO = "gnu_radio"
    OOT_MODULE = "oot_module"
    HARDWARE_SDK = "hardware_sdk"
    USER_PROJECT = "user_project"
    UNKNOWN = "unknown"
 
 
class FileType(str, Enum):
    """Classification of a file discovered during repository scanning.
 
    Attributes:
        BLOCK_YML: A GNU Radio Companion block definition (``*.block.yml``).
        TREE_YML: A GNU Radio Companion category tree file (``*.tree.yml``).
        GRC: A GNU Radio Companion flowgraph file (``*.grc``).
        PYTHON: A Python source file (``*.py``).
        CPP_SOURCE: A C++ source file (``*.cc`` or ``*.cpp``).
        CPP_HEADER: A C++ header file (``*.hpp`` or ``*.h``).
        MARKDOWN: A Markdown document (``*.md``).
        RESTRUCTURED_TEXT: A reStructuredText document (``*.rst``).
        JSON: A JSON document (``*.json``).
        TEXT: A plain text document (``*.txt``).
        CMAKE: A CMake build file (``CMakeLists.txt`` or ``*.cmake``).
        IMAGE: An image asset (e.g. ``*.png``, ``*.jpg``, ``*.svg``).
        UNKNOWN: The file type could not be determined.
    """
 
    BLOCK_YML = "block_yml"
    TREE_YML = "tree_yml"
    GRC = "grc"
    PYTHON = "python"
    CPP_SOURCE = "cpp_source"
    CPP_HEADER = "cpp_header"
    MARKDOWN = "markdown"
    RESTRUCTURED_TEXT = "restructured_text"
    JSON = "json"
    TEXT = "text"
    CMAKE = "cmake"
    IMAGE = "image"
    UNKNOWN = "unknown"
 
    @classmethod
    def from_suffix(cls, suffix: str) -> "FileType":
        """Resolves a :class:`FileType` from a file suffix or filename.
 
        Args:
            suffix: A file extension (with or without a leading dot) or a
                full filename, e.g. ``".py"``, ``"py"``, or
                ``"foo.block.yml"``.
 
        Returns:
            The matching :class:`FileType`, or :attr:`FileType.UNKNOWN` if
            no match is found.
        """
        normalized = suffix.lower().lstrip(".")
        if normalized.endswith("block.yml") or normalized.endswith("block.yaml"):
            return cls.BLOCK_YML
        if normalized.endswith("tree.yml") or normalized.endswith("tree.yaml"):
            return cls.TREE_YML
        mapping: Dict[str, "FileType"] = {
            "grc": cls.GRC,
            "py": cls.PYTHON,
            "cc": cls.CPP_SOURCE,
            "cpp": cls.CPP_SOURCE,
            "cxx": cls.CPP_SOURCE,
            "hpp": cls.CPP_HEADER,
            "h": cls.CPP_HEADER,
            "hxx": cls.CPP_HEADER,
            "md": cls.MARKDOWN,
            "rst": cls.RESTRUCTURED_TEXT,
            "json": cls.JSON,
            "txt": cls.TEXT,
            "cmake": cls.CMAKE,
            "png": cls.IMAGE,
            "jpg": cls.IMAGE,
            "jpeg": cls.IMAGE,
            "svg": cls.IMAGE,
            "gif": cls.IMAGE,
            "bmp": cls.IMAGE,
        }
        return mapping.get(normalized, cls.UNKNOWN)
 
 
class KnowledgeSourceType(str, Enum):
    """Classification of the origin of an ingested knowledge source.
 
    Attributes:
        GIT: A Git repository (local clone or remote reference).
        WEBSITE: A crawled or fetched website.
        PDF: A PDF document (datasheet, paper, manual, etc.).
        API: A knowledge source accessed via an external API.
        LOCAL: A knowledge source located on the local filesystem.
    """
 
    GIT = "git"
    WEBSITE = "website"
    PDF = "pdf"
    API = "api"
    LOCAL = "local"
 
 
class ScanStatus(str, Enum):
    """Lifecycle status of a repository scan or knowledge acquisition job.
 
    Attributes:
        NOT_STARTED: The job has been created but has not begun executing.
        RUNNING: The job is currently executing.
        COMPLETED: The job finished successfully.
        FAILED: The job terminated due to an error.
    """
 
    NOT_STARTED = "not_started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
 
 
# =====================================================================
# JSON ENCODING
# =====================================================================
 
 
class ModelEncoder(json.JSONEncoder):
    """A :class:`json.JSONEncoder` that recursively serializes FlowPilot models.
 
    Handles :class:`~pathlib.Path`, :class:`~datetime.datetime`,
    :class:`~enum.Enum`, dataclasses (including nested dataclasses),
    lists, tuples, sets, and dicts, converting each into a JSON
    serializable representation.
    """
 
    def default(self, o: Any) -> Any:  # noqa: D102 - documented on class.
        if isinstance(o, Path):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, Enum):
            return o.value
        if is_dataclass(o) and not isinstance(o, type):
            return _dataclass_to_serializable(o)
        if isinstance(o, (set, frozenset)):
            return [self.default(item) if _needs_default(item) else item for item in sorted(o, key=str)]
        return super().default(o)
 
 
def _needs_default(value: Any) -> bool:
    """Determines whether a value requires custom encoding logic.
 
    Args:
        value: The value to inspect.
 
    Returns:
        ``True`` if the value is not natively JSON serializable.
    """
    return isinstance(value, (Path, datetime, Enum)) or (
        is_dataclass(value) and not isinstance(value, type)
    )
 
 
def _serialize_value(value: Any) -> Any:
    """Recursively converts a single value into a JSON serializable form.
 
    Args:
        value: An arbitrary value that may be a primitive, a
            :class:`~pathlib.Path`, a :class:`~datetime.datetime`, an
            :class:`~enum.Enum`, a dataclass instance, or a container of
            any of the above.
 
    Returns:
        A value composed only of ``dict``, ``list``, ``str``, ``int``,
        ``float``, ``bool``, and ``None``.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return _dataclass_to_serializable(value)
    if isinstance(value, dict):
        return {str(_serialize_value(k)): _serialize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [_serialize_value(item) for item in sorted(value, key=str)]
    return value
 
 
def _dataclass_to_serializable(instance: Any) -> Dict[str, Any]:
    """Converts a dataclass instance into a nested, JSON serializable dict.
 
    Unlike :func:`dataclasses.asdict`, this does not naively recurse via
    ``copy.deepcopy``; instead it explicitly resolves ``Path``,
    ``datetime``, ``Enum``, and nested dataclass fields.
 
    Args:
        instance: The dataclass instance to convert.
 
    Returns:
        A dictionary whose values are all JSON serializable.
    """
    result: Dict[str, Any] = {}
    for f in fields(instance):
        result[f.name] = _serialize_value(getattr(instance, f.name))
    return result
 
 
# =====================================================================
# BASE MODEL
# =====================================================================
 
 
@dataclass(slots=True)
class BaseModel:
    """Base class for every FlowPilot data model.
 
    Provides consistent, explicit (non-``asdict``-reliant) serialization
    and deserialization behavior shared by all subclasses. Subclasses are
    expected to be decorated with ``@dataclass(slots=True)`` themselves.
    """
 
    _FIELD_ALIASES: ClassVar[Dict[str, str]] = {}
 
    def to_dict(self) -> Dict[str, Any]:
        """Converts this model into a plain Python dictionary.
 
        Nested dataclasses, enums, ``Path`` objects, and ``datetime``
        objects are recursively resolved into JSON-friendly primitives,
        while the top-level return type remains a standard ``dict``.
 
        Returns:
            A dictionary representation of this model.
        """
        return _dataclass_to_serializable(self)
 
    def to_json_dict(self) -> Dict[str, Any]:
        """Converts this model into a strictly JSON serializable dictionary.
 
        This is functionally equivalent to :meth:`to_dict` but exists as a
        distinct, explicit entry point for callers (such as the API layer)
        that require a guarantee of JSON compatibility.
 
        Returns:
            A dictionary containing only JSON serializable values.
        """
        return json.loads(json.dumps(self.to_dict(), cls=ModelEncoder))
 
    def to_json(self, *, indent: Optional[int] = 2) -> str:
        """Serializes this model directly to a JSON string.
 
        Args:
            indent: The indentation level passed to :func:`json.dumps`.
                Defaults to ``2``. Pass ``None`` for compact output.
 
        Returns:
            A JSON string representation of this model.
        """
        return json.dumps(self.to_dict(), cls=ModelEncoder, indent=indent)
 
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Builds a model instance from a plain dictionary.
 
        Only keys matching declared dataclass fields are consumed; unknown
        keys are ignored so that forward-compatible payloads do not raise
        errors. Subclasses that contain nested dataclasses, ``Enum``
        fields, ``Path`` fields, or ``datetime`` fields should override
        this method to perform the appropriate coercion, calling
        ``super().from_dict(data)`` is not required since this base
        implementation performs a direct, shallow field mapping.
 
        Args:
            data: A dictionary of field values, typically produced by
                :meth:`to_dict` or :meth:`to_json_dict`.
 
        Returns:
            A new instance of ``cls`` populated from ``data``.
        """
        valid_field_names = {f.name for f in fields(cls)}
        filtered = {key: value for key, value in data.items() if key in valid_field_names}
        return cls(**filtered)
 
 
# =====================================================================
# HELPER PARSERS FOR from_dict IMPLEMENTATIONS
# =====================================================================
 
 
def _parse_datetime(value: Union[str, datetime, None]) -> Optional[datetime]:
    """Parses a value into a :class:`~datetime.datetime` instance.
 
    Args:
        value: An ISO-8601 string, an existing ``datetime``, or ``None``.
 
    Returns:
        A ``datetime`` instance, or ``None`` if ``value`` is ``None``.
    """
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
 
 
def _parse_path(value: Union[str, Path, None]) -> Optional[Path]:
    """Parses a value into a :class:`~pathlib.Path` instance.
 
    Args:
        value: A path string, an existing ``Path``, or ``None``.
 
    Returns:
        A ``Path`` instance, or ``None`` if ``value`` is ``None``.
    """
    if value is None or isinstance(value, Path):
        return value
    return Path(value)
 
 
def _utc_now() -> datetime:
    """Returns the current UTC time.
 
    Returns:
        The current timezone-aware :class:`~datetime.datetime` in UTC.
    """
    return datetime.now(timezone.utc)
 
 
# =====================================================================
# FILE METADATA
# =====================================================================
 
 
@dataclass(slots=True)
class FileMetadata(BaseModel):
    """Metadata describing a single file discovered during a repository scan.
 
    Attributes:
        path: The absolute or repository-relative path to the file.
        file_type: The classified :class:`FileType` of the file.
        size_bytes: The size of the file, in bytes.
        sha256: The SHA-256 hex digest of the file's contents.
        parser: The name of the parser responsible for interpreting this
            file (e.g. ``"YamlParser"``, ``"PythonParser"``), if any.
        module_name: The name of the module this file belongs to, if
            applicable.
        last_modified: The last-modified timestamp of the file, sourced
            from the filesystem or version control history.
        encoding: The detected text encoding of the file, if applicable.
        is_binary: Whether the file is a binary (non-text) file.
        tags: Free-form tags attached to this file for search and
            filtering purposes.
        extra: Parser-specific or subsystem-specific auxiliary data that
            does not warrant a first-class field.
    """
 
    path: Path
    file_type: FileType = FileType.UNKNOWN
    size_bytes: int = 0
    sha256: Optional[str] = None
    parser: Optional[str] = None
    module_name: Optional[str] = None
    last_modified: Optional[datetime] = None
    encoding: Optional[str] = "utf-8"
    is_binary: bool = False
    tags: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
 
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileMetadata":
        """Builds a :class:`FileMetadata` instance from a dictionary.
 
        Args:
            data: A dictionary produced by :meth:`~BaseModel.to_dict` or
                an equivalent structure.
 
        Returns:
            A new :class:`FileMetadata` instance.
        """
        payload = dict(data)
        payload["path"] = _parse_path(payload.get("path"))
        raw_file_type = payload.get("file_type", FileType.UNKNOWN)
        payload["file_type"] = (
            raw_file_type if isinstance(raw_file_type, FileType) else FileType(raw_file_type)
        )
        payload["last_modified"] = _parse_datetime(payload.get("last_modified"))
        valid_field_names = {f.name for f in fields(cls)}
        filtered = {key: value for key, value in payload.items() if key in valid_field_names}
        return cls(**filtered)
 
 
# =====================================================================
# MODULE METADATA
# =====================================================================
 
 
@dataclass(slots=True)
class ModuleMetadata(BaseModel):
    """Metadata describing a single GNU Radio module (in-tree or OOT).
 
    Attributes:
        name: The canonical module name (e.g. ``"gr-digital"``).
        namespace: The C++ / GRC namespace associated with the module
            (e.g. ``"digital"``).
        version: The module's version string, if known.
        description: A human-readable summary of the module's purpose.
        block_count: The number of GNU Radio Companion blocks defined by
            this module.
        block_yml_files: Paths to ``*.block.yml`` files owned by this
            module.
        python_files: Paths to Python source files owned by this module.
        cpp_files: Paths to C++ source and header files owned by this
            module.
        dependencies: Names of other modules this module depends on.
        maintainers: Names or handles of the module's maintainers.
        tags: Free-form tags attached to this module for search and
            filtering purposes.
        extra: Parser-specific or subsystem-specific auxiliary data.
    """
 
    name: str
    namespace: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    block_count: int = 0
    block_yml_files: List[Path] = field(default_factory=list)
    python_files: List[Path] = field(default_factory=list)
    cpp_files: List[Path] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    maintainers: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
 
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModuleMetadata":
        """Builds a :class:`ModuleMetadata` instance from a dictionary.
 
        Args:
            data: A dictionary produced by :meth:`~BaseModel.to_dict` or
                an equivalent structure.
 
        Returns:
            A new :class:`ModuleMetadata` instance.
        """
        payload = dict(data)
        for path_field in ("block_yml_files", "python_files", "cpp_files"):
            if payload.get(path_field):
                payload[path_field] = [_parse_path(item) for item in payload[path_field]]
        valid_field_names = {f.name for f in fields(cls)}
        filtered = {key: value for key, value in payload.items() if key in valid_field_names}
        return cls(**filtered)
 
 
# =====================================================================
# REPOSITORY STATISTICS
# =====================================================================
 
 
@dataclass(slots=True)
class RepositoryStatistics(BaseModel):
    """Aggregate statistics computed for a scanned repository.
 
    Attributes:
        total_files: The total number of files discovered.
        total_directories: The total number of directories discovered.
        total_size_bytes: The cumulative size, in bytes, of all files.
        files_by_type: A mapping from :class:`FileType` value to the
            count of files of that type.
        module_count: The number of modules discovered.
        block_count: The total number of GNU Radio Companion blocks
            discovered across all modules.
        line_count_by_language: A mapping from language name (e.g.
            ``"python"``, ``"cpp"``) to total line count.
        scan_duration_seconds: The wall-clock duration of the scan, in
            seconds.
    """
 
    total_files: int = 0
    total_directories: int = 0
    total_size_bytes: int = 0
    files_by_type: Dict[str, int] = field(default_factory=dict)
    module_count: int = 0
    block_count: int = 0
    line_count_by_language: Dict[str, int] = field(default_factory=dict)
    scan_duration_seconds: float = 0.0
 
 
# =====================================================================
# REPOSITORY METADATA
# =====================================================================
 
 
@dataclass(slots=True)
class RepositoryMetadata(BaseModel):
    """Top-level metadata describing a repository known to FlowPilot.
 
    Attributes:
        repository_id: A stable, unique identifier for the repository
            (e.g. a slug or UUID).
        name: The human-readable repository name.
        repository_type: The classified :class:`RepositoryType`.
        local_path: The local filesystem path to the repository clone, if
            available.
        remote_url: The remote URL (e.g. Git origin) of the repository.
        version: The checked-out version, tag, or release string.
        branch: The checked-out branch name.
        commit_hash: The checked-out commit SHA.
        description: A human-readable summary of the repository.
        license: The SPDX license identifier of the repository, if known.
        modules: The modules discovered within this repository.
        scan_status: The current :class:`ScanStatus` of the repository.
        scanned_at: The timestamp at which the most recent scan
            completed.
        created_at: The timestamp at which this metadata record was
            first created.
        updated_at: The timestamp at which this metadata record was last
            updated.
        tags: Free-form tags attached to this repository for search and
            filtering purposes.
        extra: Subsystem-specific auxiliary data.
    """
 
    repository_id: str
    name: str
    repository_type: RepositoryType = RepositoryType.UNKNOWN
    local_path: Optional[Path] = None
    remote_url: Optional[str] = None
    version: Optional[str] = None
    branch: Optional[str] = None
    commit_hash: Optional[str] = None
    description: Optional[str] = None
    license: Optional[str] = None
    modules: List[ModuleMetadata] = field(default_factory=list)
    scan_status: ScanStatus = ScanStatus.NOT_STARTED
    scanned_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
    tags: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
 
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RepositoryMetadata":
        """Builds a :class:`RepositoryMetadata` instance from a dictionary.
 
        Args:
            data: A dictionary produced by :meth:`~BaseModel.to_dict` or
                an equivalent structure.
 
        Returns:
            A new :class:`RepositoryMetadata` instance.
        """
        payload = dict(data)
        payload["local_path"] = _parse_path(payload.get("local_path"))
        raw_repo_type = payload.get("repository_type", RepositoryType.UNKNOWN)
        payload["repository_type"] = (
            raw_repo_type
            if isinstance(raw_repo_type, RepositoryType)
            else RepositoryType(raw_repo_type)
        )
        raw_status = payload.get("scan_status", ScanStatus.NOT_STARTED)
        payload["scan_status"] = (
            raw_status if isinstance(raw_status, ScanStatus) else ScanStatus(raw_status)
        )
        payload["scanned_at"] = _parse_datetime(payload.get("scanned_at"))
        payload["created_at"] = _parse_datetime(payload.get("created_at")) or _utc_now()
        payload["updated_at"] = _parse_datetime(payload.get("updated_at")) or _utc_now()
        raw_modules = payload.get("modules") or []
        payload["modules"] = [
            module if isinstance(module, ModuleMetadata) else ModuleMetadata.from_dict(module)
            for module in raw_modules
        ]
        valid_field_names = {f.name for f in fields(cls)}
        filtered = {key: value for key, value in payload.items() if key in valid_field_names}
        return cls(**filtered)
 
 
# =====================================================================
# KNOWLEDGE SOURCE
# =====================================================================
 
 
@dataclass(slots=True)
class KnowledgeSource(BaseModel):
    """A single source of engineering knowledge ingested by AKAS.
 
    Attributes:
        source_id: A stable, unique identifier for the knowledge source.
        source_type: The classified :class:`KnowledgeSourceType`.
        uri: The location of the source (a URL, local path, or API
            endpoint), represented as a string for URI flexibility.
        title: A human-readable title for the source.
        checksum: A content checksum (e.g. SHA-256) used for change
            detection and deduplication.
        fetched_at: The timestamp at which the source was last fetched.
        related_repository_id: The identifier of the
            :class:`RepositoryMetadata` this source is associated with,
            if any.
        embedding_ids: Identifiers of embeddings generated from this
            source, for cross-referencing with the Embedding Engine.
        confidence_score: A confidence score in ``[0.0, 1.0]`` indicating
            the reliability of the source.
        tags: Free-form tags attached to this source for search and
            filtering purposes.
        extra: Subsystem-specific auxiliary data.
    """
 
    source_id: str
    source_type: KnowledgeSourceType
    uri: str
    title: Optional[str] = None
    checksum: Optional[str] = None
    fetched_at: Optional[datetime] = None
    related_repository_id: Optional[str] = None
    embedding_ids: List[str] = field(default_factory=list)
    confidence_score: float = 1.0
    tags: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
 
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeSource":
        """Builds a :class:`KnowledgeSource` instance from a dictionary.
 
        Args:
            data: A dictionary produced by :meth:`~BaseModel.to_dict` or
                an equivalent structure.
 
        Returns:
            A new :class:`KnowledgeSource` instance.
        """
        payload = dict(data)
        raw_source_type = payload.get("source_type")
        payload["source_type"] = (
            raw_source_type
            if isinstance(raw_source_type, KnowledgeSourceType)
            else KnowledgeSourceType(raw_source_type)
        )
        payload["fetched_at"] = _parse_datetime(payload.get("fetched_at"))
        valid_field_names = {f.name for f in fields(cls)}
        filtered = {key: value for key, value in payload.items() if key in valid_field_names}
        return cls(**filtered)
 
 
# =====================================================================
# REPOSITORY INVENTORY
# =====================================================================
 
 
@dataclass(slots=True)
class RepositoryInventory(BaseModel):
    """A complete inventory of files and statistics for a single repository.
 
    Attributes:
        repository: The :class:`RepositoryMetadata` this inventory
            belongs to.
        files: The complete list of :class:`FileMetadata` discovered.
        statistics: Aggregate :class:`RepositoryStatistics` for the
            repository.
        knowledge_sources: Knowledge sources associated with this
            repository (e.g. its README, linked documentation).
        generated_at: The timestamp at which this inventory was
            generated.
    """
 
    repository: RepositoryMetadata
    files: List[FileMetadata] = field(default_factory=list)
    statistics: RepositoryStatistics = field(default_factory=RepositoryStatistics)
    knowledge_sources: List[KnowledgeSource] = field(default_factory=list)
    generated_at: datetime = field(default_factory=_utc_now)
 
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RepositoryInventory":
        """Builds a :class:`RepositoryInventory` instance from a dictionary.
 
        Args:
            data: A dictionary produced by :meth:`~BaseModel.to_dict` or
                an equivalent structure.
 
        Returns:
            A new :class:`RepositoryInventory` instance.
        """
        payload = dict(data)
        raw_repository = payload.get("repository")
        payload["repository"] = (
            raw_repository
            if isinstance(raw_repository, RepositoryMetadata)
            else RepositoryMetadata.from_dict(raw_repository)
        )
        raw_files = payload.get("files") or []
        payload["files"] = [
            file_meta if isinstance(file_meta, FileMetadata) else FileMetadata.from_dict(file_meta)
            for file_meta in raw_files
        ]
        raw_statistics = payload.get("statistics")
        if raw_statistics is None:
            payload["statistics"] = RepositoryStatistics()
        elif isinstance(raw_statistics, RepositoryStatistics):
            payload["statistics"] = raw_statistics
        else:
            payload["statistics"] = RepositoryStatistics.from_dict(raw_statistics)
        raw_sources = payload.get("knowledge_sources") or []
        payload["knowledge_sources"] = [
            source if isinstance(source, KnowledgeSource) else KnowledgeSource.from_dict(source)
            for source in raw_sources
        ]
        payload["generated_at"] = _parse_datetime(payload.get("generated_at")) or _utc_now()
        valid_field_names = {f.name for f in fields(cls)}
        filtered = {key: value for key, value in payload.items() if key in valid_field_names}
        return cls(**filtered)
 
 
# =====================================================================
# INVENTORY REPORT
# =====================================================================
 
 
@dataclass(slots=True)
class InventoryReport(BaseModel):
    """A top-level report aggregating inventories across many repositories.
 
    This is the primary artifact produced by the Repository Discovery
    Engine after a full scan pass and is consumed by the Knowledge
    Warehouse for downstream ingestion into the Neo4j Knowledge Graph.
 
    Attributes:
        report_id: A stable, unique identifier for this report.
        inventories: The per-repository :class:`RepositoryInventory`
            entries included in this report.
        total_repositories: The total number of repositories included in
            this report.
        overall_status: The aggregate :class:`ScanStatus` of the report.
        errors: Human-readable error messages collected during the scan,
            if any repositories failed.
        started_at: The timestamp at which report generation began.
        completed_at: The timestamp at which report generation finished.
        extra: Subsystem-specific auxiliary data.
    """
 
    report_id: str
    inventories: List[RepositoryInventory] = field(default_factory=list)
    total_repositories: int = 0
    overall_status: ScanStatus = ScanStatus.NOT_STARTED
    errors: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    extra: Dict[str, Any] = field(default_factory=dict)
 
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InventoryReport":
        """Builds an :class:`InventoryReport` instance from a dictionary.
 
        Args:
            data: A dictionary produced by :meth:`~BaseModel.to_dict` or
                an equivalent structure.
 
        Returns:
            A new :class:`InventoryReport` instance.
        """
        payload = dict(data)
        raw_inventories = payload.get("inventories") or []
        payload["inventories"] = [
            inventory
            if isinstance(inventory, RepositoryInventory)
            else RepositoryInventory.from_dict(inventory)
            for inventory in raw_inventories
        ]
        raw_status = payload.get("overall_status", ScanStatus.NOT_STARTED)
        payload["overall_status"] = (
            raw_status if isinstance(raw_status, ScanStatus) else ScanStatus(raw_status)
        )
        payload["started_at"] = _parse_datetime(payload.get("started_at"))
        payload["completed_at"] = _parse_datetime(payload.get("completed_at"))
        valid_field_names = {f.name for f in fields(cls)}
        filtered = {key: value for key, value in payload.items() if key in valid_field_names}
        return cls(**filtered)