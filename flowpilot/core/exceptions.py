"""Exception hierarchy for the FlowPilot Agentic AI Platform.
 
This module defines every exception type raised across FlowPilot's
subsystems, including the Repository Scanner, the Autonomous Knowledge
Acquisition System (AKAS), the Repository Discovery Engine, the
YAML/GRC/Python/C++/Documentation parsers, the Knowledge Warehouse, the
Neo4j Knowledge Graph, the Embedding Engine, the Planner, the Generator,
the Validator, the API layer, and the Frontend.
 
All exceptions ultimately derive from :class:`FlowPilotError`, which
carries a human-readable ``message`` plus an optional ``details``
mapping for structured, machine-inspectable context (e.g. a repository
identifier, a file path, or a parser name). This allows callers such as
the API layer to catch a single base type when appropriate, while still
allowing fine-grained ``except`` clauses for specific failure modes.
 
Typical usage example:
 
    try:
        scanner.scan(repository_path)
    except RepositoryNotFoundError as exc:
        logger.error("Repository missing: %s", exc)
    except ScannerError as exc:
        logger.error("Scan failed: %s", exc.details)
"""
 
from __future__ import annotations
 
from pathlib import Path
from typing import Any, Dict, Optional, Union
 
__all__ = [
    "FlowPilotError",
    "RepositoryError",
    "RepositoryNotFoundError",
    "InvalidRepositoryError",
    "UnsupportedRepositoryError",
    "ScannerError",
    "ScanFailedError",
    "InventoryBuildError",
    "ParserError",
    "YAMLParserError",
    "GRCParserError",
    "PythonParserError",
    "CPPParserError",
    "DocumentationParserError",
    "KnowledgeError",
    "WarehouseError",
    "GraphError",
    "EmbeddingError",
    "ValidationError",
    "ConfigurationError",
    "MetadataError",
    "AcquisitionError",
    "DownloadError",
    "SynchronizationError",
    "StorageError",
    "SerializationError",
    "DeserializationError",
]
 
 
# =====================================================================
# BASE EXCEPTION
# =====================================================================
 
 
class FlowPilotError(Exception):
    """Base class for every exception raised by the FlowPilot platform.
 
    Carries a human-readable message alongside an optional ``details``
    mapping that subsystems can populate with structured context (e.g.
    ``{"repository_id": "grc-3.10"}``) for logging, telemetry, or API
    error responses. An optional ``cause`` may be supplied to preserve
    the original exception that triggered this one, in addition to
    Python's native exception chaining via ``raise ... from ...``.
 
    Attributes:
        message: A human-readable description of the error.
        details: Structured, machine-inspectable context about the
            error. Never ``None``; defaults to an empty ``dict``.
        cause: The underlying exception that caused this error, if any.
    """
 
    def __init__(
        self,
        message: str,
        *,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        """Initializes a :class:`FlowPilotError`.
 
        Args:
            message: A human-readable description of the error.
            details: Structured, machine-inspectable context about the
                error.
            cause: The underlying exception that caused this error, if
                any. If provided and Python's implicit exception chain
                is not already set, this is also used as the exception's
                ``__cause__``.
        """
        super().__init__(message)
        self.message = message
        self.details: Dict[str, Any] = dict(details) if details else {}
        self.cause = cause
        if cause is not None and self.__cause__ is None:
            self.__cause__ = cause
 
    def __str__(self) -> str:
        """Renders the error message together with any structured details.
 
        Returns:
            The error message, suffixed with a rendering of ``details``
            when non-empty.
        """
        if not self.details:
            return self.message
        rendered_details = ", ".join(f"{key}={value!r}" for key, value in self.details.items())
        return f"{self.message} ({rendered_details})"
 
    def __repr__(self) -> str:
        """Returns an unambiguous, debugger-friendly representation.
 
        Returns:
            A string of the form ``ClassName(message='...', details={...})``.
        """
        return f"{type(self).__name__}(message={self.message!r}, details={self.details!r})"
 
 
# =====================================================================
# REPOSITORY ERRORS
# =====================================================================
 
 
class RepositoryError(FlowPilotError):
    """Base class for errors related to repository identification or access."""
 
 
class RepositoryNotFoundError(RepositoryError):
    """Raised when a referenced repository cannot be located.
 
    This covers both a missing local clone (a filesystem path that does
    not exist) and an unresolvable repository identifier (e.g. one not
    present in the Knowledge Warehouse).
    """
 
    def __init__(
        self,
        repository: Union[str, Path],
        *,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        """Initializes a :class:`RepositoryNotFoundError`.
 
        Args:
            repository: The repository identifier or filesystem path
                that could not be found.
            details: Additional structured context about the error.
            cause: The underlying exception that caused this error, if
                any.
        """
        merged_details = {"repository": str(repository), **(details or {})}
        super().__init__(
            f"Repository not found: {repository}", details=merged_details, cause=cause
        )
        self.repository = repository
 
 
class InvalidRepositoryError(RepositoryError):
    """Raised when a repository exists but is structurally invalid.
 
    Examples include a directory that is not a Git repository when one
    is required, a repository missing an expected manifest, or a
    repository whose structure does not match any known layout.
    """
 
    def __init__(
        self,
        repository: Union[str, Path],
        reason: str,
        *,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        """Initializes an :class:`InvalidRepositoryError`.
 
        Args:
            repository: The repository identifier or filesystem path
                that was found to be invalid.
            reason: A human-readable explanation of why the repository
                is considered invalid.
            details: Additional structured context about the error.
            cause: The underlying exception that caused this error, if
                any.
        """
        merged_details = {"repository": str(repository), "reason": reason, **(details or {})}
        super().__init__(
            f"Invalid repository at {repository}: {reason}", details=merged_details, cause=cause
        )
        self.repository = repository
        self.reason = reason
 
 
class UnsupportedRepositoryError(RepositoryError):
    """Raised when a repository's type or layout is not supported by FlowPilot.
 
    This typically indicates that :class:`~flowpilot.core.models.RepositoryType`
    resolved to :attr:`~flowpilot.core.models.RepositoryType.UNKNOWN`, or that
    the repository targets a GNU Radio version FlowPilot does not yet
    understand.
    """
 
    def __init__(
        self,
        repository: Union[str, Path],
        *,
        repository_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        """Initializes an :class:`UnsupportedRepositoryError`.
 
        Args:
            repository: The repository identifier or filesystem path
                that is not supported.
            repository_type: The resolved repository type, if known.
            details: Additional structured context about the error.
            cause: The underlying exception that caused this error, if
                any.
        """
        merged_details = {
            "repository": str(repository),
            "repository_type": repository_type,
            **(details or {}),
        }
        suffix = f" (type={repository_type})" if repository_type else ""
        super().__init__(
            f"Unsupported repository: {repository}{suffix}", details=merged_details, cause=cause
        )
        self.repository = repository
        self.repository_type = repository_type
 
 
# =====================================================================
# SCANNER ERRORS
# =====================================================================
 
 
class ScannerError(FlowPilotError):
    """Base class for errors raised by the Repository Scanner subsystem."""
 
 
class ScanFailedError(ScannerError):
    """Raised when a repository scan terminates due to an unrecoverable error."""
 
    def __init__(
        self,
        repository: Union[str, Path],
        reason: str,
        *,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        """Initializes a :class:`ScanFailedError`.
 
        Args:
            repository: The repository identifier or filesystem path
                being scanned when the failure occurred.
            reason: A human-readable explanation of why the scan failed.
            details: Additional structured context about the error.
            cause: The underlying exception that caused this error, if
                any.
        """
        merged_details = {"repository": str(repository), "reason": reason, **(details or {})}
        super().__init__(
            f"Scan failed for {repository}: {reason}", details=merged_details, cause=cause
        )
        self.repository = repository
        self.reason = reason
 
 
class InventoryBuildError(ScannerError):
    """Raised when a :class:`~flowpilot.core.models.RepositoryInventory` or
    :class:`~flowpilot.core.models.InventoryReport` cannot be assembled.
 
    This typically indicates that per-file or per-module metadata was
    collected successfully but could not be aggregated into a coherent
    inventory, e.g. due to inconsistent or conflicting statistics.
    """
 
    def __init__(
        self,
        reason: str,
        *,
        repository: Optional[Union[str, Path]] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        """Initializes an :class:`InventoryBuildError`.
 
        Args:
            reason: A human-readable explanation of why inventory
                construction failed.
            repository: The repository identifier or filesystem path
                the inventory was being built for, if applicable.
            details: Additional structured context about the error.
            cause: The underlying exception that caused this error, if
                any.
        """
        merged_details = {"repository": str(repository) if repository else None, **(details or {})}
        message = "Failed to build inventory: " + reason
        if repository is not None:
            message = f"Failed to build inventory for {repository}: {reason}"
        super().__init__(message, details=merged_details, cause=cause)
        self.repository = repository
        self.reason = reason
 
 
# =====================================================================
# PARSER ERRORS
# =====================================================================
 
 
class ParserError(FlowPilotError):
    """Base class for errors raised by any FlowPilot source-file parser."""
 
    def __init__(
        self,
        message: str,
        *,
        path: Optional[Union[str, Path]] = None,
        line: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        """Initializes a :class:`ParserError`.
 
        Args:
            message: A human-readable description of the parsing error.
            path: The path to the file being parsed when the error
                occurred, if known.
            line: The line number within the file at which the error
                occurred, if known.
            details: Additional structured context about the error.
            cause: The underlying exception that caused this error, if
                any.
        """
        merged_details = {
            "path": str(path) if path is not None else None,
            "line": line,
            **(details or {}),
        }
        location = ""
        if path is not None:
            location = f" ({path}:{line})" if line is not None else f" ({path})"
        super().__init__(f"{message}{location}", details=merged_details, cause=cause)
        self.path = path
        self.line = line
 
 
class YAMLParserError(ParserError):
    """Raised when a ``*.block.yml`` or ``*.tree.yml`` file cannot be parsed."""
 
 
class GRCParserError(ParserError):
    """Raised when a GNU Radio Companion ``*.grc`` flowgraph cannot be parsed."""
 
 
class PythonParserError(ParserError):
    """Raised when a Python source file cannot be parsed or introspected."""
 
 
class CPPParserError(ParserError):
    """Raised when a C++ source or header file cannot be parsed."""
 
 
class DocumentationParserError(ParserError):
    """Raised when a documentation file (Markdown, reStructuredText, etc.) cannot be parsed."""
 
 
# =====================================================================
# KNOWLEDGE SUBSYSTEM ERRORS
# =====================================================================
 
 
class KnowledgeError(FlowPilotError):
    """Base class for errors raised by FlowPilot's knowledge subsystems.
 
    This includes the Knowledge Warehouse, the Neo4j Knowledge Graph, and
    the Embedding Engine.
    """
 
 
class WarehouseError(KnowledgeError):
    """Raised when the Knowledge Warehouse fails to read, write, or query records."""
 
 
class GraphError(KnowledgeError):
    """Raised when an operation against the Neo4j Knowledge Graph fails.
 
    This includes connection failures, malformed Cypher queries, and
    constraint violations encountered while writing nodes or
    relationships.
    """
 
 
class EmbeddingError(KnowledgeError):
    """Raised when the Embedding Engine fails to generate or retrieve embeddings."""
 
 
# =====================================================================
# VALIDATION / CONFIGURATION / METADATA ERRORS
# =====================================================================
 
 
class ValidationError(FlowPilotError):
    """Raised when a value, payload, or generated artifact fails validation.
 
    Used by the Validator subsystem when a generated GNU Radio project,
    flowgraph, or block definition does not satisfy FlowPilot's
    correctness rules, as well as by other subsystems performing input
    validation.
    """
 
    def __init__(
        self,
        message: str,
        *,
        field_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        """Initializes a :class:`ValidationError`.
 
        Args:
            message: A human-readable description of the validation
                failure.
            field_name: The name of the field, attribute, or parameter
                that failed validation, if applicable.
            details: Additional structured context about the error.
            cause: The underlying exception that caused this error, if
                any.
        """
        merged_details = {"field_name": field_name, **(details or {})}
        suffix = f" (field={field_name})" if field_name else ""
        super().__init__(f"{message}{suffix}", details=merged_details, cause=cause)
        self.field_name = field_name
 
 
class ConfigurationError(FlowPilotError):
    """Raised when FlowPilot's configuration is missing, malformed, or invalid."""
 
    def __init__(
        self,
        message: str,
        *,
        key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        """Initializes a :class:`ConfigurationError`.
 
        Args:
            message: A human-readable description of the configuration
                error.
            key: The configuration key or setting name that is missing
                or invalid, if applicable.
            details: Additional structured context about the error.
            cause: The underlying exception that caused this error, if
                any.
        """
        merged_details = {"key": key, **(details or {})}
        suffix = f" (key={key})" if key else ""
        super().__init__(f"{message}{suffix}", details=merged_details, cause=cause)
        self.key = key
 
 
class MetadataError(FlowPilotError):
    """Raised when repository, module, or file metadata is missing, inconsistent, or malformed.
 
    This typically indicates that a value could not be coerced into one
    of the FlowPilot data models (e.g. an invalid ``RepositoryType`` or
    ``FileType`` value).
    """
 
 
# =====================================================================
# ACQUISITION ERRORS
# =====================================================================
 
 
class AcquisitionError(FlowPilotError):
    """Base class for errors raised by the Autonomous Knowledge Acquisition System."""
 
 
class DownloadError(AcquisitionError):
    """Raised when fetching a knowledge source (Git, website, PDF, or API) fails."""
 
    def __init__(
        self,
        uri: str,
        reason: str,
        *,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        """Initializes a :class:`DownloadError`.
 
        Args:
            uri: The URI, URL, or path of the knowledge source that
                failed to download.
            reason: A human-readable explanation of why the download
                failed.
            status_code: The HTTP status code returned by the remote
                server, if applicable.
            details: Additional structured context about the error.
            cause: The underlying exception that caused this error, if
                any.
        """
        merged_details = {"uri": uri, "status_code": status_code, **(details or {})}
        suffix = f" (status={status_code})" if status_code is not None else ""
        super().__init__(
            f"Failed to download {uri}: {reason}{suffix}", details=merged_details, cause=cause
        )
        self.uri = uri
        self.reason = reason
        self.status_code = status_code
 
 
class SynchronizationError(AcquisitionError):
    """Raised when a knowledge source cannot be kept in sync with its origin.
 
    This covers failures to pull the latest commits of a Git-backed
    knowledge source, refresh a crawled website, or reconcile local
    state with a remote API.
    """
 
    def __init__(
        self,
        uri: str,
        reason: str,
        *,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        """Initializes a :class:`SynchronizationError`.
 
        Args:
            uri: The URI, URL, or path of the knowledge source that
                failed to synchronize.
            reason: A human-readable explanation of why synchronization
                failed.
            details: Additional structured context about the error.
            cause: The underlying exception that caused this error, if
                any.
        """
        merged_details = {"uri": uri, "reason": reason, **(details or {})}
        super().__init__(
            f"Failed to synchronize {uri}: {reason}", details=merged_details, cause=cause
        )
        self.uri = uri
        self.reason = reason
 
 
# =====================================================================
# STORAGE / SERIALIZATION ERRORS
# =====================================================================
 
 
class StorageError(FlowPilotError):
    """Base class for errors raised while persisting or retrieving data."""
 
    def __init__(
        self,
        message: str,
        *,
        path: Optional[Union[str, Path]] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        """Initializes a :class:`StorageError`.
 
        Args:
            message: A human-readable description of the storage error.
            path: The path or storage key involved in the failure, if
                applicable.
            details: Additional structured context about the error.
            cause: The underlying exception that caused this error, if
                any.
        """
        merged_details = {"path": str(path) if path is not None else None, **(details or {})}
        suffix = f" ({path})" if path is not None else ""
        super().__init__(f"{message}{suffix}", details=merged_details, cause=cause)
        self.path = path
 
 
class SerializationError(StorageError):
    """Raised when a FlowPilot model or value cannot be serialized (e.g. to JSON)."""
 
 
class DeserializationError(StorageError):
    """Raised when serialized data cannot be deserialized back into a FlowPilot model or value."""