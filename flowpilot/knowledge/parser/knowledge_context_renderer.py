"""
Knowledge Context Renderer.

Converts a validated KnowledgeContext into deterministic,
human-readable text suitable for downstream answer generation.
"""

from __future__ import annotations

from typing import Any, Iterable, List, Optional

from flowpilot.knowledge.parser.knowledge_context_builder import (
    KnowledgeContext,
)


class KnowledgeContextRenderer:
    """
    Render KnowledgeContext into structured text.

    The renderer does not modify the context, graph, store, or
    retrieved knowledge.
    """

    def __init__(
        self,
        include_source_attributes: bool = True,
        include_references: bool = True,
        include_methods: bool = True,
        include_functions: bool = True,
        include_parameters: bool = True,
    ) -> None:

        self.include_source_attributes = (
            include_source_attributes
        )

        self.include_references = (
            include_references
        )

        self.include_methods = (
            include_methods
        )

        self.include_functions = (
            include_functions
        )

        self.include_parameters = (
            include_parameters
        )

    # ========================================================================
    # Public API
    # ========================================================================

    def render(
        self,
        context: KnowledgeContext,
    ) -> str:
        """
        Render a KnowledgeContext into deterministic text.
        """

        if context is None:
            return (
                "# FLOWPILOT KNOWLEDGE CONTEXT\n\n"
                "ERROR: Knowledge context is missing."
            )

        sections: List[str] = []

        sections.append(
            self._render_header(
                context
            )
        )

        sections.append(
            self._render_summary(
                context
            )
        )

        sections.append(
            self._render_source_files(
                context
            )
        )

        sections.append(
            self._render_classes(
                context
            )
        )

        if self.include_methods:
            sections.append(
                self._render_methods(
                    context
                )
            )

        if self.include_functions:
            sections.append(
                self._render_functions(
                    context
                )
            )

        if self.include_parameters:
            sections.append(
                self._render_parameters(
                    context
                )
            )

        sections.append(
            self._render_bindings(
                context
            )
        )

        sections.append(
            self._render_inheritance(
                context
            )
        )

        if self.include_references:
            sections.append(
                self._render_references(
                    context
                )
            )

        sections.append(
            self._render_errors(
                context
            )
        )

        return "\n\n".join(
            section
            for section in sections
            if section.strip()
        )

    def render_compact(
        self,
        context: KnowledgeContext,
    ) -> str:
        """
        Render a compact version suitable for prompt context.
        """

        if context is None:
            return (
                "# FLOWPILOT KNOWLEDGE CONTEXT\n\n"
                "ERROR: Knowledge context is missing."
            )

        lines: List[str] = []

        lines.append(
            "# FLOWPILOT KNOWLEDGE CONTEXT"
        )

        lines.append(
            f"Query: {self._value(context, 'query')}"
        )

        lines.append(
            f"Block ID: {self._value(context, 'block_id')}"
        )

        lines.append(
            f"Block Found: {self._bool_value(context, 'block_found')}"
        )

        lines.append(
            f"Source Files: {self._count(context, 'source_files')}"
        )

        lines.append(
            f"Classes: {self._count(context, 'classes')}"
        )

        lines.append(
            f"Methods: {self._count(context, 'methods')}"
        )

        lines.append(
            f"Functions: {self._count(context, 'functions')}"
        )

        lines.append(
            f"Bindings: {self._count(context, 'bindings')}"
        )

        lines.append(
            f"Parameters: {self._count(context, 'parameters')}"
        )

        lines.append(
            f"Inherited Classes: "
            f"{self._count(context, 'inherited_classes')}"
        )

        lines.append(
            f"References: {self._count(context, 'references')}"
        )

        return "\n".join(
            lines
        )

    # ========================================================================
    # Header
    # ========================================================================

    @staticmethod
    def _render_header(
        context: KnowledgeContext,
    ) -> str:

        query = KnowledgeContextRenderer._value(
            context,
            "query",
        )

        block_id = KnowledgeContextRenderer._value(
            context,
            "block_id",
        )

        block_found = KnowledgeContextRenderer._bool_value(
            context,
            "block_found",
        )

        return "\n".join(
            [
                "# FLOWPILOT KNOWLEDGE CONTEXT",
                "",
                f"Query: {query}",
                f"Block ID: {block_id}",
                f"Block Found: {block_found}",
            ]
        )

    # ========================================================================
    # Summary
    # ========================================================================

    @staticmethod
    def _render_summary(
        context: KnowledgeContext,
    ) -> str:

        lines = [
            "## SUMMARY",
            "",
            f"Source files       : "
            f"{KnowledgeContextRenderer._count(context, 'source_files')}",
            f"Classes            : "
            f"{KnowledgeContextRenderer._count(context, 'classes')}",
            f"Methods            : "
            f"{KnowledgeContextRenderer._count(context, 'methods')}",
            f"Functions          : "
            f"{KnowledgeContextRenderer._count(context, 'functions')}",
            f"Bindings           : "
            f"{KnowledgeContextRenderer._count(context, 'bindings')}",
            f"Parameters         : "
            f"{KnowledgeContextRenderer._count(context, 'parameters')}",
            f"Inherited classes  : "
            f"{KnowledgeContextRenderer._count(context, 'inherited_classes')}",
            f"References         : "
            f"{KnowledgeContextRenderer._count(context, 'references')}",
            f"Errors             : "
            f"{KnowledgeContextRenderer._count(context, 'errors')}",
        ]

        return "\n".join(
            lines
        )

    # ========================================================================
    # Source files
    # ========================================================================

    def _render_source_files(
        self,
        context: KnowledgeContext,
    ) -> str:

        files = getattr(
            context,
            "source_files",
            [],
        )

        lines = [
            "## SOURCE FILES",
            "",
        ]

        if not files:
            lines.append(
                "None."
            )
            return "\n".join(
                lines
            )

        for index, source_file in enumerate(
            files,
            start=1,
        ):

            name = self._item_name(
                source_file
            )

            item_type = self._item_type(
                source_file
            )

            source_path = self._item_source_file(
                source_file
            )

            lines.append(
                f"{index}. {name}"
            )

            if item_type:
                lines.append(
                    f"   type: {item_type}"
                )

            if source_path:
                lines.append(
                    f"   source_file: {source_path}"
                )

            if self.include_source_attributes:
                attributes = self._item_attributes(
                    source_file
                )

                if attributes:
                    lines.append(
                        f"   attributes: "
                        f"{self._format_value(attributes)}"
                    )

        return "\n".join(
            lines
        )

    # ========================================================================
    # Classes
    # ========================================================================

    def _render_classes(
        self,
        context: KnowledgeContext,
    ) -> str:

        classes = getattr(
            context,
            "classes",
            [],
        )

        lines = [
            "## CLASSES",
            "",
        ]

        if not classes:
            lines.append(
                "None."
            )
            return "\n".join(
                lines
            )

        seen = set()

        number = 0

        for item in classes:

            item_id = self._item_id(
                item
            )

            if item_id in seen:
                continue

            if item_id:
                seen.add(
                    item_id
                )

            number += 1

            name = self._item_name(
                item
            )

            lines.append(
                f"{number}. {name}"
            )

            item_type = self._item_type(
                item
            )

            if item_type:
                lines.append(
                    f"   type: {item_type}"
                )

            source_file = self._item_source_file(
                item
            )

            if source_file:
                lines.append(
                    f"   source_file: {source_file}"
                )

            item_id = self._item_id(
                item
            )

            if item_id:
                lines.append(
                    f"   id: {item_id}"
                )

        return "\n".join(
            lines
        )

    # ========================================================================
    # Methods
    # ========================================================================

    def _render_methods(
        self,
        context: KnowledgeContext,
    ) -> str:

        methods = getattr(
            context,
            "methods",
            [],
        )

        lines = [
            "## METHODS",
            "",
        ]

        if not methods:
            lines.append(
                "None."
            )
            return "\n".join(
                lines
            )

        seen = set()

        for index, method in enumerate(
            self._unique_items(methods),
            start=1,
        ):

            name = self._item_name(
                method
            )

            lines.append(
                f"{index}. {name}"
            )

            signature = self._item_attribute(
                method,
                "signature",
            )

            if signature:
                lines.append(
                    f"   signature: {signature}"
                )

            return_type = self._item_attribute(
                method,
                "return_type",
            )

            if return_type:
                lines.append(
                    f"   return_type: {return_type}"
                )

            source_file = self._item_source_file(
                method
            )

            if source_file:
                lines.append(
                    f"   source_file: {source_file}"
                )

        return "\n".join(
            lines
        )

    # ========================================================================
    # Functions
    # ========================================================================

    def _render_functions(
        self,
        context: KnowledgeContext,
    ) -> str:

        functions = getattr(
            context,
            "functions",
            [],
        )

        lines = [
            "## FUNCTIONS",
            "",
        ]

        if not functions:
            lines.append(
                "None."
            )
            return "\n".join(
                lines
            )

        for index, function in enumerate(
            self._unique_items(functions),
            start=1,
        ):

            name = self._item_name(
                function
            )

            lines.append(
                f"{index}. {name}"
            )

            signature = self._item_attribute(
                function,
                "signature",
            )

            if signature:
                lines.append(
                    f"   signature: {signature}"
                )

            return_type = self._item_attribute(
                function,
                "return_type",
            )

            if return_type:
                lines.append(
                    f"   return_type: {return_type}"
                )

            source_file = self._item_source_file(
                function
            )

            if source_file:
                lines.append(
                    f"   source_file: {source_file}"
                )

        return "\n".join(
            lines
        )

    # ========================================================================
    # Parameters
    # ========================================================================

    def _render_parameters(
        self,
        context: KnowledgeContext,
    ) -> str:

        parameters = getattr(
            context,
            "parameters",
            [],
        )

        lines = [
            "## PARAMETERS",
            "",
        ]

        if not parameters:
            lines.append(
                "None."
            )
            return "\n".join(
                lines
            )

        for index, parameter in enumerate(
            self._unique_items(parameters),
            start=1,
        ):

            name = self._item_name(
                parameter
            )

            lines.append(
                f"{index}. {name}"
            )

            parameter_type = self._item_attribute(
                parameter,
                "type",
            )

            if not parameter_type:
                parameter_type = self._item_attribute(
                    parameter,
                    "parameter_type",
                )

            if parameter_type:
                lines.append(
                    f"   type: {parameter_type}"
                )

            default = self._item_attribute(
                parameter,
                "default",
            )

            if default is not None:
                lines.append(
                    f"   default: {default}"
                )

        return "\n".join(
            lines
        )

    # ========================================================================
    # Bindings
    # ========================================================================

    def _render_bindings(
        self,
        context: KnowledgeContext,
    ) -> str:

        bindings = getattr(
            context,
            "bindings",
            [],
        )

        lines = [
            "## BINDINGS",
            "",
        ]

        if not bindings:
            lines.append(
                "None."
            )
            return "\n".join(
                lines
            )

        for index, binding in enumerate(
            self._unique_items(bindings),
            start=1,
        ):

            name = self._item_name(
                binding
            )

            lines.append(
                f"{index}. {name}"
            )

            source_file = self._item_source_file(
                binding
            )

            if source_file:
                lines.append(
                    f"   source_file: {source_file}"
                )

            attributes = self._item_attributes(
                binding
            )

            if attributes:
                lines.append(
                    f"   attributes: "
                    f"{self._format_value(attributes)}"
                )

        return "\n".join(
            lines
        )

    # ========================================================================
    # Inheritance
    # ========================================================================

    def _render_inheritance(
        self,
        context: KnowledgeContext,
    ) -> str:

        inherited = getattr(
            context,
            "inherited_classes",
            [],
        )

        lines = [
            "## INHERITANCE",
            "",
        ]

        if not inherited:
            lines.append(
                "None."
            )
            return "\n".join(
                lines
            )

        for index, item in enumerate(
            self._unique_items(inherited),
            start=1,
        ):

            name = self._item_name(
                item
            )

            lines.append(
                f"{index}. {name}"
            )

            item_id = self._item_id(
                item
            )

            if item_id:
                lines.append(
                    f"   id: {item_id}"
                )

        return "\n".join(
            lines
        )

    # ========================================================================
    # References
    # ========================================================================

    def _render_references(
        self,
        context: KnowledgeContext,
    ) -> str:

        references = getattr(
            context,
            "references",
            [],
        )

        lines = [
            "## REFERENCES",
            "",
        ]

        if not references:
            lines.append(
                "None."
            )
            return "\n".join(
                lines
            )

        for index, reference in enumerate(
            references,
            start=1,
        ):

            source = getattr(
                reference,
                "source",
                "",
            )

            relationship = getattr(
                reference,
                "relationship",
                "",
            )

            target = getattr(
                reference,
                "target",
                "",
            )

            lines.append(
                f"{index}. "
                f"{source} "
                f"--[{relationship}]--> "
                f"{target}"
            )

            metadata = getattr(
                reference,
                "metadata",
                {},
            )

            if metadata:
                lines.append(
                    f"   metadata: "
                    f"{self._format_value(metadata)}"
                )

        return "\n".join(
            lines
        )

    # ========================================================================
    # Errors
    # ========================================================================

    @staticmethod
    def _render_errors(
        context: KnowledgeContext,
    ) -> str:

        errors = getattr(
            context,
            "errors",
            [],
        )

        lines = [
            "## ERRORS",
            "",
        ]

        if not errors:
            lines.append(
                "0"
            )
            return "\n".join(
                lines
            )

        for index, error in enumerate(
            errors,
            start=1,
        ):

            lines.append(
                f"{index}. {error}"
            )

        return "\n".join(
            lines
        )

    # ========================================================================
    # Generic helpers
    # ========================================================================

    @staticmethod
    def _value(
        context: Any,
        field_name: str,
    ) -> str:

        value = getattr(
            context,
            field_name,
            "",
        )

        if value is None:
            return ""

        return str(
            value
        )

    @staticmethod
    def _bool_value(
        context: Any,
        field_name: str,
    ) -> str:

        return str(
            bool(
                getattr(
                    context,
                    field_name,
                    False,
                )
            )
        )

    @staticmethod
    def _count(
        context: Any,
        field_name: str,
    ) -> int:

        value = getattr(
            context,
            field_name,
            [],
        )

        if value is None:
            return 0

        try:
            return len(
                value
            )
        except TypeError:
            return 0

    @staticmethod
    def _item_id(
        item: Any,
    ) -> str:

        if item is None:
            return ""

        if isinstance(
            item,
            dict,
        ):
            value = item.get(
                "id",
                "",
            )
        else:
            value = getattr(
                item,
                "id",
                "",
            )

        if value is None:
            return ""

        return str(
            value
        )

    @staticmethod
    def _item_name(
        item: Any,
    ) -> str:

        if item is None:
            return ""

        if isinstance(
            item,
            dict,
        ):
            value = item.get(
                "name",
                item.get(
                    "id",
                    "",
                ),
            )
        else:
            value = getattr(
                item,
                "name",
                None,
            )

            if value is None:
                value = getattr(
                    item,
                    "id",
                    "",
                )

        if value is None:
            return ""

        return str(
            value
        )

    @staticmethod
    def _item_type(
        item: Any,
    ) -> str:

        if item is None:
            return ""

        if isinstance(
            item,
            dict,
        ):
            value = item.get(
                "node_type",
                item.get(
                    "type",
                    "",
                ),
            )
        else:
            value = getattr(
                item,
                "node_type",
                None,
            )

            if value is None:
                value = getattr(
                    item,
                    "type",
                    "",
                )

        if value is None:
            return ""

        value = getattr(
            value,
            "value",
            value,
        )

        return str(
            value
        )

    @staticmethod
    def _item_source_file(
        item: Any,
    ) -> str:

        if item is None:
            return ""

        if isinstance(
            item,
            dict,
        ):
            value = item.get(
                "source_file",
                "",
            )
        else:
            value = getattr(
                item,
                "source_file",
                "",
            )

        if value is None:
            return ""

        return str(
            value
        )

    @staticmethod
    def _item_attributes(
        item: Any,
    ) -> dict:

        if item is None:
            return {}

        if isinstance(
            item,
            dict,
        ):
            value = item.get(
                "attributes",
                {},
            )
        else:
            value = getattr(
                item,
                "attributes",
                {},
            )

        if not isinstance(
            value,
            dict,
        ):
            return {}

        return value

    @staticmethod
    def _item_attribute(
        item: Any,
        name: str,
    ) -> Any:

        if item is None:
            return None

        if isinstance(
            item,
            dict,
        ):
            return item.get(
                name
            )

        return getattr(
            item,
            name,
            None,
        )

    @staticmethod
    def _unique_items(
        items: Iterable[Any],
    ) -> List[Any]:

        result: List[Any] = []

        seen = set()

        for item in items:

            item_id = KnowledgeContextRenderer._item_id(
                item
            )

            if item_id:

                if item_id in seen:
                    continue

                seen.add(
                    item_id
                )

            result.append(
                item
            )

        return result

    @staticmethod
    def _format_value(
        value: Any,
    ) -> str:

        if isinstance(
            value,
            dict,
        ):

            parts = []

            for key in sorted(
                value.keys(),
                key=lambda x: str(x),
            ):

                parts.append(
                    f"{key}={value[key]}"
                )

            return (
                "{"
                + ", ".join(parts)
                + "}"
            )

        if isinstance(
            value,
            (list, tuple),
        ):

            return (
                "["
                + ", ".join(
                    str(x)
                    for x in value
                )
                + "]"
            )

        return str(
            value
        )


# ============================================================================
# Convenience functions
# ============================================================================


def render_knowledge_context(
    context: KnowledgeContext,
) -> str:

    return KnowledgeContextRenderer().render(
        context
    )


def render_knowledge_context_compact(
    context: KnowledgeContext,
) -> str:

    return KnowledgeContextRenderer().render_compact(
        context
    )


__all__ = [
    "KnowledgeContextRenderer",
    "render_knowledge_context",
    "render_knowledge_context_compact",
]