"""Knowledge extraction parsers for the FlowPilot platform.
 
This package holds the schema-tolerant parsers that convert raw source
files discovered by the Repository Scanner into structured knowledge
for the Autonomous Knowledge Acquisition System (AKAS). It currently
provides :class:`~flowpilot.knowledge.parser.block_yaml_parser.BlockYamlParser`
for GNU Radio Companion block YAML files, and
:class:`~flowpilot.knowledge.parser.block_store.BlockStore` for
persisting and querying the resulting
:class:`~flowpilot.knowledge.parser.block_models.BlockDefinition`
objects in ``flowpilot/knowledge/blocks/``. Parsers for other source
types (GRC flowgraphs, Python, C++, documentation) are added here as
the same kind of sibling module.
"""
 
from __future__ import annotations
 
from flowpilot.knowledge.parser.block_models import (
    BlockDefinition,
    BlockParameter,
    BlockPort,
    ParseStatus,
)
from flowpilot.knowledge.parser.block_store import BlockStore
from flowpilot.knowledge.parser.block_yaml_parser import BlockYamlParser
 
__all__ = [
    "BlockDefinition",
    "BlockParameter",
    "BlockPort",
    "ParseStatus",
    "BlockYamlParser",
    "BlockStore",
]