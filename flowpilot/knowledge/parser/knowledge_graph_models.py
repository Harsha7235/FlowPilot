"""
FlowPilot Knowledge Graph Models.

Lightweight, deterministic graph representation for connecting:

    BlockDefinition
    SourceReference
    ImplementationKnowledge
    SourceFileKnowledge
    SourceClass
    SourceMethod
    SourceFunction
    SourceBinding

This module intentionally does NOT build the graph from source data.
It only provides the graph data structures and deterministic identity,
deduplication, provenance, and serialization.

No graph database is required.
No source code is executed.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from flowpilot.core.models import BaseModel, ModelEncoder


__all__ = [
    "GraphNodeType",
    "GraphRelationship",
    "GraphConfidence",
    "GraphProvenance",
    "GraphNode",
    "GraphEdge",
    "KnowledgeGraph",
]


# ============================================================================
# ENUMS
# ============================================================================


class GraphNodeType(str, Enum):
    """
    Supported knowledge-graph node types.

    The values are intentionally generic so that the graph can later
    represent additional FlowPilot knowledge without requiring a new
    Python class for every entity.
    """

    REPOSITORY = "repository"
    MODULE = "module"
    BLOCK = "block"
    SOURCE_FILE = "source_file"
    CLASS = "class"
    STRUCT = "struct"
    METHOD = "method"
    FUNCTION = "function"
    BINDING = "binding"
    TEST = "test"
    PARAMETER = "parameter"
    PORT = "port"


class GraphRelationship(str, Enum):
    """
    Relationships currently supported by the graph model.

    These are relationship labels only. The graph builder must provide
    evidence before creating a relationship.
    """

    CONTAINS = "contains"
    BELONGS_TO = "belongs_to"

    DEFINED_BY = "defined_by"
    IMPLEMENTED_BY = "implemented_by"
    DECLARED_IN = "declared_in"
    BOUND_BY = "bound_by"
    TESTED_BY = "tested_by"

    HAS_METHOD = "has_method"
    HAS_FUNCTION = "has_function"
    HAS_PARAMETER = "has_parameter"
    HAS_INPUT = "has_input"
    HAS_OUTPUT = "has_output"

    INCLUDES = "includes"
    INHERITS_FROM = "inherits_from"
    DEPENDS_ON = "depends_on"
    REFERENCES = "references"


class GraphConfidence(str, Enum):
    """
    Confidence/provenance classification.

    confirmed:
        Directly supported by existing FlowPilot knowledge.

    possible:
        Weak/possible evidence. This must never silently become
        confirmed.

    unknown:
        Confidence was not available.
    """

    CONFIRMED = "confirmed"
    POSSIBLE = "possible"
    UNKNOWN = "unknown"


# ============================================================================
# PROVENANCE
# ============================================================================


@dataclass(slots=True)
class GraphProvenance(BaseModel):
    """
    Provenance attached to a graph node or edge.

    This records where the graph information came from.

    source_kind examples:

        block_definition
        source_reference
        source_analysis
        source_file
        source_class
        source_method
        source_function
        source_binding
    """

    source_kind: Optional[str] = None

    source_file: Optional[Path] = None

    line_start: Optional[int] = None

    line_end: Optional[int] = None

    confidence: GraphConfidence = (
        GraphConfidence.UNKNOWN
    )

    details: Dict[str, Any] = field(
        default_factory=dict
    )

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "GraphProvenance":
        """
        Deserialize provenance while coercing Path and Enum values.
        """

        if not isinstance(data, dict):
            return cls()

        source_file = data.get(
            "source_file"
        )

        if source_file:
            source_file = Path(
                source_file
            )

        confidence = data.get(
            "confidence",
            GraphConfidence.UNKNOWN,
        )

        try:
            confidence = (
                GraphConfidence(
                    confidence
                )
            )
        except (
            ValueError,
            TypeError,
        ):
            confidence = (
                GraphConfidence.UNKNOWN
            )

        return cls(
            source_kind=data.get(
                "source_kind"
            ),
            source_file=source_file,
            line_start=data.get(
                "line_start"
            ),
            line_end=data.get(
                "line_end"
            ),
            confidence=confidence,
            details=dict(
                data.get(
                    "details",
                    {},
                )
                or {}
            ),
        )


# ============================================================================
# GRAPH NODE
# ============================================================================


@dataclass(slots=True)
class GraphNode(BaseModel):
    """
    A single deterministic knowledge-graph node.

    `id` is the canonical deterministic identity.

    `attributes` stores entity-specific information without forcing the
    graph model to know every possible property of every FlowPilot entity.
    """

    id: str

    node_type: GraphNodeType

    name: Optional[str] = None

    repository: Optional[str] = None

    module: Optional[str] = None

    block_id: Optional[str] = None

    source_file: Optional[Path] = None

    line_start: Optional[int] = None

    line_end: Optional[int] = None

    attributes: Dict[str, Any] = field(
        default_factory=dict
    )

    provenance: List[GraphProvenance] = field(
        default_factory=list
    )

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "GraphNode":
        """
        Deserialize a GraphNode including nested provenance.
        """

        if not isinstance(data, dict):
            raise TypeError(
                "GraphNode.from_dict expects a dictionary"
            )

        node_type = data.get(
            "node_type"
        )

        try:
            node_type = GraphNodeType(
                node_type
            )
        except (
            ValueError,
            TypeError,
        ):
            raise ValueError(
                f"Unknown graph node type: "
                f"{node_type!r}"
            )

        source_file = data.get(
            "source_file"
        )

        if source_file:
            source_file = Path(
                source_file
            )

        provenance = [
            GraphProvenance.from_dict(item)
            for item in (
                data.get(
                    "provenance",
                    [],
                )
                or []
            )
            if isinstance(item, dict)
        ]

        return cls(
            id=str(
                data.get(
                    "id",
                    "",
                )
            ),
            node_type=node_type,
            name=data.get(
                "name"
            ),
            repository=data.get(
                "repository"
            ),
            module=data.get(
                "module"
            ),
            block_id=data.get(
                "block_id"
            ),
            source_file=source_file,
            line_start=data.get(
                "line_start"
            ),
            line_end=data.get(
                "line_end"
            ),
            attributes=dict(
                data.get(
                    "attributes",
                    {},
                )
                or {}
            ),
            provenance=provenance,
        )

    @staticmethod
    def make_id(
        node_type: GraphNodeType | str,
        *parts: object,
    ) -> str:
        """
        Create a deterministic graph-node ID.

        Empty components are ignored.

        Example:

            GraphNode.make_id(
                GraphNodeType.BLOCK,
                "gnuradio-main",
                "gr-analog",
                "analog_agc_xx",
            )

        produces:

            block:gnuradio-main/gr-analog/analog_agc_xx
        """

        if not isinstance(
            node_type,
            GraphNodeType,
        ):
            node_type = GraphNodeType(
                node_type
            )

        clean_parts = []

        for part in parts:
            if part is None:
                continue

            value = str(part).strip()

            if not value:
                continue

            value = value.replace(
                "\\",
                "/",
            )

            clean_parts.append(
                value
            )

        return (
            f"{node_type.value}:"
            + "/".join(clean_parts)
        )

    @property
    def identity(self) -> str:
        """
        Alias for the canonical node ID.
        """

        return self.id

    def add_provenance(
        self,
        provenance: GraphProvenance,
    ) -> None:
        """
        Add provenance without duplicating an identical record.
        """

        if provenance is None:
            return

        for existing in self.provenance:

            if (
                existing.source_kind
                == provenance.source_kind
                and existing.source_file
                == provenance.source_file
                and existing.line_start
                == provenance.line_start
                and existing.line_end
                == provenance.line_end
                and existing.confidence
                == provenance.confidence
                and existing.details
                == provenance.details
            ):
                return

        self.provenance.append(
            provenance
        )


# ============================================================================
# GRAPH EDGE
# ============================================================================


@dataclass(slots=True)
class GraphEdge(BaseModel):
    """
    A directed relationship between two graph nodes.
    """

    id: str

    source: str

    target: str

    relationship: GraphRelationship

    attributes: Dict[str, Any] = field(
        default_factory=dict
    )

    provenance: List[GraphProvenance] = field(
        default_factory=list
    )

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "GraphEdge":
        """
        Deserialize a GraphEdge including nested provenance.
        """

        if not isinstance(data, dict):
            raise TypeError(
                "GraphEdge.from_dict expects a dictionary"
            )

        relationship = data.get(
            "relationship"
        )

        try:
            relationship = (
                GraphRelationship(
                    relationship
                )
            )
        except (
            ValueError,
            TypeError,
        ):
            raise ValueError(
                f"Unknown graph relationship: "
                f"{relationship!r}"
            )

        provenance = [
            GraphProvenance.from_dict(item)
            for item in (
                data.get(
                    "provenance",
                    [],
                )
                or []
            )
            if isinstance(item, dict)
        ]

        return cls(
            id=str(
                data.get(
                    "id",
                    "",
                )
            ),
            source=str(
                data.get(
                    "source",
                    "",
                )
            ),
            target=str(
                data.get(
                    "target",
                    "",
                )
            ),
            relationship=relationship,
            attributes=dict(
                data.get(
                    "attributes",
                    {},
                )
                or {}
            ),
            provenance=provenance,
        )

    @staticmethod
    def make_id(
        source: str,
        relationship: GraphRelationship | str,
        target: str,
    ) -> str:
        """
        Create a deterministic edge ID.
        """

        if not isinstance(
            relationship,
            GraphRelationship,
        ):
            relationship = (
                GraphRelationship(
                    relationship
                )
            )

        return (
            f"{source}"
            f"--{relationship.value}-->"
            f"{target}"
        )

    @property
    def identity(self) -> str:
        """
        Alias for canonical edge identity.
        """

        return self.id

    def add_provenance(
        self,
        provenance: GraphProvenance,
    ) -> None:
        """
        Add provenance without duplicating an identical record.
        """

        if provenance is None:
            return

        for existing in self.provenance:

            if (
                existing.source_kind
                == provenance.source_kind
                and existing.source_file
                == provenance.source_file
                and existing.line_start
                == provenance.line_start
                and existing.line_end
                == provenance.line_end
                and existing.confidence
                == provenance.confidence
                and existing.details
                == provenance.details
            ):
                return

        self.provenance.append(
            provenance
        )


# ============================================================================
# KNOWLEDGE GRAPH
# ============================================================================


@dataclass(slots=True)
class KnowledgeGraph(BaseModel):
    """
    Lightweight deterministic knowledge graph.

    Nodes and edges are indexed by deterministic IDs.

    The graph deliberately uses lists for serialized representation while
    maintaining private indexes for efficient duplicate detection.
    """

    nodes: List[GraphNode] = field(
        default_factory=list
    )

    edges: List[GraphEdge] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    # Internal indexes are rebuilt after deserialization.
    _node_index: Dict[str, GraphNode] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )

    _edge_index: Dict[str, GraphEdge] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        """
        Build indexes from any initial nodes/edges.
        """

        self._rebuild_indexes()

    def _rebuild_indexes(self) -> None:
        """
        Rebuild internal deterministic indexes.
        """

        self._node_index = {}
        self._edge_index = {}

        unique_nodes = []

        for node in self.nodes:

            if not node.id:
                continue

            if node.id in self._node_index:

                existing = (
                    self._node_index[
                        node.id
                    ]
                )

                self._merge_node(
                    existing,
                    node,
                )

                continue

            self._node_index[
                node.id
            ] = node

            unique_nodes.append(
                node
            )

        unique_edges = []

        for edge in self.edges:

            if not edge.id:
                continue

            if edge.id in self._edge_index:

                existing = (
                    self._edge_index[
                        edge.id
                    ]
                )

                self._merge_edge(
                    existing,
                    edge,
                )

                continue

            self._edge_index[
                edge.id
            ] = edge

            unique_edges.append(
                edge
            )

        self.nodes = unique_nodes
        self.edges = unique_edges

    # ------------------------------------------------------------------
    # NODE OPERATIONS
    # ------------------------------------------------------------------

    def add_node(
        self,
        node: GraphNode,
    ) -> GraphNode:
        """
        Add a node.

        If a node with the same deterministic ID already exists, the
        existing node is retained and compatible information/provenance
        is merged into it.

        Returns the canonical graph node.
        """

        if not isinstance(
            node,
            GraphNode,
        ):
            raise TypeError(
                "add_node expects GraphNode"
            )

        if not node.id:
            raise ValueError(
                "GraphNode.id cannot be empty"
            )

        existing = (
            self._node_index.get(
                node.id
            )
        )

        if existing is not None:

            self._merge_node(
                existing,
                node,
            )

            return existing

        self.nodes.append(
            node
        )

        self._node_index[
            node.id
        ] = node

        return node

    def get_node(
        self,
        node_id: str,
    ) -> Optional[GraphNode]:
        """
        Return a node by deterministic ID.
        """

        return self._node_index.get(
            node_id
        )

    def has_node(
        self,
        node_id: str,
    ) -> bool:
        """
        Check whether a node exists.
        """

        return node_id in self._node_index

    def get_nodes_by_type(
        self,
        node_type: GraphNodeType | str,
    ) -> List[GraphNode]:
        """
        Return nodes matching a node type.
        """

        if not isinstance(
            node_type,
            GraphNodeType,
        ):
            node_type = GraphNodeType(
                node_type
            )

        return [
            node
            for node in self.nodes
            if node.node_type
            == node_type
        ]

    # ------------------------------------------------------------------
    # EDGE OPERATIONS
    # ------------------------------------------------------------------

    def add_edge(
        self,
        edge: GraphEdge,
    ) -> GraphEdge:
        """
        Add an edge.

        Duplicate deterministic edges are merged instead of duplicated.

        Both endpoint nodes must already exist.

        Returns the canonical graph edge.
        """

        if not isinstance(
            edge,
            GraphEdge,
        ):
            raise TypeError(
                "add_edge expects GraphEdge"
            )

        if not edge.id:
            raise ValueError(
                "GraphEdge.id cannot be empty"
            )

        if not self.has_node(
            edge.source
        ):
            raise ValueError(
                "Cannot add edge: source "
                f"node does not exist: "
                f"{edge.source}"
            )

        if not self.has_node(
            edge.target
        ):
            raise ValueError(
                "Cannot add edge: target "
                f"node does not exist: "
                f"{edge.target}"
            )

        existing = (
            self._edge_index.get(
                edge.id
            )
        )

        if existing is not None:

            self._merge_edge(
                existing,
                edge,
            )

            return existing

        self.edges.append(
            edge
        )

        self._edge_index[
            edge.id
        ] = edge

        return edge

    def add_relationship(
        self,
        source: str,
        target: str,
        relationship: GraphRelationship | str,
        *,
        attributes: Optional[
            Dict[str, Any]
        ] = None,
        provenance: Optional[
            Iterable[GraphProvenance]
        ] = None,
    ) -> GraphEdge:
        """
        Convenience method for creating and adding an edge.
        """

        if not isinstance(
            relationship,
            GraphRelationship,
        ):
            relationship = (
                GraphRelationship(
                    relationship
                )
            )

        edge_id = GraphEdge.make_id(
            source,
            relationship,
            target,
        )

        edge = GraphEdge(
            id=edge_id,
            source=source,
            target=target,
            relationship=relationship,
            attributes=dict(
                attributes or {}
            ),
            provenance=list(
                provenance or []
            ),
        )

        return self.add_edge(
            edge
        )

    def get_edge(
        self,
        edge_id: str,
    ) -> Optional[GraphEdge]:
        """
        Return an edge by deterministic ID.
        """

        return self._edge_index.get(
            edge_id
        )

    def has_edge(
        self,
        edge_id: str,
    ) -> bool:
        """
        Check whether an edge exists.
        """

        return edge_id in self._edge_index

    def get_edges_by_relationship(
        self,
        relationship: GraphRelationship | str,
    ) -> List[GraphEdge]:
        """
        Return all edges matching a relationship.
        """

        if not isinstance(
            relationship,
            GraphRelationship,
        ):
            relationship = (
                GraphRelationship(
                    relationship
                )
            )

        return [
            edge
            for edge in self.edges
            if edge.relationship
            == relationship
        ]

    def get_outgoing_edges(
        self,
        node_id: str,
    ) -> List[GraphEdge]:
        """
        Return edges originating from a node.
        """

        return [
            edge
            for edge in self.edges
            if edge.source
            == node_id
        ]

    def get_incoming_edges(
        self,
        node_id: str,
    ) -> List[GraphEdge]:
        """
        Return edges pointing to a node.
        """

        return [
            edge
            for edge in self.edges
            if edge.target
            == node_id
        ]

    # ------------------------------------------------------------------
    # MERGING
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_node(
        target: GraphNode,
        incoming: GraphNode,
    ) -> None:
        """
        Merge non-destructively into an existing node.
        """

        if target.name is None:
            target.name = incoming.name

        if target.repository is None:
            target.repository = (
                incoming.repository
            )

        if target.module is None:
            target.module = (
                incoming.module
            )

        if target.block_id is None:
            target.block_id = (
                incoming.block_id
            )

        if target.source_file is None:
            target.source_file = (
                incoming.source_file
            )

        if target.line_start is None:
            target.line_start = (
                incoming.line_start
            )

        if target.line_end is None:
            target.line_end = (
                incoming.line_end
            )

        for key, value in (
            incoming.attributes.items()
        ):

            if key not in target.attributes:

                target.attributes[
                    key
                ] = value

        for provenance in (
            incoming.provenance
        ):

            target.add_provenance(
                provenance
            )

    @staticmethod
    def _merge_edge(
        target: GraphEdge,
        incoming: GraphEdge,
    ) -> None:
        """
        Merge non-destructively into an existing edge.
        """

        for key, value in (
            incoming.attributes.items()
        ):

            if key not in target.attributes:

                target.attributes[
                    key
                ] = value

        for provenance in (
            incoming.provenance
        ):

            target.add_provenance(
                provenance
            )

    # ------------------------------------------------------------------
    # SERIALIZATION
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the complete graph to plain dictionaries.

        This explicit implementation avoids relying on shallow
        BaseModel serialization for nested graph objects.
        """

        return {
            "nodes": [
                self._node_to_dict(
                    node
                )
                for node in self.nodes
            ],
            "edges": [
                self._edge_to_dict(
                    edge
                )
                for edge in self.edges
            ],
            "metadata": dict(
                self.metadata
            ),
        }

    @staticmethod
    def _node_to_dict(
        node: GraphNode,
    ) -> Dict[str, Any]:
        """
        Serialize one node.
        """

        return {
            "id": node.id,
            "node_type": node.node_type.value,
            "name": node.name,
            "repository": node.repository,
            "module": node.module,
            "block_id": node.block_id,
            "source_file": (
                str(node.source_file)
                if node.source_file is not None
                else None
            ),
            "line_start": node.line_start,
            "line_end": node.line_end,
            "attributes": dict(
                node.attributes
            ),
            "provenance": [
                {
                    "source_kind":
                        item.source_kind,
                    "source_file": (
                        str(
                            item.source_file
                        )
                        if item.source_file
                        is not None
                        else None
                    ),
                    "line_start":
                        item.line_start,
                    "line_end":
                        item.line_end,
                    "confidence":
                        item.confidence.value,
                    "details":
                        dict(
                            item.details
                        ),
                }
                for item in node.provenance
            ],
        }

    @staticmethod
    def _edge_to_dict(
        edge: GraphEdge,
    ) -> Dict[str, Any]:
        """
        Serialize one edge.
        """

        return {
            "id": edge.id,
            "source": edge.source,
            "target": edge.target,
            "relationship":
                edge.relationship.value,
            "attributes": dict(
                edge.attributes
            ),
            "provenance": [
                {
                    "source_kind":
                        item.source_kind,
                    "source_file": (
                        str(
                            item.source_file
                        )
                        if item.source_file
                        is not None
                        else None
                    ),
                    "line_start":
                        item.line_start,
                    "line_end":
                        item.line_end,
                    "confidence":
                        item.confidence.value,
                    "details":
                        dict(
                            item.details
                        ),
                }
                for item in edge.provenance
            ],
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "KnowledgeGraph":
        """
        Deserialize a complete graph including all nested models.
        """

        if not isinstance(
            data,
            dict,
        ):
            raise TypeError(
                "KnowledgeGraph.from_dict "
                "expects a dictionary"
            )

        nodes = [
            GraphNode.from_dict(
                item
            )
            for item in (
                data.get(
                    "nodes",
                    [],
                )
                or []
            )
            if isinstance(item, dict)
        ]

        edges = [
            GraphEdge.from_dict(
                item
            )
            for item in (
                data.get(
                    "edges",
                    [],
                )
                or []
            )
            if isinstance(item, dict)
        ]

        return cls(
            nodes=nodes,
            edges=edges,
            metadata=dict(
                data.get(
                    "metadata",
                    {},
                )
                or {}
            ),
        )

    # ------------------------------------------------------------------
    # SUMMARY / VALIDATION
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """
        Return compact graph statistics.
        """

        node_types: Dict[str, int] = {}

        for node in self.nodes:

            key = node.node_type.value

            node_types[key] = (
                node_types.get(
                    key,
                    0,
                )
                + 1
            )

        relationships: Dict[str, int] = {}

        for edge in self.edges:

            key = (
                edge.relationship.value
            )

            relationships[key] = (
                relationships.get(
                    key,
                    0,
                )
                + 1
            )

        return {
            "nodes": len(
                self.nodes
            ),
            "edges": len(
                self.edges
            ),
            "node_types": node_types,
            "relationships":
                relationships,
            "metadata":
                dict(self.metadata),
        }

    def validate(self) -> List[str]:
        """
        Validate graph consistency.

        Returns an empty list when the graph is valid.
        """

        errors: List[str] = []

        # Node IDs must be unique.
        node_ids = set()

        for node in self.nodes:

            if not node.id:

                errors.append(
                    "Graph contains node "
                    "with empty ID"
                )

                continue

            if node.id in node_ids:

                errors.append(
                    "Duplicate node ID: "
                    f"{node.id}"
                )

            node_ids.add(
                node.id
            )

        # Edge IDs must be unique.
        edge_ids = set()

        for edge in self.edges:

            if not edge.id:

                errors.append(
                    "Graph contains edge "
                    "with empty ID"
                )

                continue

            if edge.id in edge_ids:

                errors.append(
                    "Duplicate edge ID: "
                    f"{edge.id}"
                )

            edge_ids.add(
                edge.id
            )

            if edge.source not in node_ids:

                errors.append(
                    "Edge source does not "
                    "exist: "
                    f"{edge.source}"
                )

            if edge.target not in node_ids:

                errors.append(
                    "Edge target does not "
                    "exist: "
                    f"{edge.target}"
                )

        return errors

    def clear(self) -> None:
        """
        Remove all nodes and edges while preserving metadata.
        """

        self.nodes.clear()
        self.edges.clear()
        self._node_index.clear()
        self._edge_index.clear()