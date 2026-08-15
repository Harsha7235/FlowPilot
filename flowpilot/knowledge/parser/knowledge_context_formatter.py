"""
Knowledge Context Formatter.

Converts KnowledgeContext objects into deterministic, readable text
for downstream FlowPilot components.

This module is formatting-only.
It does not modify the knowledge graph, retriever, or stored knowledge.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Optional

from flowpilot.knowledge.parser.knowledge_context_builder import (
    ContextReference,
    KnowledgeContext,
    KnowledgeContextBuilder,
)


# ============================================================================
# Formatting result
# ============================================================================


@dataclass
class KnowledgeContextFormatResult:
    """Result produced by the context formatter."""

    success: bool = False
    query: str = ""
    block_id: Optional[str] = None
    text: str = ""
    errors: List[str] = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []

    def summary(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "query": self.query,
            "block_id": self.block_id,
            "characters": len(self.text),
            "lines": (
                len(self.text.splitlines())
                if self.text
                else 0
            ),
            "errors": len(self.errors),
        }


# ============================================================================
# Formatter
# ============================================================================


class KnowledgeContextFormatter:
    """
    Formats KnowledgeContext into deterministic text.

    The output is designed to be consumed by later FlowPilot
    reasoning/answer components.
    """

    def __init__(
        self,
        builder: Optional[
            KnowledgeContextBuilder
        ] = None,
        *,
        include_files: bool = True,
        include_classes: bool = True,
        include_methods: bool = True,
        include_functions: bool = True,
        include_bindings: bool = True,
        include_parameters: bool = True,
        include_inherited_classes: bool = True,
        include_references: bool = True,
        max_items_per_section: int = 5000,
    ) -> None:

        self.builder = (
            builder
            if builder is not None
            else KnowledgeContextBuilder()
        )

        self.include_files = include_files
        self.include_classes = include_classes
        self.include_methods = include_methods
        self.include_functions = include_functions
        self.include_bindings = include_bindings
        self.include_parameters = include_parameters
        self.include_inherited_classes = (
            include_inherited_classes
        )
        self.include_references = (
            include_references
        )
        self.max_items_per_section = (
            max_items_per_section
        )

    # ========================================================================
    # Public API
    # ========================================================================

    def format(
        self,
        context: KnowledgeContext,
    ) -> KnowledgeContextFormatResult:
        """
        Format an already-built KnowledgeContext.
        """

        errors: List[str] = []

        if context is None:
            return KnowledgeContextFormatResult(
                success=False,
                errors=[
                    "Knowledge context is required."
                ],
            )

        try:
            text = self._format_context(
                context
            )

            return KnowledgeContextFormatResult(
                success=not bool(
                    errors
                ),
                query=context.query,
                block_id=context.block_id,
                text=text,
                errors=errors,
            )

        except Exception as exc:
            errors.append(
                "Context formatting failed: "
                f"{type(exc).__name__}: {exc}"
            )

            return KnowledgeContextFormatResult(
                success=False,
                query=context.query,
                block_id=context.block_id,
                text="",
                errors=errors,
            )

    def build_and_format(
        self,
        query: str,
    ) -> KnowledgeContextFormatResult:
        """
        Build a KnowledgeContext and immediately format it.
        """

        build_result = self.builder.build(
            query
        )

        if not build_result.success:
            errors = list(
                build_result.errors
            )

            if (
                not errors
                and build_result.context is not None
            ):
                errors.extend(
                    build_result.context.errors
                )

            return KnowledgeContextFormatResult(
                success=False,
                query=query,
                block_id=(
                    build_result.context.block_id
                    if build_result.context
                    else None
                ),
                text="",
                errors=errors,
            )

        return self.format(
            build_result.context
        )

    # ========================================================================
    # Main formatter
    # ========================================================================

    def _format_context(
        self,
        context: KnowledgeContext,
    ) -> str:

        lines: List[str] = []

        lines.append(
            "======================================================================"
        )
        lines.append(
            "FLOWPILOT KNOWLEDGE CONTEXT"
        )
        lines.append(
            "======================================================================"
        )

        lines.append(
            f"Query: {context.query}"
        )

        lines.append(
            f"Block ID: {context.block_id or 'unknown'}"
        )

        lines.append(
            f"Block Found: {context.block_found}"
        )

        lines.append("")

        self._append_summary(
            lines,
            context,
        )

        if self.include_files:
            self._append_section(
                lines,
                "SOURCE FILES",
                context.source_files,
            )

        if self.include_classes:
            self._append_section(
                lines,
                "CLASSES",
                context.classes,
            )

        if self.include_methods:
            self._append_section(
                lines,
                "METHODS",
                context.methods,
            )

        if self.include_functions:
            self._append_section(
                lines,
                "FUNCTIONS",
                context.functions,
            )

        if self.include_bindings:
            self._append_section(
                lines,
                "BINDINGS",
                context.bindings,
            )

        if self.include_parameters:
            self._append_section(
                lines,
                "PARAMETERS",
                context.parameters,
            )

        if self.include_inherited_classes:
            self._append_section(
                lines,
                "INHERITED CLASSES",
                context.inherited_classes,
            )

        if self.include_references:
            self._append_references(
                lines,
                context.references,
            )

        if context.errors:
            self._append_errors(
                lines,
                context.errors,
            )

        lines.append("")
        lines.append(
            "======================================================================"
        )
        lines.append(
            "END KNOWLEDGE CONTEXT"
        )
        lines.append(
            "======================================================================"
        )

        return "\n".join(
            lines
        )

    # ========================================================================
    # Summary
    # ========================================================================

    def _append_summary(
        self,
        lines: List[str],
        context: KnowledgeContext,
    ) -> None:

        lines.append(
            "SUMMARY"
        )
        lines.append(
            "-------"
        )

        lines.append(
            f"Source files       : "
            f"{len(context.source_files)}"
        )

        lines.append(
            f"Classes            : "
            f"{len(context.classes)}"
        )

        lines.append(
            f"Methods            : "
            f"{len(context.methods)}"
        )

        lines.append(
            f"Functions          : "
            f"{len(context.functions)}"
        )

        lines.append(
            f"Bindings           : "
            f"{len(context.bindings)}"
        )

        lines.append(
            f"Parameters         : "
            f"{len(context.parameters)}"
        )

        lines.append(
            f"Inherited classes  : "
            f"{len(context.inherited_classes)}"
        )

        lines.append(
            f"References         : "
            f"{len(context.references)}"
        )

        lines.append(
            f"Errors             : "
            f"{len(context.errors)}"
        )

        lines.append("")

    # ========================================================================
    # Generic sections
    # ========================================================================

    def _append_section(
        self,
        lines: List[str],
        title: str,
        items: Iterable[Any],
    ) -> None:

        values = list(
            items
        )[: self.max_items_per_section]

        lines.append(
            title
        )

        lines.append(
            "-" * len(title)
        )

        if not values:
            lines.append(
                "(none)"
            )
            lines.append("")
            return

        for index, item in enumerate(
            values,
            start=1,
        ):
            lines.extend(
                self._format_item(
                    index,
                    item,
                )
            )

        lines.append("")

    # ========================================================================
    # References
    # ========================================================================

    def _append_references(
        self,
        lines: List[str],
        references: Iterable[
            ContextReference
        ],
    ) -> None:

        values = list(
            references
        )[: self.max_items_per_section]

        title = "REFERENCES"

        lines.append(
            title
        )

        lines.append(
            "-" * len(title)
        )

        if not values:
            lines.append(
                "(none)"
            )
            lines.append("")
            return

        for index, reference in enumerate(
            values,
            start=1,
        ):
            lines.append(
                f"{index}. "
                f"{reference.source}"
            )

            lines.append(
                f"   relationship: "
                f"{reference.relationship}"
            )

            lines.append(
                f"   target: "
                f"{reference.target}"
            )

            metadata = (
                reference.metadata
            )

            if metadata:
                lines.append(
                    "   metadata: "
                    + self._format_metadata(
                        metadata
                    )
                )

        lines.append("")

    # ========================================================================
    # Errors
    # ========================================================================

    def _append_errors(
        self,
        lines: List[str],
        errors: Iterable[str],
    ) -> None:

        title = "ERRORS"

        lines.append(
            title
        )

        lines.append(
            "-" * len(title)
        )

        for index, error in enumerate(
            errors,
            start=1,
        ):
            lines.append(
                f"{index}. {error}"
            )

        lines.append("")

    # ========================================================================
    # Item formatting
    # ========================================================================

    def _format_item(
        self,
        index: int,
        item: Any,
    ) -> List[str]:

        lines: List[str] = []

        name = self._value(
            item,
            "name",
            "",
        )

        item_id = self._value(
            item,
            "id",
            "",
        )

        node_type = self._value(
            item,
            "node_type",
            "",
        )

        if node_type:
            node_type = getattr(
                node_type,
                "value",
                node_type,
            )

        source_file = self._value(
            item,
            "source_file",
            None,
        )

        lines.append(
            f"{index}. "
            f"{name or item_id or '(unnamed)'}"
        )

        if node_type:
            lines.append(
                f"   type: {node_type}"
            )

        if item_id:
            lines.append(
                f"   id: {item_id}"
            )

        if source_file:
            lines.append(
                f"   source_file: "
                f"{source_file}"
            )

        self._append_optional_field(
            lines,
            item,
            "kind",
        )

        self._append_optional_field(
            lines,
            item,
            "signature",
        )

        self._append_optional_field(
            lines,
            item,
            "return_type",
        )

        self._append_optional_field(
            lines,
            item,
            "access",
        )

        self._append_optional_field(
            lines,
            item,
            "namespace",
        )

        self._append_optional_field(
            lines,
            item,
            "line_start",
        )

        self._append_optional_field(
            lines,
            item,
            "line_end",
        )

        self._append_list_field(
            lines,
            item,
            "parameters",
        )

        self._append_list_field(
            lines,
            item,
            "base_classes",
        )

        self._append_list_field(
            lines,
            item,
            "decorators",
        )

        self._append_list_field(
            lines,
            item,
            "member_variables",
        )

        self._append_bool_field(
            lines,
            item,
            "is_static",
        )

        self._append_bool_field(
            lines,
            item,
            "is_const",
        )

        self._append_bool_field(
            lines,
            item,
            "is_virtual",
        )

        self._append_bool_field(
            lines,
            item,
            "is_override",
        )

        self._append_bool_field(
            lines,
            item,
            "is_constructor",
        )

        self._append_bool_field(
            lines,
            item,
            "is_destructor",
        )

        attributes = self._value(
            item,
            "attributes",
            None,
        )

        if isinstance(
            attributes,
            dict,
        ) and attributes:
            lines.append(
                "   attributes: "
                + self._format_metadata(
                    attributes
                )
            )

        return lines

    # ========================================================================
    # Field helpers
    # ========================================================================

    def _append_optional_field(
        self,
        lines: List[str],
        item: Any,
        field_name: str,
    ) -> None:

        value = self._value(
            item,
            field_name,
            None,
        )

        if value is None:
            return

        if value == "":
            return

        lines.append(
            f"   {field_name}: "
            f"{value}"
        )

    def _append_list_field(
        self,
        lines: List[str],
        item: Any,
        field_name: str,
    ) -> None:

        value = self._value(
            item,
            field_name,
            None,
        )

        if not value:
            return

        if isinstance(
            value,
            (list, tuple, set),
        ):
            rendered = ", ".join(
                str(x)
                for x in value
            )
        else:
            rendered = str(
                value
            )

        lines.append(
            f"   {field_name}: "
            f"{rendered}"
        )

    def _append_bool_field(
        self,
        lines: List[str],
        item: Any,
        field_name: str,
    ) -> None:

        value = self._value(
            item,
            field_name,
            None,
        )

        if value is True:
            lines.append(
                f"   {field_name}: true"
            )

    @staticmethod
    def _value(
        item: Any,
        field_name: str,
        default: Any = None,
    ) -> Any:

        if item is None:
            return default

        if isinstance(
            item,
            dict,
        ):
            return item.get(
                field_name,
                default,
            )

        return getattr(
            item,
            field_name,
            default,
        )

    @staticmethod
    def _format_metadata(
        metadata: dict[str, Any],
    ) -> str:

        parts: List[str] = []

        for key in sorted(
            metadata.keys(),
            key=str,
        ):
            value = metadata[key]

            parts.append(
                f"{key}={value}"
            )

        return (
            "{"
            + ", ".join(parts)
            + "}"
        )


# ============================================================================
# Convenience function
# ============================================================================


def format_knowledge_context(
    context: KnowledgeContext,
) -> KnowledgeContextFormatResult:

    return KnowledgeContextFormatter().format(
        context
    )


def build_and_format_knowledge_context(
    query: str,
) -> KnowledgeContextFormatResult:

    return KnowledgeContextFormatter().build_and_format(
        query
    )


__all__ = [
    "KnowledgeContextFormatResult",
    "KnowledgeContextFormatter",
    "format_knowledge_context",
    "build_and_format_knowledge_context",
]