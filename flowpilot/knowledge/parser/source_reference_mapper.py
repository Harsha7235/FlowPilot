"""
GNU Radio Source Reference Mapper.

Maps parsed BlockDefinition objects to likely source files in a GNU Radio
module using evidence from:

- block identifiers
- GRC templates
- C++ templates
- GNU Radio naming conventions
- module directory structure

The mapper does NOT parse C++/Python source code.

It only identifies and scores source-file references.

Confidence levels:

HIGH
    Strong evidence from YAML templates or exact filename/stem matches.

MEDIUM
    Reasonable GNU Radio naming-convention match.

LOW
    Weak substring overlap only.

LOW-confidence matches are stored in possible_references and are never
treated as confirmed source references.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field, fields
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Set, Union

from flowpilot.core.models import BaseModel, ModelEncoder
from flowpilot.core.utils import (
    configure_logger,
    load_json,
    normalize_path,
    safe_mkdir,
    save_json,
)
from flowpilot.knowledge.parser.block_models import BlockDefinition


__all__ = [
    "MatchConfidence",
    "SourceFileMatch",
    "SourceReference",
    "SourceReferenceMapper",
]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_STORAGE_DIR = (
    Path(__file__).resolve().parent.parent / "blocks"
)

_SOURCE_SUFFIXES = frozenset({
    ".cc",
    ".cpp",
})

_HEADER_SUFFIXES = frozenset({
    ".h",
    ".hpp",
})

_DOC_SUFFIXES = frozenset({
    ".rst",
    ".md",
    ".txt",
})

_TEST_MARKER_PREFIXES = (
    "qa_",
    "test_",
)

_TEST_MARKER_SUBSTRINGS = (
    "_test",
)

_TEST_DIRECTORY_NAMES = frozenset({
    "test",
    "tests",
    "qa",
})

# GNU Radio type-code characters.
# c = complex
# f = float
# i = int
# s = short
# b = byte
_TYPE_CODE_CHARS = frozenset("cfisb")

_PLACEHOLDER_SUFFIXES = (
    "_xx",
    "_x",
)

_MIN_LOW_CONFIDENCE_STEM_LENGTH = 3
_MIN_DOC_STEM_LENGTH = 4

_SAFE_FILENAME_CHARACTERS = frozenset(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789-_ ."
)

# Remove the accidental space from the safe-character set.
_SAFE_FILENAME_CHARACTERS = frozenset(
    char for char in _SAFE_FILENAME_CHARACTERS if char != " "
)


# ---------------------------------------------------------------------------
# Template regexes
# ---------------------------------------------------------------------------

_TEMPLATE_PLACEHOLDER_RE = re.compile(
    r"\$\{[^}]*\}"
)

_TEMPLATE_INCLUDE_RE = re.compile(
    r"#include\s*<gnuradio/\w+/([\w${}.]+)\.h>"
)

_TEMPLATE_CPP_CALL_RE = re.compile(
    r"\b([\w${}.]+)::(?:make|sptr)\b"
)

_TEMPLATE_PY_CALL_RE = re.compile(
    r"\b\w+\.([\w${}.]+)\s*\("
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_path(
    value: Union[str, Path, None]
) -> Optional[Path]:
    """
    Convert a path-like value into Path.
    """
    if value is None:
        return None

    if isinstance(value, Path):
        return value

    return Path(value)


def _derive_namespace(
    module: Optional[str],
) -> Optional[str]:
    """
    Derive GNU Radio namespace from module name.

    Example:

        gr-analog -> analog
        gr-digital -> digital

    Non-gr-* module names are returned unchanged.
    """
    if not module:
        return None

    if module.startswith("gr-") and len(module) > 3:
        return module[3:]

    return module


def _strip_placeholder_suffix(
    stem: str,
) -> str:
    """
    Strip GRC multi-type placeholder suffix.

    Example:

        analog_agc_xx -> analog_agc
        agc_xx -> agc
    """
    for suffix in _PLACEHOLDER_SUFFIXES:
        if stem.endswith(suffix) and len(stem) > len(suffix):
            return stem[:-len(suffix)]

    return stem


def _strip_type_suffix(
    stem: str,
) -> str:
    """
    Strip a GNU Radio type suffix.

    Examples:

        agc_cc -> agc
        agc_ff -> agc
        multiply_const_cc -> multiply_const
    """
    if "_" not in stem:
        return stem

    prefix, _, suffix = stem.rpartition("_")

    if (
        prefix
        and suffix
        and 1 <= len(suffix) <= 3
        and all(ch in _TYPE_CODE_CHARS for ch in suffix)
    ):
        return prefix

    return stem


def _derive_block_stem_candidates(
    block_id: str,
    namespace: Optional[str],
) -> Set[str]:
    """
    Derive possible implementation filename stems.

    Example:

        block_id = analog_agc_xx
        namespace = analog

    produces candidates approximately:

        analog_agc_xx
        agc_xx
        agc
    """
    candidates: Set[str] = {
        block_id
    }

    stem = block_id

    if namespace and stem.startswith(
        f"{namespace}_"
    ):
        stem = stem[
            len(namespace) + 1:
        ]

        candidates.add(stem)

    placeholder_stripped = _strip_placeholder_suffix(
        stem
    )

    candidates.add(
        placeholder_stripped
    )

    candidates.add(
        _strip_type_suffix(
            placeholder_stripped
        )
    )

    return {
        candidate
        for candidate in candidates
        if candidate
    }


def _stem_pattern_from_template(
    raw_stem: str,
) -> Optional[Pattern[str]]:
    """
    Convert a GRC template stem into a regex.

    Example:

        agc_${type.fcn}

    becomes approximately:

        ^agc_[A-Za-z0-9]+$

    This allows:

        agc_cc
        agc_ff

    but does not match:

        agc2_cc
        agc3_cc
        feedforward_agc_cc
    """
    if not raw_stem:
        return None

    segments = _TEMPLATE_PLACEHOLDER_RE.split(
        raw_stem
    )

    if not any(
        segment.strip()
        for segment in segments
    ):
        return None

    escaped_segments = [
        re.escape(segment)
        for segment in segments
    ]

    pattern_str = (
        "[A-Za-z0-9]+"
        .join(escaped_segments)
    )

    try:
        return re.compile(
            f"^{pattern_str}$"
        )
    except re.error:
        return None


def _collect_template_texts(
    raw_metadata: Dict[str, Any],
) -> List[str]:
    """
    Collect template strings from block YAML metadata.

    Looks under:

        templates
        cpp_templates
    """
    texts: List[str] = []

    for key in (
        "templates",
        "cpp_templates",
    ):
        section = raw_metadata.get(key)

        if not isinstance(section, dict):
            continue

        for value in section.values():

            if isinstance(value, str):
                texts.append(value)

            elif isinstance(value, list):
                texts.extend(
                    item
                    for item in value
                    if isinstance(item, str)
                )

    return texts


def _extract_template_patterns(
    raw_metadata: Dict[str, Any],
) -> List[Pattern[str]]:
    """
    Extract filename patterns from YAML templates.

    Patterns can originate from:

    - #include <gnuradio/...>
    - namespace::make(...)
    - namespace::sptr
    - Python block calls
    """
    patterns: List[Pattern[str]] = []

    for text in _collect_template_texts(
        raw_metadata
    ):
        captured = (
            *_TEMPLATE_INCLUDE_RE.findall(text),
            *_TEMPLATE_CPP_CALL_RE.findall(text),
            *_TEMPLATE_PY_CALL_RE.findall(text),
        )

        for raw_stem in captured:
            pattern = _stem_pattern_from_template(
                raw_stem
            )

            if pattern is not None:
                patterns.append(pattern)

    # Remove duplicate regex patterns.
    unique_patterns: Dict[str, Pattern[str]] = {}

    for pattern in patterns:
        unique_patterns[pattern.pattern] = pattern

    return list(unique_patterns.values())


def _normalize_impl_stem(
    stem: str,
) -> str:
    """
    Remove _impl from implementation filename.

    Example:

        agc_ff_impl -> agc_ff
    """
    if stem.endswith("_impl"):
        return stem[:-len("_impl")]

    return stem


def _normalize_binding_stem(
    stem: str,
) -> str:
    """
    Remove _python from binding filename.

    Example:

        agc_ff_python -> agc_ff
    """
    if stem.endswith("_python"):
        return stem[:-len("_python")]

    return stem


def _normalize_qa_stem(
    stem: str,
) -> str:
    """
    Remove qa_ prefix from QA filename.

    Example:

        qa_agc -> agc
    """
    if stem.startswith("qa_"):
        return stem[len("qa_"):]

    return stem


def _classify_match(
    normalized_stem: str,
    block_stem_candidates: Set[str],
    template_patterns: List[Pattern[str]],
) -> Optional[tuple]:
    """
    Classify a filename against block evidence.

    Returns:

        (MatchConfidence, evidence)

    or:

        None
    """

    # ---------------------------------------------------------------
    # HIGH: YAML template pattern
    # ---------------------------------------------------------------

    for pattern in template_patterns:

        if pattern.match(normalized_stem):

            return (
                MatchConfidence.HIGH,
                (
                    "matches YAML template pattern "
                    f"'{pattern.pattern}'"
                ),
            )

    # ---------------------------------------------------------------
    # HIGH: exact stem
    # ---------------------------------------------------------------

    if normalized_stem in block_stem_candidates:

        return (
            MatchConfidence.HIGH,
            (
                "exact stem match with block "
                f"identifier ('{normalized_stem}')"
            ),
        )

    # ---------------------------------------------------------------
    # MEDIUM: type suffix normalization
    # ---------------------------------------------------------------

    type_stripped_stem = _strip_type_suffix(
        normalized_stem
    )

    if (
        type_stripped_stem
        in block_stem_candidates
        and type_stripped_stem
        != normalized_stem
    ):

        return (
            MatchConfidence.MEDIUM,
            (
                "naming-convention match after "
                "stripping type suffix "
                f"('{normalized_stem}' -> "
                f"'{type_stripped_stem}')"
            ),
        )

    # ---------------------------------------------------------------
    # LOW: substring overlap
    # ---------------------------------------------------------------

    for candidate in block_stem_candidates:

        if (
            len(candidate)
            < _MIN_LOW_CONFIDENCE_STEM_LENGTH
        ):
            continue

        if (
            candidate in normalized_stem
            or normalized_stem in candidate
        ):

            return (
                MatchConfidence.LOW,
                (
                    "filename substring overlap "
                    "with block stem candidate "
                    f"'{candidate}'"
                ),
            )

    return None


def _sanitize_filename_part(
    part: str,
) -> str:
    """
    Make a repository/module/block identifier safe
    for a filename.
    """
    return "".join(
        char
        if char in _SAFE_FILENAME_CHARACTERS
        else "_"
        for char in part
    )


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class MatchConfidence(str, Enum):
    """
    Confidence assigned to a source-file match.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(slots=True)
class SourceFileMatch(BaseModel):
    """
    A single source-file candidate.
    """

    path: Optional[Path] = None

    category: str = ""

    confidence: MatchConfidence = (
        MatchConfidence.LOW
    )

    evidence: str = ""

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "SourceFileMatch":

        payload = dict(data)

        payload["path"] = _parse_path(
            payload.get("path")
        )

        raw_confidence = payload.get(
            "confidence",
            MatchConfidence.LOW,
        )

        payload["confidence"] = (
            raw_confidence
            if isinstance(
                raw_confidence,
                MatchConfidence,
            )
            else MatchConfidence(
                raw_confidence
            )
        )

        valid_field_names = {
            f.name
            for f in fields(cls)
        }

        filtered = {
            key: value
            for key, value in payload.items()
            if key in valid_field_names
        }

        return cls(**filtered)


@dataclass(slots=True)
class SourceReference(BaseModel):
    """
    Complete source-reference record for one block.

    Only HIGH and MEDIUM matches are stored in the
    confirmed category lists.

    LOW-confidence matches are stored in
    possible_references.
    """

    block_id: Optional[str] = None

    repository: Optional[str] = None

    module: Optional[str] = None

    block_definition_file: Optional[Path] = None

    module_root: Optional[Path] = None

    implementation_files: List[
        SourceFileMatch
    ] = field(default_factory=list)

    header_files: List[
        SourceFileMatch
    ] = field(default_factory=list)

    binding_files: List[
        SourceFileMatch
    ] = field(default_factory=list)

    test_files: List[
        SourceFileMatch
    ] = field(default_factory=list)

    documentation_files: List[
        SourceFileMatch
    ] = field(default_factory=list)

    possible_references: List[
        SourceFileMatch
    ] = field(default_factory=list)

    matched_file_count: int = 0

    high_confidence_count: int = 0

    medium_confidence_count: int = 0

    low_confidence_count: int = 0

    unmatched_reason: Optional[str] = None

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "SourceReference":

        payload = dict(data)

        payload["block_definition_file"] = (
            _parse_path(
                payload.get(
                    "block_definition_file"
                )
            )
        )

        payload["module_root"] = _parse_path(
            payload.get("module_root")
        )

        list_fields = (
            "implementation_files",
            "header_files",
            "binding_files",
            "test_files",
            "documentation_files",
            "possible_references",
        )

        for list_field in list_fields:

            raw_matches = (
                payload.get(list_field)
                or []
            )

            payload[list_field] = [
                (
                    match
                    if isinstance(
                        match,
                        SourceFileMatch,
                    )
                    else SourceFileMatch.from_dict(
                        match
                    )
                )
                for match in raw_matches
            ]

        valid_field_names = {
            f.name
            for f in fields(cls)
        }

        filtered = {
            key: value
            for key, value in payload.items()
            if key in valid_field_names
        }

        return cls(**filtered)


# ---------------------------------------------------------------------------
# Mapper
# ---------------------------------------------------------------------------

class SourceReferenceMapper:
    """
    Maps BlockDefinition objects to source files.

    This class does not parse YAML itself.

    It consumes already-parsed BlockDefinition objects and creates
    SourceReference records.
    """

    def __init__(
        self,
        *,
        logger: Optional[logging.Logger] = None,
    ) -> None:

        self._logger = (
            logger
            or configure_logger(__name__)
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def map_block(
        self,
        block: BlockDefinition,
    ) -> SourceReference:
        """
        Map one BlockDefinition to source references.
        """

        reference = SourceReference(
            block_id=block.block_id,
            repository=block.repository,
            module=block.module,
            block_definition_file=block.source_file,
        )

        # --------------------------------------------------------------
        # Validate required information
        # --------------------------------------------------------------

        if (
            not block.block_id
            or not block.module
            or block.source_file is None
        ):

            reference.unmatched_reason = (
                "block is missing block_id, module, "
                "or source_file; cannot resolve references"
            )

            return reference

        # --------------------------------------------------------------
        # Resolve module root
        # --------------------------------------------------------------

        module_root = self._resolve_module_root(
            block.source_file,
            block.module,
        )

        if module_root is None:

            reference.unmatched_reason = (
                f"could not locate a directory named "
                f"'{block.module}' among the ancestors "
                f"of {block.source_file}"
            )

            return reference

        reference.module_root = module_root

        # --------------------------------------------------------------
        # Derive namespace
        # --------------------------------------------------------------

        namespace = _derive_namespace(
            block.module
        )

        # --------------------------------------------------------------
        # Derive filename stems
        # --------------------------------------------------------------

        block_stem_candidates = (
            _derive_block_stem_candidates(
                block.block_id,
                namespace,
            )
        )

        # --------------------------------------------------------------
        # Extract patterns from YAML metadata
        # --------------------------------------------------------------

        raw_metadata = (
            block.raw_metadata
            if isinstance(
                block.raw_metadata,
                dict,
            )
            else {}
        )

        template_patterns = (
            _extract_template_patterns(
                raw_metadata
            )
        )

        # --------------------------------------------------------------
        # Search implementation/header files
        # --------------------------------------------------------------

        self._collect_lib_files(
            module_root,
            block_stem_candidates,
            template_patterns,
            reference,
        )

        # --------------------------------------------------------------
        # Search public headers
        # --------------------------------------------------------------

        self._collect_include_files(
            module_root,
            namespace,
            block_stem_candidates,
            template_patterns,
            reference,
        )

        # --------------------------------------------------------------
        # Search Python/bindings/tests
        # --------------------------------------------------------------

        self._collect_python_files(
            module_root,
            namespace,
            block_stem_candidates,
            template_patterns,
            reference,
        )

        # --------------------------------------------------------------
        # Search documentation
        # --------------------------------------------------------------

        self._collect_documentation_files(
            module_root,
            block_stem_candidates,
            reference,
        )

        # --------------------------------------------------------------
        # Calculate statistics
        # --------------------------------------------------------------

        reference.matched_file_count = (
            len(reference.implementation_files)
            + len(reference.header_files)
            + len(reference.binding_files)
            + len(reference.test_files)
            + len(reference.documentation_files)
        )

        reference.high_confidence_count = (
            self._count_at_confidence(
                reference,
                MatchConfidence.HIGH,
            )
        )

        reference.medium_confidence_count = (
            self._count_at_confidence(
                reference,
                MatchConfidence.MEDIUM,
            )
        )

        reference.low_confidence_count = (
            len(reference.possible_references)
        )

        # --------------------------------------------------------------
        # Explain unmatched blocks
        # --------------------------------------------------------------

        if reference.matched_file_count == 0:

            if reference.possible_references:

                reference.unmatched_reason = (
                    "no high- or medium-confidence "
                    "reference found; "
                    f"{len(reference.possible_references)} "
                    "weak substring-only candidate(s) "
                    "recorded in possible_references "
                    "for manual review"
                )

            else:

                reference.unmatched_reason = (
                    "module root was located, but no "
                    "implementation, header, binding, "
                    "test, or documentation file matched "
                    "this block's identifier or YAML "
                    "template patterns"
                )

        return reference

    def map_blocks(
        self,
        blocks: List[BlockDefinition],
    ) -> List[SourceReference]:
        """
        Map a list of BlockDefinitions.

        One failed block must not prevent other blocks
        from being processed.
        """

        references: List[SourceReference] = []

        for block in blocks:

            try:

                references.append(
                    self.map_block(block)
                )

            except Exception as exc:

                self._logger.exception(
                    "Failed to map block '%s'",
                    getattr(
                        block,
                        "block_id",
                        "<unknown>",
                    ),
                )

                reference = SourceReference(
                    block_id=getattr(
                        block,
                        "block_id",
                        None,
                    ),
                    repository=getattr(
                        block,
                        "repository",
                        None,
                    ),
                    module=getattr(
                        block,
                        "module",
                        None,
                    ),
                    block_definition_file=getattr(
                        block,
                        "source_file",
                        None,
                    ),
                    unmatched_reason=(
                        "source-reference mapping failed: "
                        f"{exc}"
                    ),
                )

                references.append(reference)

        return references

    # ------------------------------------------------------------------
    # Storage API
    # ------------------------------------------------------------------

    def save(
        self,
        reference: SourceReference,
        storage_dir: Union[str, Path] = (
            _DEFAULT_STORAGE_DIR
        ),
    ) -> Path:
        """
        Save one SourceReference as JSON.
        """

        resolved_dir = safe_mkdir(
            storage_dir
        )

        output_path = (
            resolved_dir
            / self._build_filename(
                reference
            )
        )

        save_json(
            output_path,
            reference.to_dict(),
            encoder=ModelEncoder,
        )

        return output_path

    def save_many(
        self,
        references: List[SourceReference],
        storage_dir: Union[str, Path] = (
            _DEFAULT_STORAGE_DIR
        ),
    ) -> List[Path]:
        """
        Save multiple SourceReference records.
        """

        resolved_dir = safe_mkdir(
            storage_dir
        )

        written_paths = [
            self.save(
                reference,
                resolved_dir,
            )
            for reference in references
        ]

        self._logger.info(
            "Stored %d source reference record(s) in %s",
            len(written_paths),
            resolved_dir,
        )

        return written_paths

    def load(
        self,
        repository: str,
        module: str,
        block_id: str,
        storage_dir: Union[str, Path] = (
            _DEFAULT_STORAGE_DIR
        ),
    ) -> Optional[SourceReference]:
        """
        Load one SourceReference record.
        """

        resolved_dir = normalize_path(
            storage_dir
        )

        path = (
            resolved_dir
            / self._build_filename_from_parts(
                repository,
                module,
                block_id,
            )
        )

        if not path.exists():
            return None

        return SourceReference.from_dict(
            load_json(path)
        )

    # ------------------------------------------------------------------
    # Module resolution
    # ------------------------------------------------------------------

    def _resolve_module_root(
        self,
        source_file: Path,
        module: str,
    ) -> Optional[Path]:
        """
        Locate the module root by walking up from
        the block YAML file.
        """

        for ancestor in (
            source_file,
            *source_file.parents,
        ):

            if ancestor.name == module:
                return ancestor

        return None

    # ------------------------------------------------------------------
    # Match routing
    # ------------------------------------------------------------------

    @staticmethod
    def _route_match(
        reference: SourceReference,
        target_list: List[SourceFileMatch],
        match: SourceFileMatch,
    ) -> None:
        """
        Route LOW-confidence matches to possible_references.

        HIGH/MEDIUM matches remain confirmed references.
        """

        if (
            match.confidence
            == MatchConfidence.LOW
        ):

            reference.possible_references.append(
                match
            )

        else:

            target_list.append(
                match
            )

    # ------------------------------------------------------------------
    # Library files
    # ------------------------------------------------------------------

    def _collect_lib_files(
        self,
        module_root: Path,
        stems: Set[str],
        patterns: List[Pattern[str]],
        reference: SourceReference,
    ) -> None:
        """
        Search module/lib for C++ implementations,
        headers and tests.
        """

        lib_dir = (
            module_root / "lib"
        )

        if not lib_dir.is_dir():
            return

        for path in sorted(
            lib_dir.rglob("*")
        ):

            if not path.is_file():
                continue

            suffix = path.suffix.lower()

            if (
                suffix not in _SOURCE_SUFFIXES
                and suffix not in _HEADER_SUFFIXES
            ):
                continue

            is_test = self._looks_like_test(
                path
            )

            normalized_stem = (
                _normalize_impl_stem(
                    path.stem
                )
            )

            result = _classify_match(
                normalized_stem,
                stems,
                patterns,
            )

            if result is None:
                continue

            confidence, evidence = result

            if is_test:

                match = SourceFileMatch(
                    path=path,
                    category="test",
                    confidence=confidence,
                    evidence=evidence,
                )

                self._route_match(
                    reference,
                    reference.test_files,
                    match,
                )

            elif suffix in _SOURCE_SUFFIXES:

                match = SourceFileMatch(
                    path=path,
                    category="implementation",
                    confidence=confidence,
                    evidence=evidence,
                )

                self._route_match(
                    reference,
                    reference.implementation_files,
                    match,
                )

            else:

                match = SourceFileMatch(
                    path=path,
                    category="header_impl",
                    confidence=confidence,
                    evidence=evidence,
                )

                self._route_match(
                    reference,
                    reference.header_files,
                    match,
                )

    # ------------------------------------------------------------------
    # Public headers
    # ------------------------------------------------------------------

    def _collect_include_files(
        self,
        module_root: Path,
        namespace: Optional[str],
        stems: Set[str],
        patterns: List[Pattern[str]],
        reference: SourceReference,
    ) -> None:
        """
        Search include/gnuradio/<namespace> for public headers.
        """

        if not namespace:
            return

        include_dir = (
            module_root
            / "include"
            / "gnuradio"
            / namespace
        )

        if not include_dir.is_dir():
            return

        for path in sorted(
            include_dir.rglob("*")
        ):

            if (
                not path.is_file()
                or path.suffix.lower()
                not in _HEADER_SUFFIXES
            ):
                continue

            result = _classify_match(
                path.stem,
                stems,
                patterns,
            )

            if result is None:
                continue

            confidence, evidence = result

            match = SourceFileMatch(
                path=path,
                category="header_public",
                confidence=confidence,
                evidence=evidence,
            )

            self._route_match(
                reference,
                reference.header_files,
                match,
            )

    # ------------------------------------------------------------------
    # Python/bindings/tests
    # ------------------------------------------------------------------

    def _collect_python_files(
        self,
        module_root: Path,
        namespace: Optional[str],
        stems: Set[str],
        patterns: List[Pattern[str]],
        reference: SourceReference,
    ) -> None:
        """
        Search Python implementations, bindings and tests.
        """

        if not namespace:
            return

        python_dir = (
            module_root
            / "python"
            / namespace
        )

        if not python_dir.is_dir():
            return

        # --------------------------------------------------------------
        # Bindings
        # --------------------------------------------------------------

        bindings_dir = (
            python_dir / "bindings"
        )

        if bindings_dir.is_dir():

            for path in sorted(
                bindings_dir.rglob("*")
            ):

                if not path.is_file():
                    continue

                if (
                    path.suffix.lower()
                    not in _SOURCE_SUFFIXES
                    and path.suffix.lower()
                    != ".py"
                ):
                    continue

                normalized_stem = (
                    _normalize_binding_stem(
                        path.stem
                    )
                )

                result = _classify_match(
                    normalized_stem,
                    stems,
                    patterns,
                )

                if result is None:
                    continue

                confidence, evidence = result

                match = SourceFileMatch(
                    path=path,
                    category="binding",
                    confidence=confidence,
                    evidence=evidence,
                )

                self._route_match(
                    reference,
                    reference.binding_files,
                    match,
                )

        # --------------------------------------------------------------
        # Python files
        # --------------------------------------------------------------

        test_candidates: List[Path] = []

        for path in sorted(
            python_dir.glob("*.py")
        ):

            if (
                not path.is_file()
                or path.name == "__init__.py"
            ):
                continue

            if self._looks_like_test(path):

                test_candidates.append(path)
                continue

            result = _classify_match(
                path.stem,
                stems,
                patterns,
            )

            if result is None:
                continue

            confidence, evidence = result

            match = SourceFileMatch(
                path=path,
                category="implementation_python",
                confidence=confidence,
                evidence=evidence,
            )

            self._route_match(
                reference,
                reference.implementation_files,
                match,
            )

        # --------------------------------------------------------------
        # Python tests/QA directories
        # --------------------------------------------------------------

        for subdirectory_name in (
            "tests",
            "qa",
        ):

            subdirectory = (
                python_dir
                / subdirectory_name
            )

            if subdirectory.is_dir():

                test_candidates.extend(
                    subdirectory.rglob("*.py")
                )

        # --------------------------------------------------------------
        # Tests
        # --------------------------------------------------------------

        for path in sorted(
            set(test_candidates)
        ):

            if (
                not path.is_file()
                or not self._looks_like_test(path)
            ):
                continue

            normalized_stem = (
                _normalize_qa_stem(
                    path.stem
                )
            )

            result = _classify_match(
                normalized_stem,
                stems,
                patterns,
            )

            if result is None:
                continue

            confidence, evidence = result

            match = SourceFileMatch(
                path=path,
                category="test",
                confidence=confidence,
                evidence=evidence,
            )

            self._route_match(
                reference,
                reference.test_files,
                match,
            )

    # ------------------------------------------------------------------
    # Documentation
    # ------------------------------------------------------------------

    def _collect_documentation_files(
        self,
        module_root: Path,
        stems: Set[str],
        reference: SourceReference,
    ) -> None:
        """
        Search docs/ for block-related documentation.
        """

        docs_dir = (
            module_root / "docs"
        )

        if not docs_dir.is_dir():
            return

        for path in sorted(
            docs_dir.rglob("*")
        ):

            if (
                not path.is_file()
                or path.suffix.lower()
                not in _DOC_SUFFIXES
            ):
                continue

            normalized_stem = path.stem

            # Exact documentation stem.
            if normalized_stem in stems:

                match = SourceFileMatch(
                    path=path,
                    category="documentation",
                    confidence=MatchConfidence.MEDIUM,
                    evidence=(
                        "filename stem matches "
                        f"block stem candidate "
                        f"'{normalized_stem}'"
                    ),
                )

                self._route_match(
                    reference,
                    reference.documentation_files,
                    match,
                )

                continue

            # Weak documentation overlap.
            for candidate in stems:

                if (
                    len(candidate)
                    >= _MIN_DOC_STEM_LENGTH
                    and candidate
                    in normalized_stem
                ):

                    match = SourceFileMatch(
                        path=path,
                        category="documentation",
                        confidence=MatchConfidence.LOW,
                        evidence=(
                            "filename contains block "
                            "stem candidate "
                            f"'{candidate}'"
                        ),
                    )

                    self._route_match(
                        reference,
                        reference.documentation_files,
                        match,
                    )

                    break

    # ------------------------------------------------------------------
    # Test detection
    # ------------------------------------------------------------------

    @staticmethod
    def _looks_like_test(
        path: Path,
    ) -> bool:
        """
        Determine whether a path looks like a QA/test file.
        """

        name = path.name.lower()

        if any(
            name.startswith(prefix)
            for prefix in _TEST_MARKER_PREFIXES
        ):
            return True

        if any(
            marker in name
            for marker in _TEST_MARKER_SUBSTRINGS
        ):
            return True

        return any(
            part.lower()
            in _TEST_DIRECTORY_NAMES
            for part in path.parts
        )

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    @staticmethod
    def _count_at_confidence(
        reference: SourceReference,
        level: MatchConfidence,
    ) -> int:
        """
        Count confirmed matches at a confidence level.

        possible_references are deliberately excluded.
        """

        all_matches = (
            reference.implementation_files
            + reference.header_files
            + reference.binding_files
            + reference.test_files
            + reference.documentation_files
        )

        return sum(
            1
            for match in all_matches
            if match.confidence == level
        )

    # ------------------------------------------------------------------
    # Storage filename
    # ------------------------------------------------------------------

    @staticmethod
    def _build_filename(
        reference: SourceReference,
    ) -> str:
        """
        Build deterministic storage filename.

        Format:

            repository__module__block.sources.json
        """

        return (
            SourceReferenceMapper
            ._build_filename_from_parts(
                reference.repository
                or "unknown_repository",
                reference.module
                or "unknown_module",
                reference.block_id
                or "unknown_block",
            )
        )

    @staticmethod
    def _build_filename_from_parts(
        repository: str,
        module: str,
        block_id: str,
    ) -> str:
        """
        Build deterministic filesystem-safe filename.
        """

        parts = [
            _sanitize_filename_part(
                str(part)
            )
            for part in (
                repository,
                module,
                block_id,
            )
        ]

        return (
            "__".join(parts)
            + ".sources.json"
        )