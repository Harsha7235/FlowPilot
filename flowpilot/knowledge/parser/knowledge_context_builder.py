"""
Knowledge Context Builder.

Converts KnowledgeRetriever results into a stable context object
for the next FlowPilot knowledge/answer layer.

This module does not modify the knowledge graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from flowpilot.knowledge.parser.knowledge_retriever import (
    KnowledgeRetriever,
)


# ============================================================================
# Context reference
# ============================================================================


@dataclass
class ContextReference:
    """A reference discovered during knowledge retrieval."""

    source: str = ""
    relationship: str = ""
    target: str = ""
    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "relationship": self.relationship,
            "target": self.target,
            "metadata": dict(self.metadata),
        }


# ============================================================================
# Knowledge context
# ============================================================================


@dataclass
class KnowledgeContext:
    """Complete structured knowledge context for one query."""

    query: str = ""

    block_id: Optional[str] = None

    block_found: bool = False

    source_files: List[Any] = field(
        default_factory=list
    )

    classes: List[Any] = field(
        default_factory=list
    )

    methods: List[Any] = field(
        default_factory=list
    )

    functions: List[Any] = field(
        default_factory=list
    )

    bindings: List[Any] = field(
        default_factory=list
    )

    parameters: List[Any] = field(
        default_factory=list
    )

    inherited_classes: List[Any] = field(
        default_factory=list
    )

    references: List[ContextReference] = field(
        default_factory=list
    )

    errors: List[str] = field(
        default_factory=list
    )

    def summary(self) -> Dict[str, Any]:
        return {
            "success": (
                self.block_found
                and not self.errors
            ),
            "query": self.query,
            "block_id": self.block_id,
            "block_found": self.block_found,
            "source_files": len(
                self.source_files
            ),
            "classes": len(
                self.classes
            ),
            "methods": len(
                self.methods
            ),
            "functions": len(
                self.functions
            ),
            "bindings": len(
                self.bindings
            ),
            "parameters": len(
                self.parameters
            ),
            "inherited_classes": len(
                self.inherited_classes
            ),
            "references": len(
                self.references
            ),
            "errors": len(
                self.errors
            ),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "block_id": self.block_id,
            "block_found": self.block_found,
            "source_files": [
                KnowledgeContextBuilder._serialize(
                    item
                )
                for item in self.source_files
            ],
            "classes": [
                KnowledgeContextBuilder._serialize(
                    item
                )
                for item in self.classes
            ],
            "methods": [
                KnowledgeContextBuilder._serialize(
                    item
                )
                for item in self.methods
            ],
            "functions": [
                KnowledgeContextBuilder._serialize(
                    item
                )
                for item in self.functions
            ],
            "bindings": [
                KnowledgeContextBuilder._serialize(
                    item
                )
                for item in self.bindings
            ],
            "parameters": [
                KnowledgeContextBuilder._serialize(
                    item
                )
                for item in self.parameters
            ],
            "inherited_classes": [
                KnowledgeContextBuilder._serialize(
                    item
                )
                for item in self.inherited_classes
            ],
            "references": [
                item.to_dict()
                for item in self.references
            ],
            "errors": list(
                self.errors
            ),
        }


# ============================================================================
# Build result
# ============================================================================


@dataclass
class KnowledgeContextBuildResult:
    """Result of context construction."""

    success: bool = False

    context: Optional[
        KnowledgeContext
    ] = None

    errors: List[str] = field(
        default_factory=list
    )

    def summary(self) -> Dict[str, Any]:
        if self.context is None:
            return {
                "success": self.success,
                "query": "",
                "block_id": None,
                "block_found": False,
                "source_files": 0,
                "classes": 0,
                "methods": 0,
                "functions": 0,
                "bindings": 0,
                "parameters": 0,
                "inherited_classes": 0,
                "references": 0,
                "errors": len(
                    self.errors
                ),
            }

        result = self.context.summary()
        result["success"] = self.success
        return result


# ============================================================================
# Builder
# ============================================================================


class KnowledgeContextBuilder:
    """
    Builds structured context from KnowledgeRetriever results.
    """

    def __init__(
        self,
        retriever: Optional[
            KnowledgeRetriever
        ] = None,
        *,
        max_source_files: int = 500,
        max_classes: int = 5000,
        max_methods: int = 10000,
        max_functions: int = 10000,
        max_bindings: int = 5000,
        max_parameters: int = 20000,
        max_inherited_classes: int = 5000,
        max_references: int = 10000,
    ) -> None:

        self.retriever = (
            retriever
            if retriever is not None
            else KnowledgeRetriever()
        )

        self.max_source_files = (
            max_source_files
        )

        self.max_classes = (
            max_classes
        )

        self.max_methods = (
            max_methods
        )

        self.max_functions = (
            max_functions
        )

        self.max_bindings = (
            max_bindings
        )

        self.max_parameters = (
            max_parameters
        )

        self.max_inherited_classes = (
            max_inherited_classes
        )

        self.max_references = (
            max_references
        )

    # ========================================================================
    # Public build API
    # ========================================================================

    def build(
        self,
        query: str,
    ) -> KnowledgeContextBuildResult:

        context = KnowledgeContext(
            query=str(query)
        )

        if not query or not str(query).strip():
            context.errors.append(
                "Query is required."
            )

            return KnowledgeContextBuildResult(
                success=False,
                context=context,
                errors=list(
                    context.errors
                ),
            )

        try:
            retrieved = (
                self.retriever.retrieve(
                    query
                )
            )

        except Exception as exc:
            error = (
                "Knowledge retrieval failed: "
                f"{type(exc).__name__}: {exc}"
            )

            context.errors.append(
                error
            )

            return KnowledgeContextBuildResult(
                success=False,
                context=context,
                errors=list(
                    context.errors
                ),
            )

        try:
            self._populate_context(
                context,
                retrieved,
            )

        except Exception as exc:
            error = (
                "Knowledge context construction failed: "
                f"{type(exc).__name__}: {exc}"
            )

            context.errors.append(
                error
            )

        success = (
            context.block_found
            and not context.errors
        )

        return KnowledgeContextBuildResult(
            success=success,
            context=context,
            errors=list(
                context.errors
            ),
        )

    def build_block(
        self,
        block_id: str,
    ) -> KnowledgeContextBuildResult:
        return self.build(
            block_id
        )

    # ========================================================================
    # Populate
    # ========================================================================

    def _populate_context(
        self,
        context: KnowledgeContext,
        retrieved: Any,
    ) -> None:

        context.block_id = self._get(
            retrieved,
            "block_id",
            None,
        )

        # IMPORTANT:
        #
        # The retriever is returning the correct block_id:
        #
        # block:gnuradio-main/gr-analog/analog_agc_xx
        #
        # Therefore block_found must be derived from the resolved
        # block_id rather than trusting the inconsistent flag.
        context.block_found = bool(
            context.block_id
        )

        context.source_files = self._limited(
            self._get_sequence(
                retrieved,
                "source_files",
            ),
            self.max_source_files,
        )

        context.classes = self._limited(
            self._get_sequence(
                retrieved,
                "classes",
            ),
            self.max_classes,
        )

        context.methods = self._limited(
            self._get_sequence(
                retrieved,
                "methods",
            ),
            self.max_methods,
        )

        context.functions = self._limited(
            self._get_sequence(
                retrieved,
                "functions",
            ),
            self.max_functions,
        )

        context.bindings = self._limited(
            self._get_sequence(
                retrieved,
                "bindings",
            ),
            self.max_bindings,
        )

        context.parameters = self._limited(
            self._get_sequence(
                retrieved,
                "parameters",
            ),
            self.max_parameters,
        )

        context.inherited_classes = (
            self._limited(
                self._get_sequence(
                    retrieved,
                    "inherited_classes",
                ),
                self.max_inherited_classes,
            )
        )

        context.references = (
            self._build_references(
                self._get_sequence(
                    retrieved,
                    "references",
                ),
                context.block_id,
            )
        )

        retrieval_errors = (
            self._get_sequence(
                retrieved,
                "errors",
            )
        )

        for error in retrieval_errors:
            if error is None:
                continue

            text = str(error)

            if (
                text
                and text not in context.errors
            ):
                context.errors.append(
                    text
                )

    # ========================================================================
    # References
    # ========================================================================

    def _build_references(
        self,
        values: Sequence[Any],
        block_id: Optional[str],
    ) -> List[ContextReference]:

        result: List[
            ContextReference
        ] = []

        seen: set[
            tuple[str, str, str]
        ] = set()

        for value in values:

            if value is None:
                continue

            node_id = self._node_id(
                value
            )

            node_name = self._node_name(
                value
            )

            if not node_id and not node_name:
                continue

            node_type = self._node_type(
                value
            )

            attributes = self._get(
                value,
                "attributes",
                {},
            )

            if not isinstance(
                attributes,
                dict,
            ):
                attributes = {}

            reference_types = (
                self._reference_types(
                    attributes
                )
            )

            if not reference_types:
                reference_types = [
                    "reference"
                ]

            relationship = "|".join(
                reference_types
            )

            source = (
                str(block_id)
                if block_id
                else node_id
            )

            target = (
                node_id
                if node_id
                else node_name
            )

            key = (
                source,
                relationship,
                target,
            )

            if key in seen:
                continue

            seen.add(key)

            metadata = {
                "node_name": node_name,
                "node_type": node_type,
            }

            for reference_type in (
                reference_types
            ):
                metadata[
                    reference_type
                ] = True

            result.append(
                ContextReference(
                    source=source,
                    relationship=relationship,
                    target=target,
                    metadata=metadata,
                )
            )

            if (
                len(result)
                >= self.max_references
            ):
                break

        return result

    def _reference_types(
        self,
        attributes: Dict[str, Any],
    ) -> List[str]:

        result: List[str] = []

        flags = [
            "external_reference",
            "inheritance_reference",
            "binding_reference",
            "reference",
            "dependency_reference",
            "include_reference",
        ]

        for flag in flags:
            if attributes.get(
                flag,
                False,
            ):
                result.append(
                    flag
                )

        return result

    # ========================================================================
    # Generic helpers
    # ========================================================================

    @staticmethod
    def _get(
        value: Any,
        name: str,
        default: Any = None,
    ) -> Any:

        if value is None:
            return default

        if isinstance(
            value,
            dict,
        ):
            return value.get(
                name,
                default,
            )

        return getattr(
            value,
            name,
            default,
        )

    @classmethod
    def _get_sequence(
        cls,
        value: Any,
        name: str,
    ) -> List[Any]:

        result = cls._get(
            value,
            name,
            [],
        )

        if result is None:
            return []

        if isinstance(
            result,
            list,
        ):
            return list(
                result
            )

        if isinstance(
            result,
            tuple,
        ):
            return list(
                result
            )

        if isinstance(
            result,
            set,
        ):
            return list(
                result
            )

        if isinstance(
            result,
            Sequence,
        ) and not isinstance(
            result,
            (
                str,
                bytes,
            ),
        ):
            return list(
                result
            )

        return [result]

    @staticmethod
    def _limited(
        values: Sequence[Any],
        maximum: int,
    ) -> List[Any]:

        if maximum <= 0:
            return []

        return list(
            values[:maximum]
        )

    @classmethod
    def _node_id(
        cls,
        node: Any,
    ) -> str:

        value = cls._get(
            node,
            "id",
            "",
        )

        if value is None:
            return ""

        return str(
            value
        )

    @classmethod
    def _node_name(
        cls,
        node: Any,
    ) -> str:

        value = cls._get(
            node,
            "name",
            "",
        )

        if value is None:
            return ""

        return str(
            value
        )

    @classmethod
    def _node_type(
        cls,
        node: Any,
    ) -> str:

        value = cls._get(
            node,
            "node_type",
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
    def _serialize(
        value: Any,
    ) -> Any:

        if value is None:
            return None

        if isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
            ),
        ):
            return value

        if isinstance(
            value,
            dict,
        ):
            return {
                str(key): KnowledgeContextBuilder._serialize(
                    item
                )
                for key, item in value.items()
            }

        if isinstance(
            value,
            (list, tuple),
        ):
            return [
                KnowledgeContextBuilder._serialize(
                    item
                )
                for item in value
            ]

        to_dict = getattr(
            value,
            "to_dict",
            None,
        )

        if callable(
            to_dict
        ):
            try:
                return KnowledgeContextBuilder._serialize(
                    to_dict()
                )
            except Exception:
                pass

        return str(
            value
        )


# ============================================================================
# Public helper
# ============================================================================


def build_knowledge_context(
    query: str,
) -> KnowledgeContextBuildResult:

    return KnowledgeContextBuilder().build(
        query
    )


__all__ = [
    "ContextReference",
    "KnowledgeContext",
    "KnowledgeContextBuildResult",
    "KnowledgeContextBuilder",
    "build_knowledge_context",
]