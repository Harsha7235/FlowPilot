"""
FlowPilot static source-code analyzer.

Analyzes confirmed SourceReference files and extracts conservative,
structured implementation knowledge.

Supported:
    - C/C++ source
    - C/C++ headers
    - Python
    - GNU Radio C++ Python bindings

This is intentionally NOT a compiler or full AST parser.
"""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from flowpilot.knowledge.parser.source_code_models import (
    ImplementationKnowledge,
    SourceBinding,
    SourceClass,
    SourceFileKnowledge,
    SourceFunction,
    SourceLanguage,
    SourceMethod,
    SourceParseStatus,
)
from flowpilot.knowledge.parser.source_reference_mapper import (
    SourceFileMatch,
    SourceReference,
)


__all__ = [
    "SourceCodeAnalyzer",
]

SOURCE_CODE_ANALYZER_VERSION = "cpp-qualified-v5"


# ---------------------------------------------------------------------------
# Regular expressions
# ---------------------------------------------------------------------------

_CPP_INCLUDE_RE = re.compile(
    r'^\s*#\s*include\s*[<"]([^>"]+)[>"]',
    re.MULTILINE,
)

_CPP_NAMESPACE_RE = re.compile(
    r'\bnamespace\s+([A-Za-z_]\w*(?:::\w+)*)\s*\{'
)

_CPP_CLASS_RE = re.compile(
    r'\b(class|struct)\s+'
    r'([A-Za-z_]\w*)'
    r'(?:\s+final)?'
    r'(?:\s*:\s*([^{]+))?'
    r'\s*\{',
    re.MULTILINE,
)

_CPP_METHOD_RE = re.compile(
    r"""
    (?P<prefix>
        (?:
            static\s+
        )?
        (?:
            inline\s+
        )?
        (?:
            virtual\s+
        )?
        (?:
            explicit\s+
        )?
    )
    (?P<return>
        [A-Za-z_][\w:<>,\s*&~]*?
    )
    \s+
    (?P<name>
        ~?[A-Za-z_]\w*
    )
    \s*
    \(
        (?P<params>[^()]*(?:\([^()]*\)[^()]*)*)
    \)
    (?P<qualifiers>
        [^{;]*?
    )
    (?P<terminator>
        \{
        |
        ;
    )
    """,
    re.VERBOSE | re.MULTILINE,
)

_CPP_QUALIFIED_CTOR_DTOR_RE = re.compile(
    r"""
    (?P<class>
        [A-Za-z_]\w*(?:::[A-Za-z_]\w*)*
    )
    ::
    (?P<name>
        ~?[A-Za-z_]\w*
    )
    \s*\(
        (?P<params>[^()]*(?:\([^()]*\)[^()]*)*)
    \)
    (?P<qualifiers>
        (?:
            \s+
            (?:const|volatile|noexcept(?:\s*\([^;{}]*\))?|override|final|constexpr|&{1,2})
        )*
        \s*
        (?: : [^{};]* )?
        \s*
    )
    \{
    """,
    re.VERBOSE | re.MULTILINE,
)

_CPP_QUALIFIED_METHOD_RE = re.compile(
    r"""
    (?P<return>
        (?:const\s+)?
        [A-Za-z_]\w*(?:::[A-Za-z_]\w*)*
        (?:\s*<[^{}();]*>)?
        (?:\s*[*&]+)?
    )
    \s+
    (?P<class>
        [A-Za-z_]\w*(?:::[A-Za-z_]\w*)*
    )
    ::
    (?P<name>[A-Za-z_]\w*)
    \s*\(
        (?P<params>[^()]*(?:\([^()]*\)[^()]*)*)
    \)
    (?P<qualifiers>
        (?:\s+(?:const|volatile|noexcept(?:\s*\([^;{}]*\))?|override|final|constexpr|&{1,2}))*
        \s*
    )
    \{
    """,
    re.VERBOSE | re.MULTILINE,
)

_CPP_VARIABLE_RE = re.compile(
    r"""
    (?:
        public|protected|private
    )?
    \s*
    (?P<type>
        [A-Za-z_][\w:<>,\s*&]*?
    )
    \s+
    (?P<name>
        [A-Za-z_]\w*
    )
    \s*
    (?:
        =[^;]+
    )?
    ;
    """,
    re.VERBOSE,
)

_CPP_GNURADIO_REF_RE = re.compile(
    r'\b(?:gr|gnuradio)::'
    r'[A-Za-z_][\w:]*'
)

_PY_IMPORT_RE = re.compile(
    r'^\s*import\s+(.+)$',
    re.MULTILINE,
)

_PY_FROM_IMPORT_RE = re.compile(
    r'^\s*from\s+([A-Za-z_][\w.]*)\s+import\s+(.+)$',
    re.MULTILINE,
)

_BINDING_CLASS_RE = re.compile(
    r"""
    \b(?:py::class_|py::class)
    \s*<
    \s*(?P<cpp>[A-Za-z_]\w*(?:::\w+)*)
    [^>]*>
    \s*
    (?P<rest>
        [^;]+
    )
    """,
    re.VERBOSE | re.MULTILINE,
)

_BINDING_MODULE_RE = re.compile(
    r'\b(?:py::module|m)\s*(?:&)?'
    r'\s*(?:module|m)?'
    r'\s*(?:=)?\s*'
    r'(?:py::module|module)'
    r'\s*\(\s*'
    r'["\']([^"\']+)["\']'
)

_BINDING_METHOD_RE = re.compile(
    r'\.\s*def(?:_static)?\s*\(\s*'
    r'["\']([^"\']+)["\']'
)

_BINDING_DEF_READONLY_RE = re.compile(
    r'\.\s*def_read(?:only|write)\s*\(\s*'
    r'["\']([^"\']+)["\']'
)

_BINDING_CPP_INCLUDE_RE = re.compile(
    r'#include\s*[<"]([^>"]+)[>"]'
)

_STRING_RE = re.compile(
    r'["\']([^"\']+)["\']'
)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _line_number(
    text: str,
    offset: int,
) -> int:
    """Return 1-based source line for a character offset."""
    return text.count("\n", 0, offset) + 1


def _line_end(
    text: str,
    offset: int,
) -> int:
    """Return the final line number represented by an offset."""
    return text.count("\n", 0, offset) + 1


def _strip_cpp_comments(
    text: str,
) -> str:
    """
    Remove C/C++ comments while preserving line structure.

    Strings are intentionally not fully lexed. This is a conservative
    preprocessing step for lightweight structural extraction.
    """

    text = re.sub(
        r'/\*.*?\*/',
        lambda match: "\n" * match.group(0).count("\n"),
        text,
        flags=re.DOTALL,
    )

    text = re.sub(
        r'//.*?$',
        '',
        text,
        flags=re.MULTILINE,
    )

    return text


def _split_parameters(
    parameters: str,
) -> List[str]:
    """
    Split a C++ parameter list conservatively.

    Nested template/function expressions are handled using simple
    angle/parenthesis/bracket depth tracking.
    """

    parameters = parameters.strip()

    if not parameters:
        return []

    result: List[str] = []
    current: List[str] = []

    angle_depth = 0
    paren_depth = 0
    bracket_depth = 0

    for char in parameters:

        if char == "<":
            angle_depth += 1

        elif char == ">":
            angle_depth = max(
                0,
                angle_depth - 1,
            )

        elif char == "(":
            paren_depth += 1

        elif char == ")":
            paren_depth = max(
                0,
                paren_depth - 1,
            )

        elif char == "[":
            bracket_depth += 1

        elif char == "]":
            bracket_depth = max(
                0,
                bracket_depth - 1,
            )

        if (
            char == ","
            and angle_depth == 0
            and paren_depth == 0
            and bracket_depth == 0
        ):
            value = "".join(current).strip()

            if value:
                result.append(value)

            current = []

        else:
            current.append(char)

    value = "".join(current).strip()

    if value:
        result.append(value)

    return result


def _clean_cpp_type(
    value: str,
) -> str:
    """Normalize whitespace in a C++ type."""
    return re.sub(
        r"\s+",
        " ",
        value.strip(),
    )


def _extract_base_classes(
    inheritance: Optional[str],
) -> List[str]:
    """
    Extract base class names from a C++ inheritance clause.
    """

    if not inheritance:
        return []

    bases: List[str] = []

    for raw_base in inheritance.split(","):

        value = raw_base.strip()

        value = re.sub(
            r'\b(public|protected|private|virtual)\b',
            '',
            value,
        )

        value = re.sub(
            r'\s+',
            ' ',
            value,
        ).strip()

        if value:
            bases.append(value)

    return bases


def _detect_language(
    path: Path,
    category: str = "",
) -> SourceLanguage:
    """
    Determine source language from extension/category.
    """

    suffix = path.suffix.lower()

    if category == "binding":
        return SourceLanguage.BINDING

    if suffix in {".cc", ".cpp", ".cxx"}:
        return SourceLanguage.CPP

    if suffix in {".h", ".hpp"}:
        return SourceLanguage.HEADER

    if suffix == ".py":
        return SourceLanguage.PYTHON

    return SourceLanguage.UNKNOWN


def _is_supported_language(
    language: SourceLanguage,
) -> bool:
    return language in {
        SourceLanguage.CPP,
        SourceLanguage.HEADER,
        SourceLanguage.PYTHON,
        SourceLanguage.BINDING,
    }


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class SourceCodeAnalyzer:
    """
    Lightweight deterministic static source analyzer.

    It consumes confirmed SourceReference objects and analyzes only
    their confirmed source files.
    """

    def __init__(
        self,
        *,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.logger = (
            logger
            or logging.getLogger(
                __name__
            )
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_file(
        self,
        path: Path,
        category: str = "",
    ) -> SourceFileKnowledge:
        """
        Analyze one source file.
        """

        path = Path(path)

        language = _detect_language(
            path,
            category,
        )

        result = SourceFileKnowledge(
            path=path,
            language=language,
        )

        if not _is_supported_language(
            language
        ):
            result.parse_status = (
                SourceParseStatus.UNSUPPORTED
            )

            result.parse_errors.append(
                f"Unsupported source type: {path.suffix}"
            )

            return result

        if not path.exists():
            result.parse_status = (
                SourceParseStatus.FAILED
            )

            result.parse_errors.append(
                f"Source file does not exist: {path}"
            )

            return result

        if not path.is_file():
            result.parse_status = (
                SourceParseStatus.FAILED
            )

            result.parse_errors.append(
                f"Source path is not a file: {path}"
            )

            return result

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except Exception as exc:

            result.parse_status = (
                SourceParseStatus.FAILED
            )

            result.parse_errors.append(
                f"Unable to read source file: {exc}"
            )

            return result

        result.line_count = (
            len(text.splitlines())
        )

        try:

            if language in {
                SourceLanguage.CPP,
                SourceLanguage.HEADER,
            }:
                self._analyze_cpp(
                    text,
                    result,
                )

            elif language == SourceLanguage.PYTHON:
                self._analyze_python(
                    text,
                    result,
                )

            elif language == SourceLanguage.BINDING:
                self._analyze_binding(
                    text,
                    result,
                )

            result.parse_status = (
                SourceParseStatus.SUCCESS
            )

        except Exception as exc:

            self.logger.exception(
                "Source analysis failed for %s",
                path,
            )

            result.parse_status = (
                SourceParseStatus.PARTIAL
            )

            result.parse_errors.append(
                f"Static extraction error: {exc}"
            )

        return result

    def analyze_reference(
        self,
        reference: SourceReference,
    ) -> ImplementationKnowledge:
        """
        Analyze all confirmed files from one SourceReference.

        possible_references are deliberately ignored.
        """

        knowledge = ImplementationKnowledge(
            block_id=reference.block_id,
            repository=reference.repository,
            module=reference.module,
        )

        matches = self._confirmed_matches(
            reference
        )

        for match in matches:

            if match.path is None:
                continue

            try:

                result = self.analyze_file(
                    match.path,
                    match.category,
                )

                knowledge.source_files.append(
                    result
                )

            except Exception as exc:

                self.logger.exception(
                    "Unexpected analyzer failure for %s",
                    match.path,
                )

                knowledge.errors.append(
                    f"{match.path}: {exc}"
                )

        knowledge.recompute_statistics()

        return knowledge

    def analyze_references(
        self,
        references: Sequence[SourceReference],
    ) -> List[ImplementationKnowledge]:
        """
        Analyze multiple SourceReference records.

        One failed block does not stop the complete run.
        """

        results: List[
            ImplementationKnowledge
        ] = []

        for reference in references:

            try:

                results.append(
                    self.analyze_reference(
                        reference
                    )
                )

            except Exception as exc:

                self.logger.exception(
                    "Failed to analyze block %s",
                    reference.block_id,
                )

                failed = ImplementationKnowledge(
                    block_id=reference.block_id,
                    repository=reference.repository,
                    module=reference.module,
                    errors=[
                        str(exc)
                    ],
                )

                results.append(
                    failed
                )

        return results

    # ------------------------------------------------------------------
    # Confirmed reference handling
    # ------------------------------------------------------------------

    @staticmethod
    def _confirmed_matches(
        reference: SourceReference,
    ) -> List[SourceFileMatch]:
        """
        Return only confirmed source references.

        Weak possible_references are intentionally excluded.
        """

        return [
            *reference.implementation_files,
            *reference.header_files,
            *reference.binding_files,
            *reference.test_files,
            *reference.documentation_files,
        ]

    # ------------------------------------------------------------------
    # C/C++ analysis
    # ------------------------------------------------------------------

    def _analyze_cpp(
        self,
        text: str,
        result: SourceFileKnowledge,
    ) -> None:
        """
        Extract conservative C/C++ structure.
        """

        clean_text = _strip_cpp_comments(
            text
        )

        # --------------------------------------------------------------
        # Includes
        # --------------------------------------------------------------

        result.includes = list(
            dict.fromkeys(
                _CPP_INCLUDE_RE.findall(
                    clean_text
                )
            )
        )

        # --------------------------------------------------------------
        # Namespaces
        # --------------------------------------------------------------

        result.namespaces = list(
            dict.fromkeys(
                _CPP_NAMESPACE_RE.findall(
                    clean_text
                )
            )
        )

        # --------------------------------------------------------------
        # GNU Radio references
        # --------------------------------------------------------------

        result.referenced_gnuradio_classes = (
            list(
                dict.fromkeys(
                    _CPP_GNURADIO_REF_RE.findall(
                        clean_text
                    )
                )
            )
        )

        # --------------------------------------------------------------
        # Dependencies
        # --------------------------------------------------------------

        result.dependencies = list(
            dict.fromkeys(
                include
                for include in result.includes
                if (
                    include.startswith(
                        "gnuradio/"
                    )
                    or include.startswith(
                        "boost/"
                    )
                    or include.startswith(
                        "pmt"
                    )
                )
            )
        )

        # --------------------------------------------------------------
        # Classes and structs
        # --------------------------------------------------------------

        class_matches = list(
            _CPP_CLASS_RE.finditer(
                clean_text
            )
        )

        for match in class_matches:

            kind = match.group(
                1
            )

            name = match.group(
                2
            )

            inheritance = match.group(
                3
            )

            line_start = _line_number(
                clean_text,
                match.start(),
            )

            line_end = self._find_brace_end(
                clean_text,
                match.end() - 1,
            )

            namespace = (
                self._namespace_at_position(
                    clean_text,
                    match.start(),
                )
            )

            source_class = SourceClass(
                name=name,
                kind=kind,
                base_classes=_extract_base_classes(
                    inheritance
                ),
                namespace=namespace,
                line_start=line_start,
                line_end=line_end,
                source_file=result.path,
            )

            # ----------------------------------------------------------
            # Extract methods inside class body
            # ----------------------------------------------------------

            body_end = (
                line_end
                if line_end is not None
                else len(clean_text)
            )

            body = clean_text[
                match.end():body_end
            ]

            body_offset = match.end()

            for method_match in _CPP_METHOD_RE.finditer(
                body
            ):

                method = self._build_cpp_method(
                    method_match,
                    body,
                    source_class.name,
                    result.path,
                    body_offset,
                )

                if method is not None:
                    source_class.methods.append(
                        method
                    )

            # ----------------------------------------------------------
            # Member variables
            # ----------------------------------------------------------

            source_class.member_variables = (
                self._extract_member_variables(
                    body
                )
            )

            result.classes.append(
                source_class
            )

        # --------------------------------------------------------------
        # Qualified out-of-class methods/functions
        # --------------------------------------------------------------

        # Qualified out-of-class definitions with an explicit return type.
        # If the owner class is not declared in this file (common for .cc
        # files that include the class declaration from a header), preserve
        # the definition as a SourceFunction instead of dropping it.
        for match in _CPP_QUALIFIED_METHOD_RE.finditer(
            clean_text
        ):

            class_path = match.group("class")
            target = self._find_class(
                result.classes,
                class_path,
            )

            method = self._build_qualified_cpp_method(
                match,
                clean_text,
                result.path,
            )

            if method is None:
                continue

            if target is not None:
                if not any(
                    existing.name == method.name
                    and existing.line_start == method.line_start
                    for existing in target.methods
                ):
                    target.methods.append(method)
            else:
                function = self._build_qualified_cpp_function(
                    match,
                    clean_text,
                    result.path,
                )
                if function is not None:
                    if not any(
                        existing.name == function.name
                        and existing.line_start == function.line_start
                        for existing in result.functions
                    ):
                        result.functions.append(function)

        # Constructors/destructors have no return type, so they cannot be
        # matched by _CPP_QUALIFIED_METHOD_RE. Handle them separately.
        for match in _CPP_QUALIFIED_CTOR_DTOR_RE.finditer(
            clean_text
        ):
            class_path = match.group("class")
            name = match.group("name")
            short_class_name = class_path.split("::")[-1]

            # Only accept actual constructors/destructors in this pass.
            if name not in {
                short_class_name,
                f"~{short_class_name}",
            }:
                continue

            target = self._find_class(
                result.classes,
                class_path,
            )

            if target is not None:
                method = self._build_qualified_cpp_method(
                    match,
                    clean_text,
                    result.path,
                    return_type="",
                )
                if method is not None and not any(
                    existing.name == method.name
                    and existing.line_start == method.line_start
                    for existing in target.methods
                ):
                    target.methods.append(method)
            else:
                function = self._build_qualified_cpp_function(
                    match,
                    clean_text,
                    result.path,
                    return_type="",
                )
                if function is not None and not any(
                    existing.name == function.name
                    and existing.line_start == function.line_start
                    for existing in result.functions
                ):
                    result.functions.append(function)

        # --------------------------------------------------------------
        # Keep deterministic ordering
        # --------------------------------------------------------------

        result.classes.sort(
            key=lambda item: (
                item.line_start
                or 0,
                item.name,
            )
        )

        for source_class in result.classes:
            source_class.methods.sort(
                key=lambda item: (
                    item.line_start
                    or 0,
                    item.name,
                )
            )

    # ------------------------------------------------------------------
    # C++ method builders
    # ------------------------------------------------------------------

    def _build_cpp_method(
        self,
        match: re.Match,
        body: str,
        class_name: str,
        source_file: Optional[Path],
        body_offset: int,
    ) -> Optional[SourceMethod]:
        """
        Convert a class-body regex match into SourceMethod.
        """

        name = match.group(
            "name"
        )

        return_type = _clean_cpp_type(
            match.group(
                "return"
            )
        )

        parameters_raw = match.group(
            "params"
        )

        parameters = _split_parameters(
            parameters_raw
        )

        prefix = (
            match.group(
                "prefix"
            )
            or ""
        )

        qualifiers = (
            match.group(
                "qualifiers"
            )
            or ""
        )

        signature = (
            f"{return_type} "
            f"{name}("
            f"{parameters_raw.strip()}"
            f")"
            f"{qualifiers.strip()}"
        ).strip()

        local_offset = (
            match.start()
        )

        line_start = (
            _line_number(
                body,
                local_offset,
            )
        )

        absolute_start = (
            body_offset
            + local_offset
        )

        is_constructor = (
            name == class_name
        )

        is_destructor = (
            name == f"~{class_name}"
        )

        return SourceMethod(
            name=name,
            signature=signature,
            return_type=return_type,
            parameters=parameters,
            is_static=(
                "static" in prefix.split()
            ),
            is_virtual=(
                "virtual" in prefix.split()
            ),
            is_override=(
                "override" in qualifiers
            ),
            is_const=(
                re.search(
                    r"\bconst\b",
                    qualifiers,
                )
                is not None
            ),
            is_constructor=is_constructor,
            is_destructor=is_destructor,
            line_start=line_start,
            line_end=_line_end(
                body,
                match.end(),
            ),
            source_file=source_file,
        )

    def _build_qualified_cpp_method(
        self,
        match: re.Match,
        text: str,
        source_file: Optional[Path],
        return_type: Optional[str] = None,
    ) -> Optional[SourceMethod]:
        """
        Build method representation for:

            Class::method(...)
        """

        name = match.group(
            "name"
        )

        class_path = match.group(
            "class"
        )

        class_name = class_path.split(
            "::"
        )[-1]

        if return_type is None:
            return_type = _clean_cpp_type(
                match.group("return")
            )
        else:
            return_type = _clean_cpp_type(
                return_type
            )

        params_raw = match.group(
            "params"
        )

        parameters = _split_parameters(
            params_raw
        )

        qualifiers = (
            match.group("qualifiers")
            or ""
        ).strip()

        # A constructor has no return type. Its initializer list is not
        # part of the callable signature. The dedicated constructor regex
        # may still capture the initializer list, so remove it before
        # constructing the signature.
        if not return_type and ":" in qualifiers:
            qualifiers = qualifiers.split(":", 1)[0].strip()

        qualified_name = f"{class_path}::{name}"
        signature = (
            f"{return_type} " if return_type else ""
        ) + f"{qualified_name}({params_raw.strip()})"
        if qualifiers:
            signature += qualifiers
        signature = re.sub(r"\s+", " ", signature).strip()

        return SourceMethod(
            name=name,
            signature=signature,
            return_type=return_type,
            parameters=parameters,
            is_const=(
                re.search(
                    r"\bconst\b",
                    qualifiers,
                )
                is not None
            ),
            is_constructor=(
                name == class_name
            ),
            is_destructor=(
                name == f"~{class_name}"
            ),
            line_start=_line_number(
                text,
                match.start(),
            ),
            line_end=_line_end(
                text,
                match.end(),
            ),
            source_file=source_file,
        )

    def _build_qualified_cpp_function(
        self,
        match: re.Match,
        text: str,
        source_file: Optional[Path],
        return_type: Optional[str] = None,
    ) -> Optional[SourceFunction]:
        """
        Preserve a qualified out-of-class C++ definition when its
        declaring class is not present in the current source file.

        Examples:
            agc_ff::sptr agc_ff::make(...)
            agc_ff_impl::agc_ff_impl(...)
            agc_ff_impl::~agc_ff_impl(...)
        """

        class_path = match.group("class")
        name = match.group("name")
        params_raw = match.group("params")
        parameters = _split_parameters(params_raw)

        if return_type is None:
            return_type = _clean_cpp_type(
                match.group("return")
            )
        else:
            return_type = _clean_cpp_type(
                return_type
            )

        qualifiers = (
            match.group("qualifiers")
            or ""
        ).strip()

        qualified_name = (
            f"{class_path}::{name}"
        )

        signature_prefix = (
            f"{return_type} "
            if return_type
            else ""
        )

        signature = (
            f"{signature_prefix}"
            f"{qualified_name}"
            f"({params_raw.strip()})"
            f"{qualifiers}"
        ).strip()

        return SourceFunction(
            name=qualified_name,
            signature=signature,
            return_type=return_type,
            parameters=parameters,
            line_start=_line_number(
                text,
                match.start(),
            ),
            line_end=_line_end(
                text,
                match.end(),
            ),
            source_file=source_file,
        )

    # ------------------------------------------------------------------
    # C++ helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_brace_end(
        text: str,
        opening_brace: int,
    ) -> Optional[int]:
        """
        Find matching closing brace.

        This is deliberately conservative and does not attempt to
        fully parse strings/preprocessor constructs.
        """

        if (
            opening_brace < 0
            or opening_brace >= len(text)
            or text[opening_brace] != "{"
        ):
            return None

        depth = 0

        for index in range(
            opening_brace,
            len(text),
        ):

            char = text[index]

            if char == "{":
                depth += 1

            elif char == "}":
                depth -= 1

                if depth == 0:
                    return index

        return None

    @staticmethod
    def _namespace_at_position(
        text: str,
        position: int,
    ) -> Optional[str]:
        """
        Best-effort namespace detection at a source position.
        """

        before = text[:position]

        matches = list(
            _CPP_NAMESPACE_RE.finditer(
                before
            )
        )

        if not matches:
            return None

        return matches[-1].group(1)

    @staticmethod
    def _find_class(
        classes: Sequence[SourceClass],
        qualified_name: str,
    ) -> Optional[SourceClass]:
        """
        Find a discovered class by qualified or short name.
        """

        short_name = qualified_name.split(
            "::"
        )[-1]

        for source_class in classes:

            if (
                source_class.name
                == short_name
            ):
                return source_class

        return None

    @staticmethod
    def _extract_member_variables(
        body: str,
    ) -> List[str]:
        """
        Extract obvious member declarations.

        This intentionally avoids complex C++ declarations.
        """

        variables: List[str] = []

        for match in _CPP_VARIABLE_RE.finditer(
            body
        ):

            name = match.group(
                "name"
            )

            if not name:
                continue

            value = (
                match.group(0)
                .strip()
            )

            # Avoid treating method declarations as variables.
            if "(" in value:
                continue

            variables.append(value)

        return list(
            dict.fromkeys(
                variables
            )
        )

    # ------------------------------------------------------------------
    # Python analysis
    # ------------------------------------------------------------------

    def _analyze_python(
        self,
        text: str,
        result: SourceFileKnowledge,
    ) -> None:
        """
        Analyze Python using the standard-library AST.

        This does not execute the Python file.
        """

        # Imports are also extracted textually so malformed Python
        # can still yield useful information.
        result.includes = list(
            dict.fromkeys(
                self._extract_python_imports(
                    text
                )
            )
        )

        try:
            tree = ast.parse(
                text
            )
        except SyntaxError as exc:

            result.parse_status = (
                SourceParseStatus.PARTIAL
            )

            result.parse_errors.append(
                f"Python syntax error: {exc}"
            )

            return

        for node in tree.body:

            if isinstance(
                node,
                (
                    ast.Import,
                    ast.ImportFrom,
                ),
            ):
                continue

            if isinstance(
                node,
                (
                    ast.ClassDef,
                ),
            ):

                result.classes.append(
                    self._parse_python_class(
                        node,
                        result.path,
                    )
                )

            elif isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):

                result.functions.append(
                    self._parse_python_function(
                        node,
                        result.path,
                    )
                )

            elif isinstance(
                node,
                (
                    ast.Assign,
                    ast.AnnAssign,
                ),
            ):

                names = (
                    self._python_assignment_names(
                        node
                    )
                )

                result.module_level_variables.extend(
                    names
                )

        result.module_level_variables = list(
            dict.fromkeys(
                result.module_level_variables
            )
        )

        result.classes.sort(
            key=lambda item: (
                item.line_start
                or 0
            )
        )

    @staticmethod
    def _extract_python_imports(
        text: str,
    ) -> List[str]:
        """
        Extract readable Python import statements.
        """

        imports: List[str] = []

        for match in _PY_IMPORT_RE.finditer(
            text
        ):
            imports.append(
                f"import {match.group(1).strip()}"
            )

        for match in _PY_FROM_IMPORT_RE.finditer(
            text
        ):
            imports.append(
                (
                    f"from {match.group(1)} "
                    f"import {match.group(2).strip()}"
                )
            )

        return imports

    def _parse_python_class(
        self,
        node: ast.ClassDef,
        source_file: Optional[Path],
    ) -> SourceClass:
        """
        Convert Python AST class into SourceClass.
        """

        bases: List[str] = []

        for base in node.bases:

            value = self._python_expr_name(
                base
            )

            if value:
                bases.append(value)

        decorators = [
            self._python_expr_name(
                decorator
            )
            or ast.unparse(decorator)
            for decorator in node.decorator_list
        ]

        source_class = SourceClass(
            name=node.name,
            kind="class",
            base_classes=bases,
            decorators=decorators,
            line_start=getattr(
                node,
                "lineno",
                None,
            ),
            line_end=getattr(
                node,
                "end_lineno",
                None,
            ),
            source_file=source_file,
        )

        for child in node.body:

            if isinstance(
                child,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):

                source_class.methods.append(
                    self._parse_python_method(
                        child,
                        node.name,
                        source_file,
                    )
                )

        return source_class

    def _parse_python_method(
        self,
        node: ast.AST,
        class_name: str,
        source_file: Optional[Path],
    ) -> SourceMethod:
        """
        Convert Python method AST into SourceMethod.
        """

        name = getattr(
            node,
            "name",
            "<unknown>",
        )

        args = getattr(
            node,
            "args",
            None,
        )

        parameters: List[str] = []

        if args is not None:

            all_args = [
                *args.posonlyargs,
                *args.args,
                *args.kwonlyargs,
            ]

            for argument in all_args:

                if argument.arg:
                    parameters.append(
                        argument.arg
                    )

            if args.vararg:
                parameters.append(
                    f"*{args.vararg.arg}"
                )

            if args.kwarg:
                parameters.append(
                    f"**{args.kwarg.arg}"
                )

        decorators = getattr(
            node,
            "decorator_list",
            [],
        )

        decorator_names = [
            self._python_expr_name(
                decorator
            )
            or ast.unparse(decorator)
            for decorator in decorators
        ]

        return SourceMethod(
            name=name,
            signature=(
                f"{name}("
                f"{', '.join(parameters)}"
                f")"
            ),
            parameters=parameters,
            is_static=(
                "staticmethod"
                in decorator_names
            ),
            line_start=getattr(
                node,
                "lineno",
                None,
            ),
            line_end=getattr(
                node,
                "end_lineno",
                None,
            ),
            source_file=source_file,
        )

    def _parse_python_function(
        self,
        node: ast.AST,
        source_file: Optional[Path],
    ) -> SourceFunction:
        """
        Convert Python function AST into SourceFunction.
        """

        name = getattr(
            node,
            "name",
            "<unknown>",
        )

        args = getattr(
            node,
            "args",
            None,
        )

        parameters: List[str] = []

        if args is not None:

            all_args = [
                *args.posonlyargs,
                *args.args,
                *args.kwonlyargs,
            ]

            parameters = [
                argument.arg
                for argument in all_args
            ]

            if args.vararg:
                parameters.append(
                    f"*{args.vararg.arg}"
                )

            if args.kwarg:
                parameters.append(
                    f"**{args.kwarg.arg}"
                )

        decorators = getattr(
            node,
            "decorator_list",
            [],
        )

        decorator_names = [
            self._python_expr_name(
                decorator
            )
            or ast.unparse(decorator)
            for decorator in decorators
        ]

        return SourceFunction(
            name=name,
            signature=(
                f"{name}("
                f"{', '.join(parameters)}"
                f")"
            ),
            parameters=parameters,
            decorators=decorator_names,
            line_start=getattr(
                node,
                "lineno",
                None,
            ),
            line_end=getattr(
                node,
                "end_lineno",
                None,
            ),
            source_file=source_file,
        )

    @staticmethod
    def _python_expr_name(
        node: ast.AST,
    ) -> Optional[str]:
        """
        Convert a simple Python AST expression into a readable name.
        """

        if isinstance(
            node,
            ast.Name,
        ):
            return node.id

        if isinstance(
            node,
            ast.Attribute,
        ):

            parent = (
                SourceCodeAnalyzer
                ._python_expr_name(
                    node.value
                )
            )

            if parent:
                return (
                    f"{parent}.{node.attr}"
                )

            return node.attr

        if isinstance(
            node,
            ast.Constant,
        ):

            if isinstance(
                node.value,
                str,
            ):
                return node.value

        return None

    @staticmethod
    def _python_assignment_names(
        node: ast.AST,
    ) -> List[str]:
        """
        Extract names assigned at module level.
        """

        names: List[str] = []

        if isinstance(
            node,
            ast.Assign,
        ):

            for target in node.targets:

                if isinstance(
                    target,
                    ast.Name,
                ):
                    names.append(
                        target.id
                    )

        elif isinstance(
            node,
            ast.AnnAssign,
        ):

            if isinstance(
                node.target,
                ast.Name,
            ):
                names.append(
                    node.target.id
                )

        return names

    # ------------------------------------------------------------------
    # Binding analysis
    # ------------------------------------------------------------------

    def _analyze_binding(
        self,
        text: str,
        result: SourceFileKnowledge,
    ) -> None:
        """
        Analyze GNU Radio-style C++ Python binding files.
        """

        clean_text = _strip_cpp_comments(
            text
        )

        result.includes = list(
            dict.fromkeys(
                _BINDING_CPP_INCLUDE_RE.findall(
                    clean_text
                )
            )
        )

        result.dependencies = list(
            dict.fromkeys(
                include
                for include in result.includes
                if (
                    include.startswith(
                        "gnuradio/"
                    )
                    or include.startswith(
                        "pmt"
                    )
                )
            )
        )

        # --------------------------------------------------------------
        # py::class_<CppType>
        # --------------------------------------------------------------

        class_matches = list(
            _BINDING_CLASS_RE.finditer(
                clean_text
            )
        )

        if class_matches:

            binding = SourceBinding(
                line_start=_line_number(
                    clean_text,
                    class_matches[0].start(),
                ),
                line_end=_line_end(
                    clean_text,
                    class_matches[-1].end(),
                ),
                source_file=result.path,
                includes=list(
                    result.includes
                ),
            )

            for match in class_matches:

                cpp_name = match.group(
                    "cpp"
                )

                if cpp_name:
                    binding.cpp_classes.append(
                        cpp_name
                    )

                rest = match.group(
                    "rest"
                )

                for method_match in (
                    _BINDING_METHOD_RE.finditer(
                        rest
                    )
                ):

                    binding.exposed_methods.append(
                        method_match.group(1)
                    )

                for method_match in (
                    _BINDING_DEF_READONLY_RE.finditer(
                        rest
                    )
                ):

                    binding.exposed_methods.append(
                        method_match.group(1)
                    )

            binding.cpp_classes = list(
                dict.fromkeys(
                    binding.cpp_classes
                )
            )

            binding.exposed_methods = list(
                dict.fromkeys(
                    binding.exposed_methods
                )
            )

            result.bindings.append(
                binding
            )

        # --------------------------------------------------------------
        # Generic .def(...) extraction
        # --------------------------------------------------------------

        exposed_methods = [
            match.group(1)
            for match in _BINDING_METHOD_RE.finditer(
                clean_text
            )
        ]

        exposed_methods.extend(
            match.group(1)
            for match in _BINDING_DEF_READONLY_RE.finditer(
                clean_text
            )
        )

        exposed_methods = list(
            dict.fromkeys(
                exposed_methods
            )
        )

        if exposed_methods:

            if result.bindings:

                for binding in result.bindings:

                    binding.exposed_methods = list(
                        dict.fromkeys(
                            [
                                *binding.exposed_methods,
                                *exposed_methods,
                            ]
                        )
                    )

            else:

                result.bindings.append(
                    SourceBinding(
                        exposed_methods=exposed_methods,
                        includes=list(
                            result.includes
                        ),
                        line_start=1,
                        line_end=result.line_count,
                        source_file=result.path,
                    )
                )

        # --------------------------------------------------------------
        # Python module names from string literals
        # --------------------------------------------------------------

        module_names: List[str] = []

        for match in _STRING_RE.finditer(
            clean_text
        ):

            value = match.group(1)

            if (
                "." in value
                and " " not in value
                and len(value) < 100
            ):
                module_names.append(
                    value
                )

        if result.bindings:

            result.bindings[0].python_module_names = (
                list(
                    dict.fromkeys(
                        module_names
                    )
                )
            )

        # --------------------------------------------------------------
        # Represent bound C++ classes as SourceClass too
        # --------------------------------------------------------------

        for binding in result.bindings:

            for cpp_class in (
                binding.cpp_classes
            ):

                result.classes.append(
                    SourceClass(
                        name=cpp_class.split(
                            "::"
                        )[-1],
                        kind="binding",
                        line_start=(
                            binding.line_start
                        ),
                        line_end=(
                            binding.line_end
                        ),
                        source_file=result.path,
                    )
                )

    # ------------------------------------------------------------------
    # Convenience methods for direct file groups
    # ------------------------------------------------------------------

    def analyze_paths(
        self,
        paths: Iterable[Path],
    ) -> List[SourceFileKnowledge]:
        """
        Analyze a collection of paths directly.
        """

        results: List[
            SourceFileKnowledge
        ] = []

        for path in paths:

            try:

                results.append(
                    self.analyze_file(
                        Path(path)
                    )
                )

            except Exception as exc:

                self.logger.exception(
                    "Failed to analyze %s",
                    path,
                )

                results.append(
                    SourceFileKnowledge(
                        path=Path(path),
                        parse_status=(
                            SourceParseStatus.FAILED
                        ),
                        parse_errors=[
                            str(exc)
                        ],
                    )
                )

        return results