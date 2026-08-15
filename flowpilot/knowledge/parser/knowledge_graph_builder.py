from __future__ import annotations

"""
FlowPilot Knowledge Graph Builder.

Builds a KnowledgeGraph from ImplementationKnowledge records.

The implementation knowledge pipeline is:

    SourceReference
        |
        v
    SourceCodeAnalyzer
        |
        v
    ImplementationKnowledge
        |
        v
    ImplementationStore
        |
        v
    KnowledgeGraphBuilder
        |
        v
    KnowledgeGraph

This module intentionally uses only the node and relationship types
defined by flowpilot.knowledge.parser.knowledge_graph_models.

Supported graph node types:

    repository
    module
    block
    source_file
    class
    struct
    method
    function
    binding
    test
    parameter
    port

Supported relationships:

    contains
    belongs_to
    defined_by
    implemented_by
    declared_in
    bound_by
    tested_by
    has_method
    has_function
    has_parameter
    has_input
    has_output
    includes
    inherits_from
    depends_on
    references

Important design decision:

There is NO dependency node in the actual project graph model.

Therefore:

    includes
    dependencies

are retained as attributes on the relevant source-file node and are
represented through graph relationships only when an existing graph
entity is available.

The builder never invents a GraphNodeType.DEPENDENCY.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
)
import logging


from flowpilot.core.utils import configure_logger

from flowpilot.knowledge.parser.source_code_models import (
    ImplementationKnowledge,
    SourceBinding,
    SourceClass,
    SourceFileKnowledge,
    SourceFunction,
    SourceMethod,
)

from flowpilot.knowledge.parser.knowledge_graph_models import (
    KnowledgeGraph,
    GraphNode,
    GraphEdge,
    GraphNodeType,
    GraphRelationship,
)


__all__ = [
    "KnowledgeGraphBuilder",
    "KnowledgeGraphBuildResult",
    "build_knowledge_graph",
]


# ============================================================================
# CONSTANTS
# ============================================================================


GRAPH_VERSION = 2


# ============================================================================
# BUILD RESULT
# ============================================================================


@dataclass(slots=True)
class KnowledgeGraphBuildResult:
    """
    Result returned by KnowledgeGraphBuilder.build().
    """

    graph: KnowledgeGraph

    blocks_processed: int = 0

    implementation_records_processed: int = 0

    nodes_created: int = 0

    edges_created: int = 0

    errors: List[str] = field(
        default_factory=list
    )

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> Dict[str, Any]:
        """
        Return a compact machine-readable summary.
        """

        return {
            "blocks_processed": (
                self.blocks_processed
            ),
            "implementation_records_processed": (
                self.implementation_records_processed
            ),
            "nodes_created": (
                self.nodes_created
            ),
            "edges_created": (
                self.edges_created
            ),
            "errors": len(
                self.errors
            ),
            "success": self.success,
        }


# ============================================================================
# KNOWLEDGE GRAPH BUILDER
# ============================================================================


class KnowledgeGraphBuilder:
    """
    Convert ImplementationKnowledge records into KnowledgeGraph objects.

    The builder is intentionally conservative.

    It does NOT:

    * parse source code itself;
    * invent classes;
    * invent methods;
    * invent dependencies;
    * invent graph node types;
    * overwrite the source analyzer's information.

    It DOES:

    * create repository/module/block hierarchy;
    * create source-file nodes;
    * create class/struct nodes;
    * create method nodes;
    * create standalone function nodes;
    * create binding nodes;
    * create test nodes where source data identifies tests;
    * create inheritance relationships;
    * preserve includes and dependencies;
    * preserve source provenance;
    * create deterministic graph IDs;
    * rely on KnowledgeGraph for duplicate handling.
    """

    GRAPH_VERSION = GRAPH_VERSION

    def __init__(
        self,
        *,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.logger = logger or configure_logger(
            "flowpilot.knowledge.parser.knowledge_graph_builder"
        )

    # =========================================================================
    # PUBLIC BUILD API
    # =========================================================================

    def build(
        self,
        implementation_records: Iterable[
            ImplementationKnowledge
        ],
        source_references: Optional[
            Iterable[Any]
        ] = None,
    ) -> KnowledgeGraphBuildResult:
        """
        Build one KnowledgeGraph from implementation records.
        """

        graph = self._create_graph()

        references_by_key = (
            self._index_references(
                source_references or []
            )
        )

        records = list(
            implementation_records
        )

        result = KnowledgeGraphBuildResult(
            graph=graph
        )

        for knowledge in records:
            try:
                self._add_implementation_knowledge(
                    graph=graph,
                    knowledge=knowledge,
                    references_by_key=(
                        references_by_key
                    ),
                )

                result.blocks_processed += 1

                result.implementation_records_processed += 1

            except Exception as exc:
                block_id = getattr(
                    knowledge,
                    "block_id",
                    None,
                )

                message = (
                    "Failed to build knowledge graph "
                    f"for {block_id or '<unknown>'}: {exc}"
                )

                self.logger.exception(
                    message
                )

                result.errors.append(
                    message
                )

        result.nodes_created = len(
            graph.nodes
        )

        result.edges_created = len(
            graph.edges
        )

        return result

    def build_one(
        self,
        knowledge: ImplementationKnowledge,
        source_reference: Optional[Any] = None,
    ) -> KnowledgeGraphBuildResult:
        """
        Build a graph from a single ImplementationKnowledge record.
        """

        references: List[Any] = []

        if source_reference is not None:
            references.append(
                source_reference
            )

        return self.build(
            [knowledge],
            source_references=references,
        )

    def build_from_records(
        self,
        implementation_records: Iterable[
            ImplementationKnowledge
        ],
    ) -> KnowledgeGraphBuildResult:
        """
        Convenience API.
        """

        return self.build(
            implementation_records
        )

    # =========================================================================
    # GRAPH CREATION
    # =========================================================================

    def _create_graph(self) -> KnowledgeGraph:
        """
        Create the project's actual KnowledgeGraph model.

        The graph model used by this project supports nodes, edges and
        metadata.
        """

        return KnowledgeGraph(
            nodes=[],
            edges=[],
            metadata={
                "version": self.GRAPH_VERSION,
                "builder": self.__class__.__name__,
            },
        )

    # =========================================================================
    # REFERENCE INDEXING
    # =========================================================================

    def _index_references(
        self,
        references: Iterable[Any],
    ) -> Dict[
        Tuple[str, str, str],
        Any,
    ]:
        """
        Index SourceReference-like objects by repository/module/block.
        """

        result: Dict[
            Tuple[str, str, str],
            Any,
        ] = {}

        for reference in references:
            key = self._identity_key(
                getattr(
                    reference,
                    "repository",
                    None,
                ),
                getattr(
                    reference,
                    "module",
                    None,
                ),
                getattr(
                    reference,
                    "block_id",
                    None,
                ),
            )

            if key is not None:
                result[key] = reference

        return result

    @staticmethod
    def _identity_key(
        repository: Optional[str],
        module: Optional[str],
        block_id: Optional[str],
    ) -> Optional[
        Tuple[str, str, str]
    ]:
        if (
            not repository
            or not module
            or not block_id
        ):
            return None

        return (
            str(repository),
            str(module),
            str(block_id),
        )

    # =========================================================================
    # IMPLEMENTATION KNOWLEDGE
    # =========================================================================

    def _add_implementation_knowledge(
        self,
        graph: KnowledgeGraph,
        knowledge: ImplementationKnowledge,
        references_by_key: Dict[
            Tuple[str, str, str],
            Any,
        ],
    ) -> None:
        """
        Add one complete ImplementationKnowledge record.
        """

        repository = (
            knowledge.repository
            or "unknown"
        )

        module = (
            knowledge.module
            or "unknown"
        )

        block_id = (
            knowledge.block_id
            or "unknown"
        )

        # ---------------------------------------------------------------------
        # Repository
        # ---------------------------------------------------------------------

        repository_node_id = (
            self._repository_node_id(
                repository
            )
        )

        self._add_node(
            graph,
            self._make_node(
                node_type=GraphNodeType.REPOSITORY,
                node_id=repository_node_id,
                name=repository,
                repository=repository,
                attributes={
                    "repository": repository,
                },
            ),
        )

        # ---------------------------------------------------------------------
        # Module
        # ---------------------------------------------------------------------

        module_node_id = (
            self._module_node_id(
                repository,
                module,
            )
        )

        self._add_node(
            graph,
            self._make_node(
                node_type=GraphNodeType.MODULE,
                node_id=module_node_id,
                name=module,
                repository=repository,
                module=module,
                attributes={
                    "repository": repository,
                    "module": module,
                },
            ),
        )

        self._add_relationship(
            graph,
            repository_node_id,
            module_node_id,
            "contains",
        )

        # ---------------------------------------------------------------------
        # Block
        # ---------------------------------------------------------------------

        block_node_id = (
            self._block_node_id(
                repository,
                module,
                block_id,
            )
        )

        self._add_node(
            graph,
            self._make_node(
                node_type=GraphNodeType.BLOCK,
                node_id=block_node_id,
                name=block_id,
                repository=repository,
                module=module,
                block_id=block_id,
                attributes={
                    "repository": repository,
                    "module": module,
                    "block_id": block_id,
                    "analyzed_file_count": (
                        knowledge.analyzed_file_count
                    ),
                    "successful_file_count": (
                        knowledge.successful_file_count
                    ),
                    "failed_file_count": (
                        knowledge.failed_file_count
                    ),
                    "unsupported_file_count": (
                        knowledge.unsupported_file_count
                    ),
                    "classes_found": (
                        knowledge.classes_found
                    ),
                    "methods_found": (
                        knowledge.methods_found
                    ),
                    "functions_found": (
                        knowledge.functions_found
                    ),
                    "bindings_found": (
                        knowledge.bindings_found
                    ),
                    "errors": list(
                        knowledge.errors
                    ),
                },
            ),
        )

        self._add_relationship(
            graph,
            module_node_id,
            block_node_id,
            "contains",
        )

        # ---------------------------------------------------------------------
        # Source reference provenance
        # ---------------------------------------------------------------------

        reference = references_by_key.get(
            self._identity_key(
                repository,
                module,
                block_id,
            )
        )

        if reference is not None:
            self._attach_reference_metadata(
                graph,
                block_node_id,
                reference,
            )

        # ---------------------------------------------------------------------
        # Source files
        # ---------------------------------------------------------------------

        for source_file in (
            knowledge.source_files
        ):
            self._add_source_file(
                graph=graph,
                knowledge=knowledge,
                block_node_id=block_node_id,
                repository=repository,
                module=module,
                source_file=source_file,
            )

    # =========================================================================
    # SOURCE FILE
    # =========================================================================

    def _add_source_file(
        self,
        *,
        graph: KnowledgeGraph,
        knowledge: ImplementationKnowledge,
        block_node_id: str,
        repository: str,
        module: str,
        source_file: SourceFileKnowledge,
    ) -> None:
        path = self._source_path(
            source_file
        )

        source_node_id = (
            self._source_file_node_id(
                repository,
                module,
                path,
            )
        )

        source_attributes: Dict[
            str,
            Any,
        ] = {
            "repository": repository,
            "module": module,
            "block_id": knowledge.block_id,
            "language": self._enum_value(
                source_file.language
            ),
            "parse_status": self._enum_value(
                source_file.parse_status
            ),
            "parse_errors": list(
                source_file.parse_errors
            ),
            "includes": list(
                source_file.includes
            ),
            "namespaces": list(
                source_file.namespaces
            ),
            "module_level_variables": list(
                source_file.module_level_variables
            ),
            "referenced_gnuradio_classes": list(
                source_file.referenced_gnuradio_classes
            ),
            "dependencies": list(
                source_file.dependencies
            ),
            "line_count": (
                source_file.line_count
            ),
        }

        source_node = self._make_node(
            node_type=GraphNodeType.SOURCE_FILE,
            node_id=source_node_id,
            name=path,
            repository=repository,
            module=module,
            block_id=knowledge.block_id,
            source_file=(
                self._as_path(path)
            ),
            attributes=source_attributes,
        )

        self._add_node(
            graph,
            source_node,
        )

        self._add_relationship(
            graph,
            block_node_id,
            source_node_id,
            "implemented_by",
        )

        # ---------------------------------------------------------------------
        # Includes
        #
        # IMPORTANT:
        # GraphNodeType has NO DEPENDENCY value.
        #
        # Therefore includes are retained as source-file metadata rather than
        # creating fake dependency nodes.
        # ---------------------------------------------------------------------

        self._store_string_attributes(
            graph=graph,
            node_id=source_node_id,
            attribute_name="includes",
            values=source_file.includes,
        )

        self._store_string_attributes(
            graph=graph,
            node_id=source_node_id,
            attribute_name="dependencies",
            values=source_file.dependencies,
        )

        # ---------------------------------------------------------------------
        # Classes
        # ---------------------------------------------------------------------

        for source_class in (
            source_file.classes
        ):
            self._add_class(
                graph=graph,
                source_node_id=source_node_id,
                repository=repository,
                module=module,
                block_id=knowledge.block_id,
                source_class=source_class,
            )

        # ---------------------------------------------------------------------
        # Functions
        # ---------------------------------------------------------------------

        for function in (
            source_file.functions
        ):
            self._add_function(
                graph=graph,
                source_node_id=source_node_id,
                repository=repository,
                module=module,
                block_id=knowledge.block_id,
                function=function,
            )

        # ---------------------------------------------------------------------
        # Bindings
        # ---------------------------------------------------------------------

        for binding in (
            source_file.bindings
        ):
            self._add_binding(
                graph=graph,
                source_node_id=source_node_id,
                repository=repository,
                module=module,
                block_id=knowledge.block_id,
                binding=binding,
            )

        # ---------------------------------------------------------------------
        # GNU Radio referenced classes
        # ---------------------------------------------------------------------

        for referenced_class in (
            source_file.referenced_gnuradio_classes
        ):
            self._add_referenced_class(
                graph=graph,
                source_node_id=source_node_id,
                repository=repository,
                module=module,
                block_id=knowledge.block_id,
                class_name=referenced_class,
            )

    # =========================================================================
    # CLASS
    # =========================================================================

    def _add_class(
        self,
        *,
        graph: KnowledgeGraph,
        source_node_id: str,
        repository: str,
        module: str,
        block_id: Optional[str],
        source_class: SourceClass,
    ) -> None:
        if not source_class.name:
            return

        kind = (
            source_class.kind
            or "class"
        )

        node_type = (
            GraphNodeType.STRUCT
            if kind.lower() == "struct"
            else GraphNodeType.CLASS
        )

        namespace = (
            source_class.namespace
            or ""
        )

        class_node_id = (
            self._class_node_id(
                repository=repository,
                module=module,
                block_id=block_id,
                namespace=namespace,
                class_name=source_class.name,
            )
        )

        class_attributes: Dict[
            str,
            Any,
        ] = {
            "kind": kind,
            "namespace": (
                source_class.namespace
            ),
            "base_classes": list(
                source_class.base_classes
            ),
            "member_variables": list(
                source_class.member_variables
            ),
            "decorators": list(
                source_class.decorators
            ),
        }

        class_node = self._make_node(
            node_type=node_type,
            node_id=class_node_id,
            name=source_class.name,
            repository=repository,
            module=module,
            block_id=block_id,
            source_file=(
                self._as_path(
                    source_class.source_file
                )
            ),
            line_start=source_class.line_start,
            line_end=source_class.line_end,
            attributes=class_attributes,
        )

        self._add_node(
            graph,
            class_node,
        )

        self._add_relationship(
            graph,
            source_node_id,
            class_node_id,
            "declared_in",
        )

        # ---------------------------------------------------------------------
        # Inheritance
        # ---------------------------------------------------------------------

        for base_class in (
            source_class.base_classes
        ):
            self._add_inheritance(
                graph=graph,
                class_node_id=class_node_id,
                repository=repository,
                module=module,
                block_id=block_id,
                base_class=base_class,
            )

        # ---------------------------------------------------------------------
        # Methods
        # ---------------------------------------------------------------------

        for method in (
            source_class.methods
        ):
            self._add_method(
                graph=graph,
                class_node_id=class_node_id,
                repository=repository,
                module=module,
                block_id=block_id,
                class_name=source_class.name,
                method=method,
            )

    # =========================================================================
    # METHOD
    # =========================================================================

    def _add_method(
        self,
        *,
        graph: KnowledgeGraph,
        class_node_id: str,
        repository: str,
        module: str,
        block_id: Optional[str],
        class_name: str,
        method: SourceMethod,
    ) -> None:
        if not method.name:
            return

        signature = (
            method.signature
            or ""
        )

        method_node_id = (
            self._method_node_id(
                repository=repository,
                module=module,
                block_id=block_id,
                class_name=class_name,
                method_name=method.name,
                signature=signature,
            )
        )

        attributes: Dict[
            str,
            Any,
        ] = {
            "signature": (
                method.signature
            ),
            "return_type": (
                method.return_type
            ),
            "parameters": list(
                method.parameters
            ),
            "access": method.access,
            "is_static": method.is_static,
            "is_const": method.is_const,
            "is_virtual": method.is_virtual,
            "is_override": method.is_override,
            "is_constructor": (
                method.is_constructor
            ),
            "is_destructor": (
                method.is_destructor
            ),
        }

        method_node = self._make_node(
            node_type=GraphNodeType.METHOD,
            node_id=method_node_id,
            name=method.name,
            repository=repository,
            module=module,
            block_id=block_id,
            source_file=(
                self._as_path(
                    method.source_file
                )
            ),
            line_start=method.line_start,
            line_end=method.line_end,
            attributes=attributes,
        )

        self._add_node(
            graph,
            method_node,
        )

        self._add_relationship(
            graph,
            class_node_id,
            method_node_id,
            "has_method",
        )

        # ---------------------------------------------------------------------
        # Parameters
        # ---------------------------------------------------------------------

        for index, parameter in enumerate(
            method.parameters
        ):
            self._add_parameter(
                graph=graph,
                method_node_id=method_node_id,
                repository=repository,
                module=module,
                block_id=block_id,
                owner_name=class_name,
                parameter=parameter,
                index=index,
            )

    # =========================================================================
    # FUNCTION
    # =========================================================================

    def _add_function(
        self,
        *,
        graph: KnowledgeGraph,
        source_node_id: str,
        repository: str,
        module: str,
        block_id: Optional[str],
        function: SourceFunction,
    ) -> None:
        if not function.name:
            return

        signature = (
            function.signature
            or ""
        )

        function_node_id = (
            self._function_node_id(
                repository=repository,
                module=module,
                block_id=block_id,
                function_name=function.name,
                signature=signature,
            )
        )

        function_node = self._make_node(
            node_type=GraphNodeType.FUNCTION,
            node_id=function_node_id,
            name=function.name,
            repository=repository,
            module=module,
            block_id=block_id,
            source_file=(
                self._as_path(
                    function.source_file
                )
            ),
            line_start=function.line_start,
            line_end=function.line_end,
            attributes={
                "signature": (
                    function.signature
                ),
                "return_type": (
                    function.return_type
                ),
                "parameters": list(
                    function.parameters
                ),
                "decorators": list(
                    function.decorators
                ),
            },
        )

        self._add_node(
            graph,
            function_node,
        )

        self._add_relationship(
            graph,
            source_node_id,
            function_node_id,
            "has_function",
        )

        for index, parameter in enumerate(
            function.parameters
        ):
            self._add_parameter(
                graph=graph,
                method_node_id=function_node_id,
                repository=repository,
                module=module,
                block_id=block_id,
                owner_name=function.name,
                parameter=parameter,
                index=index,
            )

    # =========================================================================
    # PARAMETERS
    # =========================================================================

    def _add_parameter(
        self,
        *,
        graph: KnowledgeGraph,
        method_node_id: str,
        repository: str,
        module: str,
        block_id: Optional[str],
        owner_name: str,
        parameter: str,
        index: int,
    ) -> None:
        parameter = str(
            parameter
        ).strip()

        if not parameter:
            return

        parameter_node_id = (
            self._parameter_node_id(
                repository=repository,
                module=module,
                block_id=block_id,
                owner_name=owner_name,
                index=index,
                parameter=parameter,
            )
        )

        self._add_node(
            graph,
            self._make_node(
                node_type=GraphNodeType.PARAMETER,
                node_id=parameter_node_id,
                name=parameter,
                repository=repository,
                module=module,
                block_id=block_id,
                attributes={
                    "parameter": parameter,
                    "index": index,
                    "owner": owner_name,
                },
            ),
        )

        self._add_relationship(
            graph,
            method_node_id,
            parameter_node_id,
            "has_parameter",
        )

    # =========================================================================
    # BINDINGS
    # =========================================================================

    def _add_binding(
        self,
        *,
        graph: KnowledgeGraph,
        source_node_id: str,
        repository: str,
        module: str,
        block_id: Optional[str],
        binding: SourceBinding,
    ) -> None:
        binding_key = "|".join(
            [
                *binding.cpp_classes,
                *binding.python_classes,
                *binding.python_module_names,
                *binding.exposed_methods,
            ]
        )

        if not binding_key:
            binding_key = "binding"

        binding_node_id = (
            self._binding_node_id(
                repository=repository,
                module=module,
                block_id=block_id,
                binding_key=binding_key,
                line_start=binding.line_start,
            )
        )

        if binding.python_classes:
            binding_name = (
                binding.python_classes[0]
            )
        elif binding.cpp_classes:
            binding_name = (
                binding.cpp_classes[0]
            )
        elif binding.python_module_names:
            binding_name = (
                binding.python_module_names[0]
            )
        else:
            binding_name = "binding"

        binding_node = self._make_node(
            node_type=GraphNodeType.BINDING,
            node_id=binding_node_id,
            name=binding_name,
            repository=repository,
            module=module,
            block_id=block_id,
            source_file=(
                self._as_path(
                    binding.source_file
                )
            ),
            line_start=binding.line_start,
            line_end=binding.line_end,
            attributes={
                "cpp_classes": list(
                    binding.cpp_classes
                ),
                "python_classes": list(
                    binding.python_classes
                ),
                "exposed_methods": list(
                    binding.exposed_methods
                ),
                "python_module_names": list(
                    binding.python_module_names
                ),
                "includes": list(
                    binding.includes
                ),
            },
        )

        self._add_node(
            graph,
            binding_node,
        )

        self._add_relationship(
            graph,
            source_node_id,
            binding_node_id,
            "bound_by",
        )

        # ---------------------------------------------------------------------
        # C++ classes exposed by binding
        # ---------------------------------------------------------------------

        for cpp_class in (
            binding.cpp_classes
        ):
            if not cpp_class:
                continue

            class_node_id = (
                self._external_class_node_id(
                    repository,
                    module,
                    block_id,
                    cpp_class,
                )
            )

            self._add_node(
                graph,
                self._make_node(
                    node_type=GraphNodeType.CLASS,
                    node_id=class_node_id,
                    name=cpp_class,
                    repository=repository,
                    module=module,
                    block_id=block_id,
                    attributes={
                        "external_reference": True,
                        "binding_reference": True,
                    },
                ),
            )

            self._add_relationship(
                graph,
                binding_node_id,
                class_node_id,
                "references",
            )

        # ---------------------------------------------------------------------
        # Exposed methods
        # ---------------------------------------------------------------------

        for exposed_method in (
            binding.exposed_methods
        ):
            if not exposed_method:
                continue

            method_node_id = (
                self._external_method_node_id(
                    repository,
                    module,
                    block_id,
                    exposed_method,
                )
            )

            self._add_node(
                graph,
                self._make_node(
                    node_type=GraphNodeType.METHOD,
                    node_id=method_node_id,
                    name=exposed_method,
                    repository=repository,
                    module=module,
                    block_id=block_id,
                    attributes={
                        "binding_exposed": True,
                    },
                ),
            )

            self._add_relationship(
                graph,
                binding_node_id,
                method_node_id,
                "references",
            )

    # =========================================================================
    # INHERITANCE
    # =========================================================================

    def _add_inheritance(
        self,
        *,
        graph: KnowledgeGraph,
        class_node_id: str,
        repository: str,
        module: str,
        block_id: Optional[str],
        base_class: str,
    ) -> None:
        base_class = str(
            base_class
        ).strip()

        if not base_class:
            return

        base_node_id = (
            self._external_class_node_id(
                repository,
                module,
                block_id,
                base_class,
            )
        )

        self._add_node(
            graph,
            self._make_node(
                node_type=GraphNodeType.CLASS,
                node_id=base_node_id,
                name=base_class,
                repository=repository,
                module=module,
                block_id=block_id,
                attributes={
                    "external_reference": True,
                    "inheritance_reference": True,
                },
            ),
        )

        self._add_relationship(
            graph,
            class_node_id,
            base_node_id,
            "inherits_from",
        )

    # =========================================================================
    # REFERENCED GNU RADIO CLASS
    # =========================================================================

    def _add_referenced_class(
        self,
        *,
        graph: KnowledgeGraph,
        source_node_id: str,
        repository: str,
        module: str,
        block_id: Optional[str],
        class_name: str,
    ) -> None:
        class_name = str(
            class_name
        ).strip()

        if not class_name:
            return

        class_node_id = (
            self._external_class_node_id(
                repository,
                module,
                block_id,
                class_name,
            )
        )

        self._add_node(
            graph,
            self._make_node(
                node_type=GraphNodeType.CLASS,
                node_id=class_node_id,
                name=class_name,
                repository=repository,
                module=module,
                block_id=block_id,
                attributes={
                    "external_reference": True,
                    "gnuradio_reference": True,
                },
            ),
        )

        self._add_relationship(
            graph,
            source_node_id,
            class_node_id,
            "references",
        )

    # =========================================================================
    # SOURCE FILE METADATA
    # =========================================================================

    def _store_string_attributes(
        self,
        *,
        graph: KnowledgeGraph,
        node_id: str,
        attribute_name: str,
        values: Sequence[str],
    ) -> None:
        """
        Preserve a list-valued source attribute without creating a node type
        that does not exist in the graph schema.
        """

        node = self._get_node(
            graph,
            node_id,
        )

        if node is None:
            return

        cleaned: List[str] = []

        for value in values:
            value = str(
                value
            ).strip()

            if (
                value
                and value not in cleaned
            ):
                cleaned.append(
                    value
                )

        existing = node.attributes.get(
            attribute_name
        )

        if isinstance(
            existing,
            list,
        ):
            for value in cleaned:
                if value not in existing:
                    existing.append(
                        value
                    )
        else:
            node.attributes[
                attribute_name
            ] = cleaned

    # =========================================================================
    # NODE CREATION
    # =========================================================================

    def _make_node(
        self,
        *,
        node_type: GraphNodeType,
        node_id: str,
        name: str,
        repository: Optional[str] = None,
        module: Optional[str] = None,
        block_id: Optional[str] = None,
        source_file: Optional[Path] = None,
        line_start: Optional[int] = None,
        line_end: Optional[int] = None,
        attributes: Optional[
            Dict[str, Any]
        ] = None,
    ) -> GraphNode:
        """
        Create a GraphNode using the project's model.

        The current project graph model accepts the fields used here.
        """

        return GraphNode(
            id=node_id,
            node_type=node_type,
            name=name,
            repository=repository,
            module=module,
            block_id=block_id,
            source_file=source_file,
            line_start=line_start,
            line_end=line_end,
            attributes=dict(
                attributes or {}
            ),
        )

    def _add_node(
        self,
        graph: KnowledgeGraph,
        node: GraphNode,
    ) -> GraphNode:
        """
        Add a node through KnowledgeGraph.

        Duplicate-node handling remains centralized in the graph model.
        """

        return graph.add_node(
            node
        )

    # =========================================================================
    # EDGE CREATION
    # =========================================================================

    def _relationship(
        self,
        relationship: str,
    ) -> GraphRelationship:
        """
        Convert a relationship string to the real project enum.
        """

        aliases = {
            "implemented_by": (
                GraphRelationship.IMPLEMENTED_BY
            ),
            "declared_in": (
                GraphRelationship.DECLARED_IN
            ),
            "bound_by": (
                GraphRelationship.BOUND_BY
            ),
            "tested_by": (
                GraphRelationship.TESTED_BY
            ),
            "has_method": (
                GraphRelationship.HAS_METHOD
            ),
            "has_function": (
                GraphRelationship.HAS_FUNCTION
            ),
            "has_parameter": (
                GraphRelationship.HAS_PARAMETER
            ),
            "has_input": (
                GraphRelationship.HAS_INPUT
            ),
            "has_output": (
                GraphRelationship.HAS_OUTPUT
            ),
            "includes": (
                GraphRelationship.INCLUDES
            ),
            "inherits_from": (
                GraphRelationship.INHERITS_FROM
            ),
            "depends_on": (
                GraphRelationship.DEPENDS_ON
            ),
            "references": (
                GraphRelationship.REFERENCES
            ),
            "contains": (
                GraphRelationship.CONTAINS
            ),
            "belongs_to": (
                GraphRelationship.BELONGS_TO
            ),
            "defined_by": (
                GraphRelationship.DEFINED_BY
            ),
        }

        if relationship not in aliases:
            raise ValueError(
                f"Unsupported graph relationship: "
                f"{relationship}"
            )

        return aliases[
            relationship
        ]

    def _add_relationship(
        self,
        graph: KnowledgeGraph,
        source: str,
        target: str,
        relationship: str,
        *,
        attributes: Optional[
            Dict[str, Any]
        ] = None,
    ) -> GraphEdge:
        """
        Create and add one GraphEdge using the actual project model.
        """

        relationship_enum = (
            self._relationship(
                relationship
            )
        )

        edge_id = (
            GraphEdge.make_id(
                source,
                relationship_enum,
                target,
            )
        )

        edge = GraphEdge(
            id=edge_id,
            source=source,
            target=target,
            relationship=relationship_enum,
            attributes=dict(
                attributes or {}
            ),
        )

        return graph.add_edge(
            edge
        )

    # =========================================================================
    # REFERENCE METADATA
    # =========================================================================

    def _attach_reference_metadata(
        self,
        graph: KnowledgeGraph,
        block_node_id: str,
        reference: Any,
    ) -> None:
        """
        Preserve SourceReference information on the block node.

        This does not require a separate provenance node type.
        """

        node = self._get_node(
            graph,
            block_node_id,
        )

        if node is None:
            return

        metadata = node.attributes.setdefault(
            "source_reference",
            {},
        )

        if not isinstance(
            metadata,
            dict,
        ):
            metadata = {}

            node.attributes[
                "source_reference"
            ] = metadata

        candidate_fields = (
            "repository",
            "module",
            "block_id",
            "matched_file_count",
            "confirmed_file_count",
            "possible_file_count",
        )

        for field_name in candidate_fields:
            if not hasattr(
                reference,
                field_name,
            ):
                continue

            value = getattr(
                reference,
                field_name,
            )

            if value is not None:
                metadata[
                    field_name
                ] = self._clean_value(
                    value
                )

    # =========================================================================
    # NODE LOOKUPS
    # =========================================================================

    @staticmethod
    def _get_node(
        graph: KnowledgeGraph,
        node_id: str,
    ) -> Optional[GraphNode]:
        """
        Retrieve a graph node.

        Supports graph models that expose get_node() as well as the current
        list-backed representation.
        """

        getter = getattr(
            graph,
            "get_node",
            None,
        )

        if callable(
            getter
        ):
            try:
                return getter(
                    node_id
                )
            except Exception:
                pass

        for node in graph.nodes:
            if node.id == node_id:
                return node

        return None

    # =========================================================================
    # DETERMINISTIC NODE IDS
    # =========================================================================

    @staticmethod
    def _repository_node_id(
        repository: str,
    ) -> str:
        return GraphNode.make_id(
            GraphNodeType.REPOSITORY,
            repository,
        )

    @staticmethod
    def _module_node_id(
        repository: str,
        module: str,
    ) -> str:
        return GraphNode.make_id(
            GraphNodeType.MODULE,
            repository,
            module,
        )

    @staticmethod
    def _block_node_id(
        repository: str,
        module: str,
        block_id: str,
    ) -> str:
        return GraphNode.make_id(
            GraphNodeType.BLOCK,
            repository,
            module,
            block_id,
        )

    @staticmethod
    def _source_file_node_id(
        repository: str,
        module: str,
        path: str,
    ) -> str:
        return GraphNode.make_id(
            GraphNodeType.SOURCE_FILE,
            repository,
            module,
            path,
        )

    @staticmethod
    def _class_node_id(
        *,
        repository: str,
        module: str,
        block_id: Optional[str],
        namespace: str,
        class_name: str,
    ) -> str:
        return GraphNode.make_id(
            GraphNodeType.CLASS,
            repository,
            module,
            block_id or "",
            namespace,
            class_name,
        )

    @staticmethod
    def _external_class_node_id(
        repository: str,
        module: str,
        block_id: Optional[str],
        class_name: str,
    ) -> str:
        return GraphNode.make_id(
            GraphNodeType.CLASS,
            repository,
            module,
            block_id or "",
            "external",
            class_name,
        )

    @staticmethod
    def _method_node_id(
        *,
        repository: str,
        module: str,
        block_id: Optional[str],
        class_name: str,
        method_name: str,
        signature: str,
    ) -> str:
        return GraphNode.make_id(
            GraphNodeType.METHOD,
            repository,
            module,
            block_id or "",
            class_name,
            method_name,
            signature,
        )

    @staticmethod
    def _external_method_node_id(
        repository: str,
        module: str,
        block_id: Optional[str],
        method_name: str,
    ) -> str:
        return GraphNode.make_id(
            GraphNodeType.METHOD,
            repository,
            module,
            block_id or "",
            "external",
            method_name,
        )

    @staticmethod
    def _function_node_id(
        *,
        repository: str,
        module: str,
        block_id: Optional[str],
        function_name: str,
        signature: str,
    ) -> str:
        return GraphNode.make_id(
            GraphNodeType.FUNCTION,
            repository,
            module,
            block_id or "",
            function_name,
            signature,
        )

    @staticmethod
    def _parameter_node_id(
        *,
        repository: str,
        module: str,
        block_id: Optional[str],
        owner_name: str,
        index: int,
        parameter: str,
    ) -> str:
        return GraphNode.make_id(
            GraphNodeType.PARAMETER,
            repository,
            module,
            block_id or "",
            owner_name,
            index,
            parameter,
        )

    @staticmethod
    def _binding_node_id(
        *,
        repository: str,
        module: str,
        block_id: Optional[str],
        binding_key: str,
        line_start: Optional[int],
    ) -> str:
        return GraphNode.make_id(
            GraphNodeType.BINDING,
            repository,
            module,
            block_id or "",
            binding_key,
            line_start or 0,
        )

    # =========================================================================
    # VALUE HELPERS
    # =========================================================================

    @staticmethod
    def _source_path(
        source_file: SourceFileKnowledge,
    ) -> str:
        if source_file.path is None:
            return "<unknown-source-file>"

        return str(
            source_file.path
        )

    @staticmethod
    def _as_path(
        value: Any,
    ) -> Optional[Path]:
        if value is None:
            return None

        if isinstance(
            value,
            Path,
        ):
            return value

        text = str(
            value
        )

        if not text:
            return None

        return Path(
            text
        )

    @staticmethod
    def _enum_value(
        value: Any,
    ) -> Any:
        if value is None:
            return None

        return getattr(
            value,
            "value",
            value,
        )

    @staticmethod
    def _clean_value(
        value: Any,
    ) -> Any:
        """
        Convert model values into JSON-safe metadata.
        """

        if value is None:
            return None

        if isinstance(
            value,
            Path,
        ):
            return str(
                value
            )

        if isinstance(
            value,
            (str, int, float, bool),
        ):
            return value

        enum_value = getattr(
            value,
            "value",
            None,
        )

        if enum_value is not None:
            return enum_value

        if isinstance(
            value,
            dict,
        ):
            return {
                str(key): (
                    KnowledgeGraphBuilder._clean_value(
                        item
                    )
                )
                for key, item in value.items()
            }

        if isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):
            return [
                KnowledgeGraphBuilder._clean_value(
                    item
                )
                for item in value
            ]

        return str(
            value
        )


# ============================================================================
# FUNCTIONAL API
# ============================================================================


def build_knowledge_graph(
    implementation_records: Iterable[
        ImplementationKnowledge
    ],
    source_references: Optional[
        Iterable[Any]
    ] = None,
    *,
    logger: Optional[logging.Logger] = None,
) -> KnowledgeGraphBuildResult:
    """
    Functional convenience wrapper.
    """

    builder = KnowledgeGraphBuilder(
        logger=logger
    )

    return builder.build(
        implementation_records,
        source_references=source_references,
    )