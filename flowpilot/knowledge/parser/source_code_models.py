"""
Structured models for static source-code analysis.

These models represent implementation knowledge extracted from
confirmed SourceReference files.

The models intentionally store conservative information only.
They do not represent a complete C++ or Python AST.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from flowpilot.core.models import BaseModel, ModelEncoder


__all__ = [
    "SourceLanguage",
    "SourceParseStatus",
    "SourceMethod",
    "SourceClass",
    "SourceFunction",
    "SourceBinding",
    "SourceFileKnowledge",
    "ImplementationKnowledge",
]


class SourceLanguage(str, Enum):
    """Supported source languages."""

    CPP = "cpp"
    HEADER = "header"
    PYTHON = "python"
    BINDING = "binding"
    UNKNOWN = "unknown"


class SourceParseStatus(str, Enum):
    """Status of static source parsing."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


def _restore_path(value: Any) -> Optional[Path]:
    """
    Restore a serialized path value.

    JSON may contain:
        - None
        - a string path
        - an already constructed Path

    Invalid/empty values are treated as None.
    """

    if value is None:
        return None

    if isinstance(value, Path):
        return value

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return None

        return Path(value)

    return None


def _restore_list(value: Any) -> List[Any]:
    """
    Safely restore a serialized list.

    Non-list values become an empty list.
    """

    if isinstance(value, list):
        return list(value)

    if value is None:
        return []

    return []


def _restore_source_language(value: Any) -> SourceLanguage:
    """
    Restore SourceLanguage from JSON.

    Accepts either an enum instance or its serialized string value.
    """

    if isinstance(value, SourceLanguage):
        return value

    if isinstance(value, str):
        try:
            return SourceLanguage(value)
        except ValueError:
            return SourceLanguage.UNKNOWN

    return SourceLanguage.UNKNOWN


def _restore_parse_status(value: Any) -> SourceParseStatus:
    """
    Restore SourceParseStatus from JSON.

    Accepts either an enum instance or its serialized string value.
    """

    if isinstance(value, SourceParseStatus):
        return value

    if isinstance(value, str):
        try:
            return SourceParseStatus(value)
        except ValueError:
            return SourceParseStatus.FAILED

    return SourceParseStatus.FAILED


@dataclass(slots=True)
class SourceMethod(BaseModel):
    """
    A method or function-like member discovered in source code.
    """

    name: str

    signature: Optional[str] = None

    return_type: Optional[str] = None

    parameters: List[str] = field(
        default_factory=list
    )

    access: Optional[str] = None

    is_static: bool = False

    is_const: bool = False

    is_virtual: bool = False

    is_override: bool = False

    is_constructor: bool = False

    is_destructor: bool = False

    line_start: Optional[int] = None

    line_end: Optional[int] = None

    source_file: Optional[Path] = None

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "SourceMethod":
        """
        Restore a SourceMethod from serialized data.

        SourceMethod contains only scalar values, lists and a Path,
        so deserialization is straightforward.
        """

        if not isinstance(data, dict):
            raise TypeError(
                "SourceMethod.from_dict() expects a dictionary"
            )

        return cls(
            name=str(
                data.get(
                    "name",
                    "",
                )
                or ""
            ),
            signature=data.get(
                "signature"
            ),
            return_type=data.get(
                "return_type"
            ),
            parameters=[
                str(item)
                for item in _restore_list(
                    data.get("parameters")
                )
            ],
            access=data.get(
                "access"
            ),
            is_static=bool(
                data.get(
                    "is_static",
                    False,
                )
            ),
            is_const=bool(
                data.get(
                    "is_const",
                    False,
                )
            ),
            is_virtual=bool(
                data.get(
                    "is_virtual",
                    False,
                )
            ),
            is_override=bool(
                data.get(
                    "is_override",
                    False,
                )
            ),
            is_constructor=bool(
                data.get(
                    "is_constructor",
                    False,
                )
            ),
            is_destructor=bool(
                data.get(
                    "is_destructor",
                    False,
                )
            ),
            line_start=data.get(
                "line_start"
            ),
            line_end=data.get(
                "line_end"
            ),
            source_file=_restore_path(
                data.get("source_file")
            ),
        )


@dataclass(slots=True)
class SourceFunction(BaseModel):
    """
    A standalone function discovered in source code.
    """

    name: str

    signature: Optional[str] = None

    return_type: Optional[str] = None

    parameters: List[str] = field(
        default_factory=list
    )

    decorators: List[str] = field(
        default_factory=list
    )

    line_start: Optional[int] = None

    line_end: Optional[int] = None

    source_file: Optional[Path] = None

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "SourceFunction":
        """
        Restore a SourceFunction from serialized data.
        """

        if not isinstance(data, dict):
            raise TypeError(
                "SourceFunction.from_dict() expects a dictionary"
            )

        return cls(
            name=str(
                data.get(
                    "name",
                    "",
                )
                or ""
            ),
            signature=data.get(
                "signature"
            ),
            return_type=data.get(
                "return_type"
            ),
            parameters=[
                str(item)
                for item in _restore_list(
                    data.get("parameters")
                )
            ],
            decorators=[
                str(item)
                for item in _restore_list(
                    data.get("decorators")
                )
            ],
            line_start=data.get(
                "line_start"
            ),
            line_end=data.get(
                "line_end"
            ),
            source_file=_restore_path(
                data.get("source_file")
            ),
        )


@dataclass(slots=True)
class SourceClass(BaseModel):
    """
    A class or struct discovered in source code.
    """

    name: str

    kind: str = "class"

    base_classes: List[str] = field(
        default_factory=list
    )

    methods: List[SourceMethod] = field(
        default_factory=list
    )

    member_variables: List[str] = field(
        default_factory=list
    )

    decorators: List[str] = field(
        default_factory=list
    )

    namespace: Optional[str] = None

    line_start: Optional[int] = None

    line_end: Optional[int] = None

    source_file: Optional[Path] = None

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "SourceClass":
        """
        Restore a SourceClass and recursively restore its methods.

        This recursive conversion is essential because the base
        BaseModel.from_dict() implementation is intentionally shallow.
        """

        if not isinstance(data, dict):
            raise TypeError(
                "SourceClass.from_dict() expects a dictionary"
            )

        methods_data = data.get(
            "methods",
            [],
        )

        methods: List[SourceMethod] = []

        for item in _restore_list(methods_data):

            if isinstance(
                item,
                SourceMethod,
            ):
                methods.append(item)
                continue

            if isinstance(
                item,
                dict,
            ):
                methods.append(
                    SourceMethod.from_dict(item)
                )

        return cls(
            name=str(
                data.get(
                    "name",
                    "",
                )
                or ""
            ),
            kind=str(
                data.get(
                    "kind",
                    "class",
                )
                or "class"
            ),
            base_classes=[
                str(item)
                for item in _restore_list(
                    data.get("base_classes")
                )
            ],
            methods=methods,
            member_variables=[
                str(item)
                for item in _restore_list(
                    data.get("member_variables")
                )
            ],
            decorators=[
                str(item)
                for item in _restore_list(
                    data.get("decorators")
                )
            ],
            namespace=data.get(
                "namespace"
            ),
            line_start=data.get(
                "line_start"
            ),
            line_end=data.get(
                "line_end"
            ),
            source_file=_restore_path(
                data.get("source_file")
            ),
        )


@dataclass(slots=True)
class SourceBinding(BaseModel):
    """
    Information extracted from a C++ Python binding file.
    """

    cpp_classes: List[str] = field(
        default_factory=list
    )

    python_classes: List[str] = field(
        default_factory=list
    )

    exposed_methods: List[str] = field(
        default_factory=list
    )

    python_module_names: List[str] = field(
        default_factory=list
    )

    includes: List[str] = field(
        default_factory=list
    )

    line_start: Optional[int] = None

    line_end: Optional[int] = None

    source_file: Optional[Path] = None

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "SourceBinding":
        """
        Restore a SourceBinding from serialized data.
        """

        if not isinstance(data, dict):
            raise TypeError(
                "SourceBinding.from_dict() expects a dictionary"
            )

        return cls(
            cpp_classes=[
                str(item)
                for item in _restore_list(
                    data.get("cpp_classes")
                )
            ],
            python_classes=[
                str(item)
                for item in _restore_list(
                    data.get("python_classes")
                )
            ],
            exposed_methods=[
                str(item)
                for item in _restore_list(
                    data.get("exposed_methods")
                )
            ],
            python_module_names=[
                str(item)
                for item in _restore_list(
                    data.get("python_module_names")
                )
            ],
            includes=[
                str(item)
                for item in _restore_list(
                    data.get("includes")
                )
            ],
            line_start=data.get(
                "line_start"
            ),
            line_end=data.get(
                "line_end"
            ),
            source_file=_restore_path(
                data.get("source_file")
            ),
        )


@dataclass(slots=True)
class SourceFileKnowledge(BaseModel):
    """
    Structured knowledge extracted from one source file.

    This is the primary result of analyzing a single source file.
    """

    path: Optional[Path] = None

    language: SourceLanguage = (
        SourceLanguage.UNKNOWN
    )

    parse_status: SourceParseStatus = (
        SourceParseStatus.FAILED
    )

    parse_errors: List[str] = field(
        default_factory=list
    )

    includes: List[str] = field(
        default_factory=list
    )

    namespaces: List[str] = field(
        default_factory=list
    )

    classes: List[SourceClass] = field(
        default_factory=list
    )

    functions: List[SourceFunction] = field(
        default_factory=list
    )

    bindings: List[SourceBinding] = field(
        default_factory=list
    )

    module_level_variables: List[str] = field(
        default_factory=list
    )

    referenced_gnuradio_classes: List[str] = field(
        default_factory=list
    )

    dependencies: List[str] = field(
        default_factory=list
    )

    line_count: int = 0

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "SourceFileKnowledge":
        """
        Restore SourceFileKnowledge recursively.

        Nested collections are converted back from dictionaries into
        their corresponding model objects.
        """

        if not isinstance(data, dict):
            raise TypeError(
                "SourceFileKnowledge.from_dict() expects a dictionary"
            )

        classes_data = data.get(
            "classes",
            [],
        )

        classes: List[SourceClass] = []

        for item in _restore_list(classes_data):

            if isinstance(
                item,
                SourceClass,
            ):
                classes.append(item)
                continue

            if isinstance(
                item,
                dict,
            ):
                classes.append(
                    SourceClass.from_dict(item)
                )

        functions_data = data.get(
            "functions",
            [],
        )

        functions: List[SourceFunction] = []

        for item in _restore_list(functions_data):

            if isinstance(
                item,
                SourceFunction,
            ):
                functions.append(item)
                continue

            if isinstance(
                item,
                dict,
            ):
                functions.append(
                    SourceFunction.from_dict(item)
                )

        bindings_data = data.get(
            "bindings",
            [],
        )

        bindings: List[SourceBinding] = []

        for item in _restore_list(bindings_data):

            if isinstance(
                item,
                SourceBinding,
            ):
                bindings.append(item)
                continue

            if isinstance(
                item,
                dict,
            ):
                bindings.append(
                    SourceBinding.from_dict(item)
                )

        return cls(
            path=_restore_path(
                data.get("path")
            ),
            language=_restore_source_language(
                data.get("language")
            ),
            parse_status=_restore_parse_status(
                data.get("parse_status")
            ),
            parse_errors=[
                str(item)
                for item in _restore_list(
                    data.get("parse_errors")
                )
            ],
            includes=[
                str(item)
                for item in _restore_list(
                    data.get("includes")
                )
            ],
            namespaces=[
                str(item)
                for item in _restore_list(
                    data.get("namespaces")
                )
            ],
            classes=classes,
            functions=functions,
            bindings=bindings,
            module_level_variables=[
                str(item)
                for item in _restore_list(
                    data.get("module_level_variables")
                )
            ],
            referenced_gnuradio_classes=[
                str(item)
                for item in _restore_list(
                    data.get(
                        "referenced_gnuradio_classes"
                    )
                )
            ],
            dependencies=[
                str(item)
                for item in _restore_list(
                    data.get("dependencies")
                )
            ],
            line_count=int(
                data.get(
                    "line_count",
                    0,
                )
                or 0
            ),
        )


@dataclass(slots=True)
class ImplementationKnowledge(BaseModel):
    """
    Complete implementation knowledge for one FlowPilot block.

    This links extracted source information back to the original
    repository/module/block identity.
    """

    block_id: Optional[str] = None

    repository: Optional[str] = None

    module: Optional[str] = None

    source_files: List[SourceFileKnowledge] = field(
        default_factory=list
    )

    analyzed_file_count: int = 0

    successful_file_count: int = 0

    failed_file_count: int = 0

    unsupported_file_count: int = 0

    classes_found: int = 0

    methods_found: int = 0

    functions_found: int = 0

    bindings_found: int = 0

    errors: List[str] = field(
        default_factory=list
    )

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "ImplementationKnowledge":
        """
        Restore ImplementationKnowledge recursively.

        The important part here is that source_files are restored
        through SourceFileKnowledge.from_dict(), which itself restores
        classes, methods, functions and bindings.
        """

        if not isinstance(data, dict):
            raise TypeError(
                "ImplementationKnowledge.from_dict() expects a dictionary"
            )

        source_files_data = data.get(
            "source_files",
            [],
        )

        source_files: List[SourceFileKnowledge] = []

        for item in _restore_list(source_files_data):

            if isinstance(
                item,
                SourceFileKnowledge,
            ):
                source_files.append(item)
                continue

            if isinstance(
                item,
                dict,
            ):
                source_files.append(
                    SourceFileKnowledge.from_dict(item)
                )

        return cls(
            block_id=data.get(
                "block_id"
            ),
            repository=data.get(
                "repository"
            ),
            module=data.get(
                "module"
            ),
            source_files=source_files,
            analyzed_file_count=int(
                data.get(
                    "analyzed_file_count",
                    0,
                )
                or 0
            ),
            successful_file_count=int(
                data.get(
                    "successful_file_count",
                    0,
                )
                or 0
            ),
            failed_file_count=int(
                data.get(
                    "failed_file_count",
                    0,
                )
                or 0
            ),
            unsupported_file_count=int(
                data.get(
                    "unsupported_file_count",
                    0,
                )
                or 0
            ),
            classes_found=int(
                data.get(
                    "classes_found",
                    0,
                )
                or 0
            ),
            methods_found=int(
                data.get(
                    "methods_found",
                    0,
                )
                or 0
            ),
            functions_found=int(
                data.get(
                    "functions_found",
                    0,
                )
                or 0
            ),
            bindings_found=int(
                data.get(
                    "bindings_found",
                    0,
                )
                or 0
            ),
            errors=[
                str(item)
                for item in _restore_list(
                    data.get("errors")
                )
            ],
        )

    def recompute_statistics(self) -> None:
        """
        Recalculate aggregate statistics from source_files.

        Statistics are derived from the restored model objects rather
        than trusting potentially stale serialized counters.
        """

        self.analyzed_file_count = len(
            self.source_files
        )

        self.successful_file_count = sum(
            1
            for source_file in self.source_files
            if source_file.parse_status
            in (
                SourceParseStatus.SUCCESS,
                SourceParseStatus.PARTIAL,
            )
        )

        self.failed_file_count = sum(
            1
            for source_file in self.source_files
            if source_file.parse_status
            == SourceParseStatus.FAILED
        )

        self.unsupported_file_count = sum(
            1
            for source_file in self.source_files
            if source_file.parse_status
            == SourceParseStatus.UNSUPPORTED
        )

        self.classes_found = sum(
            len(source_file.classes)
            for source_file in self.source_files
        )

        self.methods_found = sum(
            len(source_class.methods)
            for source_file in self.source_files
            for source_class in source_file.classes
        )

        self.functions_found = sum(
            len(source_file.functions)
            for source_file in self.source_files
        )

        self.bindings_found = sum(
            len(source_file.bindings)
            for source_file in self.source_files
        )

    def summary(self) -> Dict[str, Any]:
        """
        Return a compact summary suitable for logging/testing.
        """

        return {
            "block_id": self.block_id,
            "repository": self.repository,
            "module": self.module,
            "analyzed_files": self.analyzed_file_count,
            "successful_files": self.successful_file_count,
            "failed_files": self.failed_file_count,
            "unsupported_files": self.unsupported_file_count,
            "classes": self.classes_found,
            "methods": self.methods_found,
            "functions": self.functions_found,
            "bindings": self.bindings_found,
            "errors": len(self.errors),
        }