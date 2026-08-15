from __future__ import annotations

"""
Knowledge graph query layer for FlowPilot.

This module provides read-only queries over the persisted knowledge graph.

Important graph semantics used by the current FlowPilot graph:

    BLOCK
        |
        +--implemented_by--> SOURCE_FILE
                                  |
                                  +--declared_in--> CLASS / STRUCT

    CLASS
        |
        +--has_method--> METHOD

    METHOD / FUNCTION
        |
        +--has_parameter--> PARAMETER

    CLASS
        |
        +--inherits_from--> CLASS

    BINDING
        |
        +--references--> CLASS / METHOD

The graph builder also creates reference nodes for external classes.
Those external/reference nodes must NOT automatically be counted as
implementation classes.

The query layer therefore distinguishes:

    1. declared implementation entities
    2. referenced/external entities

This is especially important for GNU Radio source repositories.
"""

from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
)

from flowpilot.knowledge.parser.knowledge_graph_models import (
    GraphEdge,
    GraphNode,
    GraphNodeType,
    KnowledgeGraph,
)
from flowpilot.knowledge.parser.knowledge_graph_store import (
    KnowledgeGraphStore,
)


# ============================================================================
# Query result models
# ============================================================================


@dataclass
class ImplementationQueryResult:
    """
    Result of querying implementation knowledge for one block.
    """

    success: bool = False

    block_found: bool = False

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

    errors: List[str] = field(
        default_factory=list
    )

    def summary(self) -> Dict[str, Any]:
        """
        Return a compact summary.
        """

        return {
            "success": self.success,
            "block_found": self.block_found,
            "source_files": len(self.source_files),
            "classes": len(self.classes),
            "methods": len(self.methods),
            "functions": len(self.functions),
            "bindings": len(self.bindings),
            "parameters": len(self.parameters),
            "errors": len(self.errors),
        }


# ============================================================================
# KnowledgeGraphQuery
# ============================================================================


class KnowledgeGraphQuery:
    """
    Read-only query API over the persisted FlowPilot knowledge graph.

    The class intentionally does not mutate the graph.

    It can:

        - load the persisted graph
        - inspect graph statistics
        - validate the graph
        - find blocks
        - find source files
        - find implementation classes
        - find methods
        - find functions
        - find bindings
        - find parameters
        - traverse graph relationships
        - reconstruct implementation knowledge for a block
    """

    # ------------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------------

    def __init__(
        self,
        store: Optional[KnowledgeGraphStore] = None,
        graph: Optional[KnowledgeGraph] = None,
    ) -> None:
        self.store = store or KnowledgeGraphStore()
        self.graph: Optional[KnowledgeGraph] = graph

    # ------------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------------

    def load(self) -> KnowledgeGraph:
        """
        Load the persisted knowledge graph.
        """

        if self.graph is not None:
            return self.graph

        self.graph = self.store.load()

        return self.graph

    def reload(self) -> KnowledgeGraph:
        """
        Force a reload from disk.
        """

        self.graph = self.store.load()

        return self.graph

    def is_loaded(self) -> bool:
        """
        Return True when a graph is loaded.
        """

        return self.graph is not None

    def _require_graph(self) -> KnowledgeGraph:
        """
        Return the loaded graph.

        Automatically loads it if necessary.
        """

        if self.graph is None:
            self.load()

        if self.graph is None:
            raise RuntimeError(
                "Knowledge graph could not be loaded"
            )

        return self.graph

    # ------------------------------------------------------------------------
    # Graph-level helpers
    # ------------------------------------------------------------------------

    def graph_summary(self) -> Dict[str, Any]:
        """
        Return graph summary.
        """

        graph = self._require_graph()

        return graph.summary()

    def validate(self) -> List[str]:
        """
        Validate the loaded graph.

        Returns:
            Empty list when valid.
        """

        graph = self._require_graph()

        return list(graph.validate())

    def nodes(self) -> List[GraphNode]:
        """
        Return all graph nodes.
        """

        graph = self._require_graph()

        return list(graph.nodes)

    def edges(self) -> List[GraphEdge]:
        """
        Return all graph edges.
        """

        graph = self._require_graph()

        return list(graph.edges)

    # ------------------------------------------------------------------------
    # Low-level node helpers
    # ------------------------------------------------------------------------

    @staticmethod
    def _node_id(node: Any) -> str:
        """
        Safely obtain a node ID.
        """

        if node is None:
            return ""

        if isinstance(node, str):
            return node

        value = getattr(node, "id", None)

        if value is not None:
            return str(value)

        value = getattr(node, "node_id", None)

        if value is not None:
            return str(value)

        return str(node)

    @staticmethod
    def _node_name(node: Any) -> str:
        """
        Safely obtain a node display name.
        """

        if node is None:
            return ""

        if isinstance(node, str):
            return node

        value = getattr(node, "name", None)

        if value is not None:
            return str(value)

        value = getattr(node, "label", None)

        if value is not None:
            return str(value)

        return KnowledgeGraphQuery._node_id(node)

    @staticmethod
    def _node_type(node: Any) -> str:
        """
        Safely normalize GraphNodeType to its string value.
        """

        if node is None:
            return ""

        value = getattr(node, "node_type", None)

        if value is None:
            value = getattr(node, "type", None)

        if value is None:
            return ""

        if hasattr(value, "value"):
            return str(value.value)

        return str(value)

    @staticmethod
    def _edge_id(edge: Any) -> str:
        """
        Safely obtain edge ID.
        """

        if edge is None:
            return ""

        value = getattr(edge, "id", None)

        if value is not None:
            return str(value)

        value = getattr(edge, "edge_id", None)

        if value is not None:
            return str(value)

        return str(edge)

    @staticmethod
    def _edge_source(edge: Any) -> str:
        """
        Safely obtain source node ID.
        """

        value = getattr(edge, "source", None)

        if value is None:
            value = getattr(edge, "source_id", None)

        if value is None:
            return ""

        if hasattr(value, "id"):
            return str(value.id)

        return str(value)

    @staticmethod
    def _edge_target(edge: Any) -> str:
        """
        Safely obtain target node ID.
        """

        value = getattr(edge, "target", None)

        if value is None:
            value = getattr(edge, "target_id", None)

        if value is None:
            return ""

        if hasattr(value, "id"):
            return str(value.id)

        return str(value)

    @staticmethod
    def _edge_relationship(edge: Any) -> str:
        """
        Safely normalize relationship.
        """

        value = getattr(edge, "relationship", None)

        if value is None:
            value = getattr(edge, "relation", None)

        if value is None:
            return ""

        if hasattr(value, "value"):
            return str(value.value)

        return str(value)

    # ------------------------------------------------------------------------
    # Generic graph access
    # ------------------------------------------------------------------------

    def node(self, node_id: str) -> Optional[GraphNode]:
        """
        Return a node by ID.
        """

        graph = self._require_graph()

        try:
            return graph.get_node(node_id)
        except Exception:
            pass

        for node in graph.nodes:
            if self._node_id(node) == node_id:
                return node

        return None

    def edge(self, edge_id: str) -> Optional[GraphEdge]:
        """
        Return an edge by ID.
        """

        graph = self._require_graph()

        for edge in graph.edges:
            if self._edge_id(edge) == edge_id:
                return edge

        return None

    def has_node(self, node_id: str) -> bool:
        """
        Return True when a node exists.
        """

        return self.node(node_id) is not None

    def outgoing_edges(
        self,
        node_id: str,
    ) -> List[GraphEdge]:
        """
        Return edges originating from node_id.
        """

        graph = self._require_graph()

        result: List[GraphEdge] = []

        for edge in graph.edges:
            if self._edge_source(edge) == node_id:
                result.append(edge)

        return result

    def incoming_edges(
        self,
        node_id: str,
    ) -> List[GraphEdge]:
        """
        Return edges entering node_id.
        """

        graph = self._require_graph()

        result: List[GraphEdge] = []

        for edge in graph.edges:
            if self._edge_target(edge) == node_id:
                result.append(edge)

        return result

    def edges_by_relationship(
        self,
        relationship: str,
    ) -> List[GraphEdge]:
        """
        Return all edges with a given relationship.
        """

        relationship = self._normalize_relationship(
            relationship
        )

        return [
            edge
            for edge in self.edges()
            if self._edge_relationship(edge)
            == relationship
        ]

    def _normalize_relationship(
        self,
        relationship: Any,
    ) -> str:
        if hasattr(relationship, "value"):
            return str(relationship.value)

        value = str(relationship)

        if "." in value:
            value = value.split(".")[-1]

        return value.lower()

    def nodes_by_type(
        self,
        node_type: Any,
    ) -> List[GraphNode]:
        """
        Return all nodes of a given type.
        """

        expected = self._normalize_node_type(
            node_type
        )

        return [
            node
            for node in self.nodes()
            if self._node_type(node) == expected
        ]

    def _normalize_node_type(
        self,
        node_type: Any,
    ) -> str:
        if hasattr(node_type, "value"):
            return str(node_type.value)

        value = str(node_type)

        if "." in value:
            value = value.split(".")[-1]

        return value.lower()

    # ------------------------------------------------------------------------
    # Relationship traversal
    # ------------------------------------------------------------------------

    def outgoing(
        self,
        node_id: str,
        relationship: Optional[str] = None,
    ) -> List[GraphNode]:
        """
        Return nodes reached through outgoing edges.
        """

        relationship = (
            self._normalize_relationship(relationship)
            if relationship is not None
            else None
        )

        result: List[GraphNode] = []

        for edge in self.outgoing_edges(node_id):

            if (
                relationship is not None
                and self._edge_relationship(edge)
                != relationship
            ):
                continue

            target = self.node(
                self._edge_target(edge)
            )

            if target is not None:
                result.append(target)

        return self._unique_nodes(result)

    def incoming(
        self,
        node_id: str,
        relationship: Optional[str] = None,
    ) -> List[GraphNode]:
        """
        Return nodes reached through incoming edges.
        """

        relationship = (
            self._normalize_relationship(relationship)
            if relationship is not None
            else None
        )

        result: List[GraphNode] = []

        for edge in self.incoming_edges(node_id):

            if (
                relationship is not None
                and self._edge_relationship(edge)
                != relationship
            ):
                continue

            source = self.node(
                self._edge_source(edge)
            )

            if source is not None:
                result.append(source)

        return self._unique_nodes(result)

    # ------------------------------------------------------------------------
    # Generic node queries
    # ------------------------------------------------------------------------

    def _unique_nodes(
        self,
        nodes: Iterable[GraphNode],
    ) -> List[GraphNode]:
        result: List[GraphNode] = []
        seen: Set[str] = set()

        for node in nodes:

            node_id = self._node_id(node)

            if not node_id:
                continue

            if node_id in seen:
                continue

            seen.add(node_id)
            result.append(node)

        return result

    def _unique_sorted_nodes(
        self,
        nodes: Iterable[GraphNode],
    ) -> List[GraphNode]:
        unique = self._unique_nodes(nodes)

        return sorted(
            unique,
            key=lambda node: (
                self._node_type(node),
                self._node_name(node),
                self._node_id(node),
            ),
        )

    # ------------------------------------------------------------------------
    # Block lookup
    # ------------------------------------------------------------------------

    def find_blocks(
        self,
        block_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> List[GraphNode]:
        """
        Find block nodes.
        """

        blocks = self.nodes_by_type(
            GraphNodeType.BLOCK
        )

        result: List[GraphNode] = []

        for block in blocks:

            node_id = self._node_id(block)
            node_name = self._node_name(block)

            if block_id is not None:

                if (
                    node_id == block_id
                    or node_name == block_id
                    or node_id.endswith(
                        "/" + block_id
                    )
                ):
                    result.append(block)

                continue

            if name is not None:

                if name.lower() in node_name.lower():
                    result.append(block)

                continue

            result.append(block)

        return self._unique_sorted_nodes(result)

    def block(
        self,
        block_id: str,
    ) -> Optional[GraphNode]:
        """
        Find one block.
        """

        matches = self.find_blocks(
            block_id=block_id
        )

        if matches:
            return matches[0]

        return None

    # ------------------------------------------------------------------------
    # Block -> source files
    # ------------------------------------------------------------------------

    def block_source_files(
        self,
        block_id: str,
    ) -> List[GraphNode]:
        """
        Return source files implementing a block.

        Actual graph direction:

            BLOCK --implemented_by--> SOURCE_FILE
        """

        block = self.block(block_id)

        if block is None:
            return []

        block_node_id = self._node_id(block)

        files = self.outgoing(
            block_node_id,
            "implemented_by",
        )

        return [
            node
            for node in self._unique_sorted_nodes(files)
            if self._node_type(node)
            == "source_file"
        ]

    # ------------------------------------------------------------------------
    # Source-file -> declared entities
    # ------------------------------------------------------------------------

    def source_file_classes(
        self,
        source_file: Any,
    ) -> List[GraphNode]:
        """
        Return classes/structs declared in one source file.

        Actual graph direction:

            SOURCE_FILE --declared_in--> CLASS
            SOURCE_FILE --declared_in--> STRUCT

        IMPORTANT:
        Only declared_in is followed.

        External classes reached through references or inheritance
        are not counted.

        IMPORTANT:
        This method preserves declaration occurrences.

        The graph may reuse one GraphNode for the same class name
        appearing in multiple declaration locations. The original
        implementation parser counts those source declarations.

        Therefore we MUST NOT call _unique_sorted_nodes() here.
        """

        source_file_id = (
            self._node_id(source_file)
            if not isinstance(source_file, str)
            else source_file
        )

        result: List[GraphNode] = []

        for edge in self.outgoing_edges(
            source_file_id
        ):

            if (
                self._edge_relationship(edge)
                != "declared_in"
            ):
                continue

            target_id = self._edge_target(edge)

            target = self.node(target_id)

            if target is None:
                continue

            target_type = self._node_type(target)

            if target_type not in (
                "class",
                "struct",
            ):
                continue

            result.append(target)

        # DO NOT DEDUPLICATE.
        #
        # Example:
        #
        # agc_python.cc
        #     declared_in -> agc_cc
        #     declared_in -> agc_ff
        #
        # Other binding files can declare the same graph class node again.
        #
        # We preserve those occurrences because the implementation parser
        # counts source declarations.
        return sorted(
            result,
            key=lambda node: (
                self._node_type(node),
                self._node_name(node),
                self._node_id(node),
            ),
        )

    def source_file_functions(
        self,
        source_file: Any,
    ) -> List[GraphNode]:
        """
        Return functions directly associated with a source file.

        The current graph uses:

            SOURCE_FILE --has_function--> FUNCTION
        """

        source_file_id = (
            self._node_id(source_file)
            if not isinstance(source_file, str)
            else source_file
        )

        result: List[GraphNode] = []

        for edge in self.outgoing_edges(
            source_file_id
        ):

            if (
                self._edge_relationship(edge)
                != "has_function"
            ):
                continue

            target = self.node(
                self._edge_target(edge)
            )

            if target is None:
                continue

            if self._node_type(target) != "function":
                continue

            result.append(target)

        return self._unique_sorted_nodes(result)

    # ------------------------------------------------------------------------
    # Block classes
    # ------------------------------------------------------------------------

    def block_classes(
        self,
        block_id: str,
    ) -> List[GraphNode]:
        """
        Return implementation classes/structs declared in the block's
        confirmed implementation source files.

        Authoritative traversal:

            BLOCK
              |
              +--implemented_by--> SOURCE_FILE
                                      |
                                      +--declared_in--> CLASS/STRUCT

        IMPORTANT:
        Do NOT deduplicate the result.

        The implementation parser counts source-level class declarations.

        For analog_agc_xx the source store reports 7 declarations:

            agc_cc_impl
            agc_ff_impl
            agc_cc
            agc_ff
            agc_cc
            agc_ff
            test_agc

        Some of those declarations resolve to the same graph node.

        Therefore:

            graph unique class nodes != source declaration count

        and the query must preserve declaration occurrences.
        """

        source_files = self.block_source_files(
            block_id
        )

        result: List[GraphNode] = []

        for source_file in source_files:

            result.extend(
                self.source_file_classes(
                    source_file
                )
            )

        # DO NOT use _unique_sorted_nodes() here.
        #
        # The graph intentionally deduplicates nodes, while this query
        # needs to preserve declaration occurrences.
        return sorted(
            result,
            key=lambda node: (
                self._node_type(node),
                self._node_name(node),
                self._node_id(node),
            ),
        )

    # ------------------------------------------------------------------------
    # Class methods
    # ------------------------------------------------------------------------

    def class_methods(
        self,
        class_node: Any,
    ) -> List[GraphNode]:
        """
        Return methods belonging to a class.

        Actual graph direction:

            CLASS --has_method--> METHOD
        """

        class_id = (
            self._node_id(class_node)
            if not isinstance(class_node, str)
            else class_node
        )

        result: List[GraphNode] = []

        for edge in self.outgoing_edges(
            class_id
        ):

            if (
                self._edge_relationship(edge)
                != "has_method"
            ):
                continue

            target = self.node(
                self._edge_target(edge)
            )

            if target is None:
                continue

            if self._node_type(target) != "method":
                continue

            result.append(target)

        return self._unique_sorted_nodes(result)

    def block_methods(
        self,
        block_id: str,
    ) -> List[GraphNode]:
        """
        Return methods belonging to implementation classes
        of a block.
        """

        classes = self.block_classes(
            block_id
        )

        result: List[GraphNode] = []

        for class_node in classes:

            result.extend(
                self.class_methods(
                    class_node
                )
            )

        return self._unique_sorted_nodes(result)

    # ------------------------------------------------------------------------
    # Functions
    # ------------------------------------------------------------------------

    def block_functions(
        self,
        block_id: str,
    ) -> List[GraphNode]:
        """
        Return standalone functions belonging to block source files.
        """

        source_files = self.block_source_files(
            block_id
        )

        result: List[GraphNode] = []

        for source_file in source_files:

            result.extend(
                self.source_file_functions(
                    source_file
                )
            )

        return self._unique_sorted_nodes(result)

    # ------------------------------------------------------------------------
    # Parameters
    # ------------------------------------------------------------------------

    def node_parameters(
        self,
        node: Any,
    ) -> List[GraphNode]:
        """
        Return parameters belonging to a method/function.

        Actual graph direction:

            METHOD/FUNCTION --has_parameter--> PARAMETER
        """

        node_id = (
            self._node_id(node)
            if not isinstance(node, str)
            else node
        )

        result: List[GraphNode] = []

        for edge in self.outgoing_edges(
            node_id
        ):

            if (
                self._edge_relationship(edge)
                != "has_parameter"
            ):
                continue

            target = self.node(
                self._edge_target(edge)
            )

            if target is None:
                continue

            if self._node_type(target) != "parameter":
                continue

            result.append(target)

        return self._unique_sorted_nodes(result)

    def block_parameters(
        self,
        block_id: str,
    ) -> List[GraphNode]:
        """
        Return parameters belonging to both methods and functions
        of a block.
        """

        result: List[GraphNode] = []

        for method in self.block_methods(
            block_id
        ):
            result.extend(
                self.node_parameters(method)
            )

        for function in self.block_functions(
            block_id
        ):
            result.extend(
                self.node_parameters(function)
            )

        return self._unique_sorted_nodes(result)

    # ------------------------------------------------------------------------
    # Binding queries
    # ------------------------------------------------------------------------

    def block_bindings(
        self,
        block_id: str,
    ) -> List[GraphNode]:
        """
        Return binding nodes belonging to the block.

        The current graph stores binding provenance using:

            BINDING --references--> CLASS/METHOD

        Binding node IDs also contain the block identity.
        """

        block = self.block(block_id)

        if block is None:
            return []

        block_node_id = self._node_id(block)

        block_name = self._node_name(block)

        bindings = self.nodes_by_type(
            GraphNodeType.BINDING
        )

        result: List[GraphNode] = []

        for binding in bindings:

            binding_id = self._node_id(
                binding
            )

            binding_name = self._node_name(
                binding
            )

            if (
                f"/{block_name}/"
                in binding_id
                or f"/{block_name}/"
                in binding_name
            ):
                result.append(binding)
                continue

            if block_node_id:

                block_suffix = (
                    block_node_id
                    .split(":", 1)[-1]
                )

                if block_suffix in binding_id:
                    result.append(binding)

        return self._unique_sorted_nodes(
            result
        )

    # ------------------------------------------------------------------------
    # Referenced classes
    # ------------------------------------------------------------------------

    def class_references(
        self,
        class_node: Any,
    ) -> List[GraphNode]:
        """
        Return nodes that reference a class.
        """

        class_id = (
            self._node_id(class_node)
            if not isinstance(class_node, str)
            else class_node
        )

        return self.incoming(
            class_id,
            "references",
        )

    def class_inheritance(
        self,
        class_node: Any,
    ) -> List[GraphNode]:
        """
        Return classes inherited by a class.

        Actual graph:

            CLASS --inherits_from--> CLASS
        """

        class_id = (
            self._node_id(class_node)
            if not isinstance(class_node, str)
            else class_node
        )

        result = self.outgoing(
            class_id,
            "inherits_from",
        )

        return [
            node
            for node in result
            if self._node_type(node)
            == "class"
        ]

    # ------------------------------------------------------------------------
    # Block implementation result
    # ------------------------------------------------------------------------

    def implementation(
        self,
        block_id: str,
    ) -> ImplementationQueryResult:
        """
        Reconstruct the implementation knowledge available in the graph
        for one block.
        """

        result = ImplementationQueryResult()

        try:

            block = self.block(
                block_id
            )

            if block is None:

                result.errors.append(
                    f"Block not found: {block_id}"
                )

                result.success = False
                result.block_found = False

                return result

            result.block = block
            result.block_found = True

            result.source_files = (
                self.block_source_files(
                    block_id
                )
            )

            result.classes = (
                self.block_classes(
                    block_id
                )
            )

            result.methods = (
                self.block_methods(
                    block_id
                )
            )

            result.functions = (
                self.block_functions(
                    block_id
                )
            )

            result.bindings = (
                self.block_bindings(
                    block_id
                )
            )

            result.parameters = (
                self.block_parameters(
                    block_id
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
    # Convenience aliases
    # ------------------------------------------------------------------------

    def get_block(
        self,
        block_id: str,
    ) -> Optional[GraphNode]:
        """
        Alias for block().
        """

        return self.block(block_id)

    def get_source_files(
        self,
        block_id: str,
    ) -> List[GraphNode]:
        """
        Alias for block_source_files().
        """

        return self.block_source_files(
            block_id
        )

    def get_classes(
        self,
        block_id: str,
    ) -> List[GraphNode]:
        """
        Alias for block_classes().
        """

        return self.block_classes(
            block_id
        )

    def get_methods(
        self,
        block_id: str,
    ) -> List[GraphNode]:
        """
        Alias for block_methods().
        """

        return self.block_methods(
            block_id
        )

    def get_functions(
        self,
        block_id: str,
    ) -> List[GraphNode]:
        """
        Alias for block_functions().
        """

        return self.block_functions(
            block_id
        )

    def get_bindings(
        self,
        block_id: str,
    ) -> List[GraphNode]:
        """
        Alias for block_bindings().
        """

        return self.block_bindings(
            block_id
        )

    def get_parameters(
        self,
        block_id: str,
    ) -> List[GraphNode]:
        """
        Alias for block_parameters().
        """

        return self.block_parameters(
            block_id
        )


# ============================================================================
# Public exports
# ============================================================================


__all__ = [
    "ImplementationQueryResult",
    "KnowledgeGraphQuery",
]