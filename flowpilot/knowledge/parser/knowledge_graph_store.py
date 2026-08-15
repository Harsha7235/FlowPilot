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

    DEFAULT_STORAGE_DIR = Path(
        "C:/Projects/FlowPilot/flowpilot/knowledge/graph"
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

        if graph is None:
            raise ValueError(
                "KnowledgeGraph is required"
            )

        validation_errors = graph.validate()

        if validation_errors:
            raise ValueError(
                "Cannot store invalid KnowledgeGraph: "
                + "; ".join(
                    str(error)
                    for error in validation_errors
                )
            )

        data = graph.to_dict()

        save_json(
            self.path,
            data,
            encoder=ModelEncoder,
        )

        self.logger.info(
            "Stored knowledge graph at %s",
            self.path,
        )

        return self.path

    def load(self) -> Optional[KnowledgeGraph]:
        """
        Load the persisted KnowledgeGraph.

        Returns:
            KnowledgeGraph when the file exists and can be restored.
            None when no persisted graph exists or restoration fails.
        """

        if not self.path.exists():
            self.logger.info(
                "No persisted knowledge graph found at %s",
                self.path,
            )
            return None

        try:
            data = load_json(self.path)

            if not isinstance(data, dict):
                raise TypeError(
                    "Persisted knowledge graph must be a JSON object"
                )

            graph = KnowledgeGraph.from_dict(data)

            validation_errors = graph.validate()

            if validation_errors:
                raise ValueError(
                    "Loaded KnowledgeGraph failed validation: "
                    + "; ".join(
                        str(error)
                        for error in validation_errors
                    )
                )

            self.logger.info(
                "Loaded knowledge graph from %s",
                self.path,
            )

            return graph

        except Exception as exc:
            self.logger.exception(
                "Failed to load knowledge graph %s: %s",
                self.path,
                exc,
            )
            return None

    def delete(self) -> bool:
        """
        Delete the persisted graph.

        Returns:
            True if a file was deleted, otherwise False.
        """

        if not self.path.exists():
            return False

        self.path.unlink()

        self.logger.info(
            "Deleted knowledge graph at %s",
            self.path,
        )

        return True

    def summary(self) -> dict:
        """
        Return the summary of the persisted graph.

        Returns an empty summary when no graph is stored.
        """

        graph = self.load()

        if graph is None:
            return {
                "exists": False,
                "path": str(self.path),
            }

        summary = graph.summary()

        return {
            "exists": True,
            "path": str(self.path),
            **summary,
        }

    def verify_round_trip(
        self,
        graph: KnowledgeGraph,
    ) -> dict:
        """
        Store and reload a graph, then verify important graph
        properties survived serialization.

        This is intentionally stricter than checking only that
        deserialization succeeded.
        """

        if graph is None:
            raise ValueError(
                "KnowledgeGraph is required"
            )

        original_validation = graph.validate()

        if original_validation:
            return {
                "success": False,
                "reason": "original_graph_invalid",
                "validation": original_validation,
            }

        original_summary = graph.summary()

        stored_path = self.store(graph)

        restored = self.load()

        if restored is None:
            return {
                "success": False,
                "reason": "reload_failed",
                "path": str(stored_path),
            }

        restored_summary = restored.summary()

        checks = {
            "nodes": (
                original_summary.get("nodes")
                == restored_summary.get("nodes")
            ),
            "edges": (
                original_summary.get("edges")
                == restored_summary.get("edges")
            ),
            "node_types": (
                original_summary.get("node_types")
                == restored_summary.get("node_types")
            ),
            "relationships": (
                original_summary.get("relationships")
                == restored_summary.get("relationships")
            ),
            "metadata": (
                original_summary.get("metadata")
                == restored_summary.get("metadata")
            ),
            "validation": (
                restored.validate() == []
            ),
        }

        success = all(checks.values())

        return {
            "success": success,
            "path": str(stored_path),
            "original": original_summary,
            "restored": restored_summary,
            "checks": checks,
            "validation": restored.validate(),
        }