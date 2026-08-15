"""Structured data models for parsed GNU Radio Companion block knowledge.
 
This module defines the dataclasses produced by
:class:`~flowpilot.knowledge.parser.block_yaml_parser.BlockYamlParser`
when it converts a GNU Radio Companion ``*.block.yml`` file into
structured, machine-readable knowledge for the Autonomous Knowledge
Acquisition System (AKAS).
 
These models deliberately live outside ``flowpilot/core/models.py``: the
core models module is a fixed, shared contract used by every FlowPilot
subsystem, while :class:`BlockDefinition` and its nested types are
specific to the block-knowledge extraction layer. They subclass
:class:`~flowpilot.core.models.BaseModel` to reuse its serialization
contract (``to_dict``, ``to_json_dict``, ``to_json``) rather than
reimplementing it.
"""
 
from __future__ import annotations
 
from dataclasses import dataclass, field, fields
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
 
from flowpilot.core.models import BaseModel
 
__all__ = [
    "ParseStatus",
    "BlockParameter",
    "BlockPort",
    "BlockDefinition",
]
 
 
def _parse_path(value: Union[str, Path, None]) -> Optional[Path]:
    """Parses a value into a :class:`~pathlib.Path` instance.
 
    A local equivalent of the private helper used internally by
    :mod:`flowpilot.core.models`, kept here rather than imported so
    that this module does not depend on that module's private API.
 
    Args:
        value: A path string, an existing ``Path``, or ``None``.
 
    Returns:
        A ``Path`` instance, or ``None`` if ``value`` is ``None``.
    """
    if value is None or isinstance(value, Path):
        return value
    return Path(value)
 
 
class ParseStatus(str, Enum):
    """Outcome of parsing a single block YAML file.
 
    Attributes:
        SUCCESS: The file was parsed with no issues; a block identity
            (``id``) was found and no structural problems were
            encountered.
        PARTIAL: A block identity was found, but one or more
            non-fatal structural issues were encountered (e.g. an
            ``inputs`` entry that was not a mapping). The block is
            still usable, but ``parse_errors`` should be reviewed.
        FAILED: No usable block could be extracted (e.g. the file was
            empty, was not valid YAML, or had no ``id`` field).
    """
 
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
 
 
@dataclass(slots=True)
class BlockParameter(BaseModel):
    """A single parameter declared by a GNU Radio Companion block.
 
    Attributes:
        id: The parameter's programmatic identifier (e.g. ``"rate"``).
        label: The parameter's human-readable label (e.g. ``"Rate"``).
        dtype: The parameter's declared data type (e.g. ``"real"``,
            ``"enum"``). May contain a GRC template expression.
        default: The parameter's default value, in whatever form the
            YAML declared it (string, number, boolean, or ``None``).
        options: The parameter's selectable options, for enum-like
            parameters. Empty if the parameter is not an enum.
        extra: Any additional fields present on this parameter in the
            source YAML that are not otherwise modeled (e.g.
            ``option_labels``, ``option_attributes``, ``hide``),
            preserved verbatim.
    """
 
    id: Optional[str] = None
    label: Optional[str] = None
    dtype: Optional[str] = None
    default: Any = None
    options: List[Any] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
 
 
@dataclass(slots=True)
class BlockPort(BaseModel):
    """A single input or output port declared by a GNU Radio Companion block.
 
    Attributes:
        label: The port's human-readable label, if declared.
        domain: The port's GNU Radio domain (e.g. ``"stream"``,
            ``"message"``).
        dtype: The port's declared data type. May contain a GRC
            template expression (e.g. ``"${ type }"``). Typically
            absent for message-domain ports.
        vlen: The port's declared vector length, in whatever form the
            YAML provided it (integer or template expression string).
        multiplicity: The port's declared multiplicity expression, for
            ports whose count is parameterized (e.g. ``"${ num_inputs
            }"``).
        optional: Whether the port is declared optional.
        extra: Any additional fields present on this port in the
            source YAML that are not otherwise modeled (e.g. a
            message-domain port's ``id``), preserved verbatim.
    """
 
    label: Optional[str] = None
    domain: Optional[str] = None
    dtype: Optional[str] = None
    vlen: Any = None
    multiplicity: Optional[str] = None
    optional: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)
 
 
@dataclass(slots=True)
class BlockDefinition(BaseModel):
    """Structured knowledge extracted from one GNU Radio Companion block.
 
    Attributes:
        block_id: The block's programmatic identifier (the YAML ``id``
            field), e.g. ``"analog_agc_xx"``. ``None`` if the source
            file had no ``id`` field.
        name: The block's canonical name. Falls back to ``label`` and
            then ``block_id`` when a dedicated ``name`` field is
            absent, since most GNU Radio block YAML schemas do not
            declare one separately.
        label: The block's human-readable GRC label (e.g. ``"AGC"``).
        category: The block's GRC category path, normalized to a
            single ``/``-joined string regardless of whether the
            source YAML declared it as a string or a list.
        description: A short description of the block, if the source
            YAML declares one under ``description`` or ``desc``.
        documentation: The block's full documentation text, if the
            source YAML declares a ``documentation`` field.
        parameters: The block's declared parameters.
        inputs: The block's declared input ports.
        outputs: The block's declared output ports.
        data_types: The distinct, non-empty ``dtype`` values collected
            across every parameter and port, deduplicated and sorted.
            Convenience field for downstream indexing and search.
        domain: The distinct, non-empty ``domain`` values collected
            across every input and output port, deduplicated and
            sorted (e.g. ``["message", "stream"]``).
        implementation: The block's declared implementation languages
            or backends, taken from the YAML ``flags`` field (e.g.
            ``["python", "cpp"]``). Empty if not declared.
        source_file: The absolute path to the source ``*.block.yml``
            file this definition was parsed from.
        repository: The name of the repository the source file belongs
            to, if known.
        module: The name of the module the source file belongs to, if
            known.
        version: The version of the repository the source file was
            scanned at, if known.
        raw_metadata: The complete, unmodified YAML document as parsed,
            guaranteeing that no field — modeled or not — is ever
            silently discarded.
        parse_status: The overall outcome of parsing this file. See
            :class:`ParseStatus`.
        parse_errors: Human-readable descriptions of any structural
            issues encountered while parsing, in the order they were
            found. Empty when ``parse_status`` is
            :attr:`ParseStatus.SUCCESS`.
    """
 
    block_id: Optional[str] = None
    name: Optional[str] = None
    label: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    documentation: Optional[str] = None
    parameters: List[BlockParameter] = field(default_factory=list)
    inputs: List[BlockPort] = field(default_factory=list)
    outputs: List[BlockPort] = field(default_factory=list)
    data_types: List[str] = field(default_factory=list)
    domain: List[str] = field(default_factory=list)
    implementation: List[str] = field(default_factory=list)
    source_file: Optional[Path] = None
    repository: Optional[str] = None
    module: Optional[str] = None
    version: Optional[str] = None
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    parse_status: ParseStatus = ParseStatus.FAILED
    parse_errors: List[str] = field(default_factory=list)
 
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BlockDefinition":
        """Builds a :class:`BlockDefinition` instance from a dictionary.
 
        Args:
            data: A dictionary produced by
                :meth:`~flowpilot.core.models.BaseModel.to_dict` or an
                equivalent structure.
 
        Returns:
            A new :class:`BlockDefinition` instance.
        """
        payload = dict(data)
        payload["source_file"] = _parse_path(payload.get("source_file"))
 
        raw_parameters = payload.get("parameters") or []
        payload["parameters"] = [
            parameter
            if isinstance(parameter, BlockParameter)
            else BlockParameter.from_dict(parameter)
            for parameter in raw_parameters
        ]
 
        for port_field in ("inputs", "outputs"):
            raw_ports = payload.get(port_field) or []
            payload[port_field] = [
                port if isinstance(port, BlockPort) else BlockPort.from_dict(port)
                for port in raw_ports
            ]
 
        raw_status = payload.get("parse_status", ParseStatus.FAILED)
        payload["parse_status"] = (
            raw_status if isinstance(raw_status, ParseStatus) else ParseStatus(raw_status)
        )
 
        valid_field_names = {f.name for f in fields(cls)}
        filtered = {key: value for key, value in payload.items() if key in valid_field_names}
        return cls(**filtered)