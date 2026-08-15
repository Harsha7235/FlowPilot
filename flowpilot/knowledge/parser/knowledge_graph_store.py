from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

from flowpilot.core.models import ModelEncoder
from flowpilot.core.utils import (
    configure_logger,
    load_json,
    safe_mkdir,
    save_json,
)

from flowpilot.knowledge.parser.knowledge_graph_models import (
    KnowledgeGraph,
)


class KnowledgeGraphStore:
    """
    Persistent storage for FlowPilot KnowledgeGraph objects.

    Storage layout:

        flowpilot/knowledge/graph/
            knowledge_graph.json

    The store deliberately keeps persistence separate from graph
    construction. KnowledgeGraphBuilder creates the graph; this class
    saves and restores it.
    """

    # Deployment-safe path.
    #
    # knowledge_graph_store.py is located at:
    #
    # flowpilot/knowledge/parser/knowledge_graph_store.py
    #
    # parents[0] -> parser
    # parents[1] -> knowledge
    #
    # Therefore:
    # flowpilot/knowledge/graph/
    DEFAULT_STORAGE_DIR = (
        Path(__file__).resolve().parents[1] / "graph"
    )

    DEFAULT_FILENAME = "knowledge_graph.json"

    def __init__(
        self,
        storage_dir: Union[str, Path] = DEFAULT_STORAGE_DIR,
        *,
        filename: str = DEFAULT_FILENAME,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.storage_dir = Path(storage_dir)
        self.filename = filename

        safe_mkdir(self.storage_dir)

        self.logger = logger or configure_logger(
            "flowpilot.knowledge.parser.knowledge_graph_store"
        )

    @property
    def path(self) -> Path:
        """
        Return the full path of the persisted graph.
        """
        return self.storage_dir / self.filename

    def exists(self) -> bool:
        """
        Return True when a persisted graph exists.
        """
        return self.path.exists()

    def store(
        self,
        graph: KnowledgeGraph,
    ) -> Path:
        """
        Persist a KnowledgeGraph to disk.

        The graph is first validated. A graph containing validation
        errors is not persisted.
        """
        errors = graph.validate()

        if errors:
            raise ValueError(
                "Knowledge graph validation failed: "
                + "; ".join(str(error) for error in errors)
            )

        safe_mkdir(self.storage_dir)

        payload = ModelEncoder.encode(graph)

        save_json(
            self.path,
            payload,
        )

        self.logger.info(
            "Stored knowledge graph at %s",
            self.path,
        )

        return self.path

    def load(self) -> KnowledgeGraph:
        """
        Load the persisted KnowledgeGraph from disk.
        """
        if not self.exists():
            raise FileNotFoundError(
                f"Knowledge graph not found: {self.path}"
            )

        payload = load_json(self.path)

        if payload is None:
            raise RuntimeError(
                f"Knowledge graph could not be loaded: {self.path}"
            )

        graph = KnowledgeGraph.from_dict(payload)

        self.logger.info(
            "Loaded knowledge graph from %s",
            self.path,
        )

        return graph