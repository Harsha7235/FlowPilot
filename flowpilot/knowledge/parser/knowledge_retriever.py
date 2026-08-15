from __future__ import annotations

"""
Knowledge retrieval layer for FlowPilot.

Purpose
-------
Convert the structured knowledge graph into a compact, useful retrieval
result for downstream answer-generation / agent components.

This module is intentionally READ-ONLY.

Pipeline:

    KnowledgeGraphStore
            |
            v
    KnowledgeGraphQuery
            |
            v
    KnowledgeRetriever
            |
            v
    RetrievalResult

The retriever does NOT:
    - modify the graph
    - rebuild the graph
    - parse source code
    - create embeddings
    - call an LLM
    - act as an agent

It only retrieves and organizes already-known information.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set

from flowpilot.knowledge.parser.knowledge_graph_models import (
    GraphNode,
    KnowledgeGraph,
)
from flowpilot.knowledge.parser.knowledge_graph_query import (
    KnowledgeGraphQuery,
)
from flowpilot.knowledge.parser.knowledge_graph_store import (
    KnowledgeGraphStore,
)


# ============================================================================
# Retrieval result
# ============================================================================


@dataclass
class RetrievalResult:
    """
    Structured result returned by KnowledgeRetriever.
    """

    success: bool = False

    query: str = ""

    block_id: Optional[str] = None

    block: Optional[GraphNode] = None

    source_files: List[GraphNode] = field(
        default_factory=list
    )

    classes: List[GraphNode] = field(
        default_factory=list
    )

    methods: List[GraphNode] = field(
        default_factory=list
    )

    functions: List[GraphNode] = field(
        default_factory=list
    )

    bindings: List[GraphNode] = field(
        default_factory=list
    )

    parameters: List[GraphNode] = field(
        default_factory=list
    )

    inherited_classes: List[GraphNode] = field(
        default_factory=list
    )

    references: List[GraphNode] = field(
        default_factory=list
    )

    errors: List[str] = field(
        default_factory=list
    )

    def summary(self) -> Dict[str, Any]:
        """
        Return compact retrieval statistics.
        """

        return {
            "success": self.success,
            "query": self.query,
            "block_id": self.block_id,
            "block_found": self.block is not None,
            "source_files": len(self.source_files),
            "classes": len(self.classes),
            "methods": len(self.methods),
            "functions": len(self.functions),
            "bindings": len(self.bindings),
            "parameters": len(self.parameters),
            "inherited_classes": len(
                self.inherited_classes
            ),
            "references": len(self.references),
            "errors": len(self.errors),
        }

    def to_context(self) -> Dict[str, Any]:
        """
        Convert the retrieval result into a JSON-friendly context object.

        This is the format intended for future answer-generation /
        agent components.
        """

        return {
            "query": self.query,
            "block_id": self.block_id,
            "block": (
                self._node_dict(self.block)
                if self.block is not None
                else None
            ),
            "source_files": [
                self._node_dict(node)
                for node in self.source_files
            ],
            "classes": [
                self._node_dict(node)
                for node in self.classes
            ],
            "methods": [
                self._node_dict(node)
                for node in self.methods
            ],
            "functions": [
                self._node_dict(node)
                for node in self.functions
            ],
            "bindings": [
                self._node_dict(node)
                for node in self.bindings
            ],
            "parameters": [
                self._node_dict(node)
                for node in self.parameters
            ],
            "inherited_classes": [
                self._node_dict(node)
                for node in self.inherited_classes
            ],
            "references": [
                self._node_dict(node)
                for node in self.references
            ],
            "errors": list(self.errors),
        }

    @staticmethod
    def _node_dict(
        node: Optional[GraphNode],
    ) -> Dict[str, Any]:
        """
        Convert a graph node into a plain dictionary.
        """

        if node is None:
            return {}

        result: Dict[str, Any] = {}

        if hasattr(node, "to_dict"):
            try:
                value = node.to_dict()

                if isinstance(value, dict):
                    return value
            except Exception:
                pass

        node_id = getattr(
            node,
            "id",
            None,
        )

        node_name = getattr(
            node,
            "name",
            None,
        )

        node_type = getattr(
            node,
            "node_type",
            None,
        )

        if hasattr(node_type, "value"):
            node_type = node_type.value

        if node_id is not None:
            result["id"] = str(node_id)

        if node_name is not None:
            result["name"] = str(node_name)

        if node_type is not None:
            result["node_type"] = str(node_type)

        return result


# ============================================================================
# KnowledgeRetriever
# ============================================================================


class KnowledgeRetriever:
    """
    Retrieval service built on top of KnowledgeGraphQuery.

    Responsibilities:

        1. Resolve a block.
        2. Retrieve implementation information.
        3. Retrieve inheritance information.
        4. Retrieve reference information.
        5. Produce compact context for downstream components.

    This class does not mutate any stored knowledge.
    """

    def __init__(
        self,
        query: Optional[KnowledgeGraphQuery] = None,
        store: Optional[KnowledgeGraphStore] = None,
    ) -> None:

        if query is not None:

            self.query = query

        else:

            self.query = KnowledgeGraphQuery(
                store=store
            )

    # ------------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------------

    def load(self) -> KnowledgeGraph:
        """
        Load the knowledge graph.
        """

        return self.query.load()

    def reload(self) -> KnowledgeGraph:
        """
        Reload the knowledge graph.
        """

        return self.query.reload()

    # ------------------------------------------------------------------------
    # Main retrieval
    # ------------------------------------------------------------------------

    def retrieve(
        self,
        query_text: str,
        block_id: Optional[str] = None,
    ) -> RetrievalResult:
        """
        Retrieve implementation knowledge.

        If block_id is supplied, it is used directly.

        Otherwise the retriever attempts to resolve the block from the
        supplied query text.
        """

        result = RetrievalResult(
            query=query_text or "",
            block_id=block_id,
        )

        try:

            self.load()

            resolved_block_id = (
                block_id
                or self.resolve_block(
                    query_text
                )
            )

            if not resolved_block_id:

                result.errors.append(
                    "Could not resolve a block from the query"
                )

                return result

            result.block_id = resolved_block_id

            implementation = (
                self.query.implementation(
                    resolved_block_id
                )
            )

            if not implementation.success:

                result.errors.extend(
                    implementation.errors
                )

                return result

            result.block = (
                implementation.block
            )

            result.source_files = list(
                implementation.source_files
            )

            result.classes = list(
                implementation.classes
            )

            result.methods = list(
                implementation.methods
            )

            result.functions = list(
                implementation.functions
            )

            result.bindings = list(
                implementation.bindings
            )

            result.parameters = list(
                implementation.parameters
            )

            result.inherited_classes = (
                self._retrieve_inheritance(
                    result.classes
                )
            )

            result.references = (
                self._retrieve_references(
                    result.classes,
                    result.bindings,
                )
            )

            result.success = True

        except Exception as exc:

            result.errors.append(
                f"{type(exc).__name__}: {exc}"
            )

            result.success = False

        return result

    # ------------------------------------------------------------------------
    # Block resolution
    # ------------------------------------------------------------------------

    def resolve_block(
        self,
        query_text: str,
    ) -> Optional[str]:
        """
        Resolve a block ID from natural-language-ish query text.

        Resolution order:

            1. Exact block ID.
            2. Exact block name.
            3. Case-insensitive block name.
            4. Token-based match.

        This is deliberately deterministic.

        It is NOT an LLM and does not invent block IDs.
        """

        if not query_text:
            return None

        text = query_text.strip()

        if not text:
            return None

        # ------------------------------------------------------------------
        # Exact block ID
        # ------------------------------------------------------------------

        exact = self.query.block(
            text
        )

        if exact is not None:
            return self.query._node_id(
                exact
            )

        # ------------------------------------------------------------------
        # Search all blocks
        # ------------------------------------------------------------------

        blocks = self.query.find_blocks()

        if not blocks:
            return None

        lowered = text.lower()

        # ------------------------------------------------------------------
        # Exact name
        # ------------------------------------------------------------------

        for block in blocks:

            name = self.query._node_name(
                block
            )

            if name.lower() == lowered:
                return self.query._node_id(
                    block
                )

        # ------------------------------------------------------------------
        # Block ID contained in query
        # ------------------------------------------------------------------

        for block in blocks:

            node_id = self.query._node_id(
                block
            )

            name = self.query._node_name(
                block
            )

            if (
                name.lower() in lowered
                and name
            ):
                return node_id

        # ------------------------------------------------------------------
        # Token overlap
        # ------------------------------------------------------------------

        query_tokens = self._tokens(
            lowered
        )

        if not query_tokens:
            return None

        best_block: Optional[
            GraphNode
        ] = None

        best_score = 0

        for block in blocks:

            node_id = self.query._node_id(
                block
            )

            name = self.query._node_name(
                block
            )

            candidate_text = (
                f"{name} {node_id}"
            ).lower()

            candidate_tokens = self._tokens(
                candidate_text
            )

            overlap = (
                query_tokens
                & candidate_tokens
            )

            score = len(overlap)

            if score > best_score:

                best_score = score
                best_block = block

        if best_block is None:
            return None

        if best_score <= 0:
            return None

        return self.query._node_id(
            best_block
        )

    # ------------------------------------------------------------------------
    # Inheritance retrieval
    # ------------------------------------------------------------------------

    def _retrieve_inheritance(
        self,
        classes: Iterable[GraphNode],
    ) -> List[GraphNode]:
        """
        Retrieve classes inherited by implementation classes.
        """

        result: List[GraphNode] = []

        for class_node in classes:

            inherited = (
                self.query.class_inheritance(
                    class_node
                )
            )

            result.extend(
                inherited
            )

        return self._unique_nodes(
            result
        )

    # ------------------------------------------------------------------------
    # Reference retrieval
    # ------------------------------------------------------------------------

    def _retrieve_references(
        self,
        classes: Iterable[GraphNode],
        bindings: Iterable[GraphNode],
    ) -> List[GraphNode]:
        """
        Retrieve graph entities referenced by implementation classes
        and binding nodes.
        """

        result: List[GraphNode] = []

        for class_node in classes:

            references = (
                self.query.class_references(
                    class_node
                )
            )

            result.extend(
                references
            )

        for binding in bindings:

            binding_id = (
                self.query._node_id(
                    binding
                )
            )

            for edge in self.query.outgoing_edges(
                binding_id
            ):

                if (
                    self.query._edge_relationship(
                        edge
                    )
                    != "references"
                ):
                    continue

                target = self.query.node(
                    self.query._edge_target(
                        edge
                    )
                )

                if target is not None:
                    result.append(
                        target
                    )

        return self._unique_nodes(
            result
        )

    # ------------------------------------------------------------------------
    # Specialized retrieval helpers
    # ------------------------------------------------------------------------

    def retrieve_block(
        self,
        block_id: str,
    ) -> RetrievalResult:
        """
        Retrieve one block directly.
        """

        return self.retrieve(
            query_text=block_id,
            block_id=block_id,
        )

    def retrieve_classes(
        self,
        block_id: str,
    ) -> List[GraphNode]:
        """
        Retrieve implementation classes for a block.
        """

        return self.query.block_classes(
            block_id
        )

    def retrieve_methods(
        self,
        block_id: str,
    ) -> List[GraphNode]:
        """
        Retrieve implementation methods for a block.
        """

        return self.query.block_methods(
            block_id
        )

    def retrieve_functions(
        self,
        block_id: str,
    ) -> List[GraphNode]:
        """
        Retrieve implementation functions for a block.
        """

        return self.query.block_functions(
            block_id
        )

    def retrieve_bindings(
        self,
        block_id: str,
    ) -> List[GraphNode]:
        """
        Retrieve Python/C++ binding nodes for a block.
        """

        return self.query.block_bindings(
            block_id
        )

    def retrieve_parameters(
        self,
        block_id: str,
    ) -> List[GraphNode]:
        """
        Retrieve method/function parameters for a block.
        """

        return self.query.block_parameters(
            block_id
        )

    # ------------------------------------------------------------------------
    # Context generation
    # ------------------------------------------------------------------------

    def context(
        self,
        query_text: str,
        block_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve information and return it as downstream-ready context.
        """

        result = self.retrieve(
            query_text=query_text,
            block_id=block_id,
        )

        return result.to_context()

    # ------------------------------------------------------------------------
    # Compact text representation
    # ------------------------------------------------------------------------

    def context_text(
        self,
        query_text: str,
        block_id: Optional[str] = None,
    ) -> str:
        """
        Convert retrieval context into compact human-readable text.

        This is intended for a future LLM/agent prompt layer.
        """

        result = self.retrieve(
            query_text=query_text,
            block_id=block_id,
        )

        lines: List[str] = []

        lines.append(
            "FLOWPILOT KNOWLEDGE RETRIEVAL"
        )

        lines.append(
            f"Query: {result.query}"
        )

        lines.append(
            f"Block: {result.block_id or 'NOT FOUND'}"
        )

        lines.append("")

        if result.block is not None:

            lines.append(
                "BLOCK"
            )

            lines.append(
                f"  ID: {self.query._node_id(result.block)}"
            )

            lines.append(
                f"  Name: {self.query._node_name(result.block)}"
            )

            lines.append("")

        lines.append(
            f"SOURCE FILES ({len(result.source_files)})"
        )

        for node in result.source_files:

            lines.append(
                f"  - {self.query._node_name(node)}"
            )

        lines.append("")

        lines.append(
            f"CLASSES ({len(result.classes)})"
        )

        for node in result.classes:

            lines.append(
                f"  - {self.query._node_name(node)}"
            )

        lines.append("")

        lines.append(
            f"METHODS ({len(result.methods)})"
        )

        for node in result.methods:

            lines.append(
                f"  - {self.query._node_name(node)}"
            )

        lines.append("")

        lines.append(
            f"FUNCTIONS ({len(result.functions)})"
        )

        for node in result.functions:

            lines.append(
                f"  - {self.query._node_name(node)}"
            )

        lines.append("")

        lines.append(
            f"BINDINGS ({len(result.bindings)})"
        )

        for node in result.bindings:

            lines.append(
                f"  - {self.query._node_name(node)}"
            )

        lines.append("")

        lines.append(
            f"PARAMETERS ({len(result.parameters)})"
        )

        for node in result.parameters:

            lines.append(
                f"  - {self.query._node_name(node)}"
            )

        lines.append("")

        lines.append(
            f"INHERITED CLASSES ({len(result.inherited_classes)})"
        )

        for node in result.inherited_classes:

            lines.append(
                f"  - {self.query._node_name(node)}"
            )

        lines.append("")

        lines.append(
            f"REFERENCES ({len(result.references)})"
        )

        for node in result.references:

            lines.append(
                f"  - {self.query._node_name(node)}"
            )

        if result.errors:

            lines.append("")

            lines.append("ERRORS")

            for error in result.errors:

                lines.append(
                    f"  - {error}"
                )

        return "\n".join(lines)

    # ------------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------------

    def statistics(
        self,
    ) -> Dict[str, Any]:
        """
        Return retrieval-layer statistics.

        This does not modify the graph.
        """

        graph_summary = (
            self.query.graph_summary()
        )

        return {
            "graph_loaded": self.query.is_loaded(),
            "graph": graph_summary,
            "validation_errors": self.query.validate(),
        }

    # ------------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------------

    @staticmethod
    def _tokens(
        text: str,
    ) -> Set[str]:
        """
        Tokenize text conservatively.
        """

        if not text:
            return set()

        normalized = (
            text.lower()
            .replace("/", " ")
            .replace("\\", " ")
            .replace(":", " ")
            .replace("-", " ")
            .replace("_", " ")
            .replace(".", " ")
        )

        tokens = {
            token
            for token in normalized.split()
            if len(token) >= 2
        }

        return tokens

    @staticmethod
    def _unique_nodes(
        nodes: Iterable[GraphNode],
    ) -> List[GraphNode]:
        """
        Deduplicate graph nodes by ID.
        """

        result: List[GraphNode] = []

        seen: Set[str] = set()

        for node in nodes:

            node_id = getattr(
                node,
                "id",
                None,
            )

            if node_id is None:

                node_id = getattr(
                    node,
                    "node_id",
                    None,
                )

            if node_id is None:
                node_id = str(node)

            node_id = str(
                node_id
            )

            if node_id in seen:
                continue

            seen.add(node_id)

            result.append(
                node
            )

        return result


# ============================================================================
# Public exports
# ============================================================================


__all__ = [
    "RetrievalResult",
    "KnowledgeRetriever",
]