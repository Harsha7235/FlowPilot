"""
FlowPilot Implementation Knowledge Builder.

Builds persistent ImplementationKnowledge records from existing
SourceReference records.

Pipeline:

    BlockStore
        ↓
    stored BlockDefinitions
        ↓
    SourceReferenceMapper.load()
        ↓
    existing SourceReference
        ↓
    SourceCodeAnalyzer.analyze_reference()
        ↓
    ImplementationKnowledge
        ↓
    ImplementationStore.store()

Important design rules:

- Does NOT rediscover source references.
- Does NOT modify SourceReferenceMapper.
- Does NOT analyze possible/weak references.
- Uses only confirmed SourceReference matches.
- Does NOT execute repository source code.
- A failure for one block must not stop the complete build.
- Existing working components remain unchanged.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from flowpilot.core.utils import configure_logger

from flowpilot.knowledge.parser.block_store import (
    BlockStore,
)

from flowpilot.knowledge.parser.source_reference_mapper import (
    SourceReferenceMapper,
)

from flowpilot.knowledge.parser.source_code_analyzer import (
    SourceCodeAnalyzer,
)

from flowpilot.knowledge.parser.implementation_store import (
    ImplementationStore,
)


@dataclass(slots=True)
class BuildFailure:
    """
    Information about one block that could not be processed.
    """

    repository: Optional[str] = None
    module: Optional[str] = None
    block_id: Optional[str] = None
    stage: str = ""
    error: str = ""


@dataclass(slots=True)
class BuildStatistics:
    """
    Aggregate statistics for one implementation-knowledge build.
    """

    blocks_discovered: int = 0

    references_loaded: int = 0

    references_missing: int = 0

    blocks_analyzed: int = 0

    successful_blocks: int = 0

    failed_blocks: int = 0

    skipped_blocks: int = 0

    files_analyzed: int = 0

    files_successful: int = 0

    files_failed: int = 0

    files_unsupported: int = 0

    classes_found: int = 0

    methods_found: int = 0

    functions_found: int = 0

    bindings_found: int = 0

    records_stored: int = 0

    elapsed_seconds: float = 0.0

    failures: List[BuildFailure] = field(
        default_factory=list
    )

    def summary(self) -> Dict[str, object]:
        """
        Return serializable build statistics.
        """

        return {
            "blocks_discovered": self.blocks_discovered,
            "references_loaded": self.references_loaded,
            "references_missing": self.references_missing,
            "blocks_analyzed": self.blocks_analyzed,
            "successful_blocks": self.successful_blocks,
            "failed_blocks": self.failed_blocks,
            "skipped_blocks": self.skipped_blocks,
            "files_analyzed": self.files_analyzed,
            "files_successful": self.files_successful,
            "files_failed": self.files_failed,
            "files_unsupported": self.files_unsupported,
            "classes_found": self.classes_found,
            "methods_found": self.methods_found,
            "functions_found": self.functions_found,
            "bindings_found": self.bindings_found,
            "records_stored": self.records_stored,
            "elapsed_seconds": self.elapsed_seconds,
            "failure_count": len(self.failures),
        }


class ImplementationKnowledgeBuilder:
    """
    Build ImplementationKnowledge for stored GNU Radio blocks.

    This class intentionally acts only as an orchestration layer.

    It uses:

        BlockStore
        SourceReferenceMapper
        SourceCodeAnalyzer
        ImplementationStore

    It does not contain source-reference matching logic.
    """

    def __init__(
        self,
        *,
        block_store: Optional[BlockStore] = None,
        reference_mapper: Optional[
            SourceReferenceMapper
        ] = None,
        analyzer: Optional[
            SourceCodeAnalyzer
        ] = None,
        implementation_store: Optional[
            ImplementationStore
        ] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:

        self.block_store = (
            block_store
            or BlockStore()
        )

        self.reference_mapper = (
            reference_mapper
            or SourceReferenceMapper()
        )

        self.analyzer = (
            analyzer
            or SourceCodeAnalyzer()
        )

        self.implementation_store = (
            implementation_store
            or ImplementationStore()
        )

        self.logger = (
            logger
            or configure_logger(
                "flowpilot.knowledge.parser.implementation_knowledge_builder"
            )
        )

    def build(
        self,
        *,
        repository: Optional[str] = None,
        module: Optional[str] = None,
        block_ids: Optional[List[str]] = None,
    ) -> BuildStatistics:
        """
        Build ImplementationKnowledge records.

        Parameters
        ----------
        repository:
            Optional repository filter.

        module:
            Optional module filter.

        block_ids:
            Optional explicit block-ID filter.

        Returns
        -------
        BuildStatistics
            Aggregate statistics for the build.
        """

        started = time.perf_counter()

        statistics = BuildStatistics()

        blocks = self._load_blocks(
            repository=repository,
            module=module,
            block_ids=block_ids,
        )

        statistics.blocks_discovered = len(
            blocks
        )

        self.logger.info(
            "Starting implementation knowledge build: %d block(s)",
            len(blocks),
        )

        for block in blocks:

            self._process_block(
                block=block,
                statistics=statistics,
            )

        statistics.elapsed_seconds = (
            time.perf_counter()
            - started
        )

        self.logger.info(
            "Implementation knowledge build completed: "
            "discovered=%d analyzed=%d successful=%d "
            "failed=%d stored=%d",
            statistics.blocks_discovered,
            statistics.blocks_analyzed,
            statistics.successful_blocks,
            statistics.failed_blocks,
            statistics.records_stored,
        )

        return statistics

    def _load_blocks(
        self,
        *,
        repository: Optional[str],
        module: Optional[str],
        block_ids: Optional[List[str]],
    ):
        """
        Load BlockDefinitions from the existing BlockStore.

        No parsing is performed here.
        """

        blocks = []

        if repository is not None:

            repositories = [
                repository
            ]

        else:

            summary = (
                self.block_store.summary()
            )

            repositories = list(
                summary.get(
                    "by_repository",
                    {},
                ).keys()
            )

        requested_ids = (
            set(block_ids)
            if block_ids
            else None
        )

        for repo in repositories:

            try:
                repo_blocks = (
                    self.block_store.list_by_repository(
                        repo
                    )
                )

            except Exception as exc:

                self.logger.exception(
                    "Failed loading blocks for repository %s",
                    repo,
                )

                continue

            for block in repo_blocks:

                if module is not None:
                    if block.module != module:
                        continue

                if requested_ids is not None:
                    if block.block_id not in requested_ids:
                        continue

                blocks.append(block)

        return blocks

    def _process_block(
        self,
        *,
        block,
        statistics: BuildStatistics,
    ) -> None:
        """
        Process exactly one BlockDefinition.

        Errors are isolated to this block.
        """

        repository = (
            getattr(
                block,
                "repository",
                None,
            )
        )

        module = (
            getattr(
                block,
                "module",
                None,
            )
        )

        block_id = (
            getattr(
                block,
                "block_id",
                None,
            )
        )

        if not repository:
            statistics.skipped_blocks += 1

            self._record_failure(
                statistics=statistics,
                repository=repository,
                module=module,
                block_id=block_id,
                stage="identity",
                error=(
                    "Block has no repository"
                ),
            )

            return

        if not module:
            statistics.skipped_blocks += 1

            self._record_failure(
                statistics=statistics,
                repository=repository,
                module=module,
                block_id=block_id,
                stage="identity",
                error=(
                    "Block has no module"
                ),
            )

            return

        if not block_id:
            statistics.skipped_blocks += 1

            self._record_failure(
                statistics=statistics,
                repository=repository,
                module=module,
                block_id=block_id,
                stage="identity",
                error=(
                    "Block has no block_id"
                ),
            )

            return

        self.logger.info(
            "Processing %s/%s/%s",
            repository,
            module,
            block_id,
        )

        # ----------------------------------------------------------
        # Stage 1: load existing SourceReference
        # ----------------------------------------------------------

        try:

            reference = (
                self.reference_mapper.load(
                    repository,
                    module,
                    block_id,
                )
            )

        except Exception as exc:

            statistics.failed_blocks += 1

            self._record_failure(
                statistics=statistics,
                repository=repository,
                module=module,
                block_id=block_id,
                stage="reference_load",
                error=str(exc),
            )

            self.logger.exception(
                "Failed loading SourceReference for %s",
                block_id,
            )

            return

        if reference is None:

            statistics.references_missing += 1

            self._record_failure(
                statistics=statistics,
                repository=repository,
                module=module,
                block_id=block_id,
                stage="reference_load",
                error=(
                    "Stored SourceReference "
                    "was not found"
                ),
            )

            self.logger.warning(
                "No SourceReference found for %s",
                block_id,
            )

            return

        statistics.references_loaded += 1

        # ----------------------------------------------------------
        # Stage 2: validate confirmed references
        # ----------------------------------------------------------

        confirmed_count = (
            reference.matched_file_count
        )

        if confirmed_count <= 0:

            statistics.skipped_blocks += 1

            self.logger.info(
                "Skipping %s: no confirmed source references",
                block_id,
            )

            return

        # ----------------------------------------------------------
        # Stage 3: static source analysis
        # ----------------------------------------------------------

        try:

            knowledge = (
                self.analyzer.analyze_reference(
                    reference
                )
            )

        except Exception as exc:

            statistics.failed_blocks += 1

            self._record_failure(
                statistics=statistics,
                repository=repository,
                module=module,
                block_id=block_id,
                stage="analysis",
                error=str(exc),
            )

            self.logger.exception(
                "Source analysis failed for %s",
                block_id,
            )

            return

        statistics.blocks_analyzed += 1

        # ----------------------------------------------------------
        # Stage 4: aggregate statistics
        # ----------------------------------------------------------

        statistics.files_analyzed += (
            knowledge.analyzed_file_count
        )

        statistics.files_successful += (
            knowledge.successful_file_count
        )

        statistics.files_failed += (
            knowledge.failed_file_count
        )

        statistics.files_unsupported += (
            knowledge.unsupported_file_count
        )

        statistics.classes_found += (
            knowledge.classes_found
        )

        statistics.methods_found += (
            knowledge.methods_found
        )

        statistics.functions_found += (
            knowledge.functions_found
        )

        statistics.bindings_found += (
            knowledge.bindings_found
        )

        # ----------------------------------------------------------
        # Stage 5: determine block success
        # ----------------------------------------------------------

        if knowledge.failed_file_count > 0:

            self.logger.warning(
                "%s analyzed with %d failed file(s)",
                block_id,
                knowledge.failed_file_count,
            )

        if (
            knowledge.analyzed_file_count == 0
        ):

            statistics.failed_blocks += 1

            self._record_failure(
                statistics=statistics,
                repository=repository,
                module=module,
                block_id=block_id,
                stage="analysis",
                error=(
                    "No confirmed source files "
                    "could be analyzed"
                ),
            )

            return

        statistics.successful_blocks += 1

        # ----------------------------------------------------------
        # Stage 6: persist ImplementationKnowledge
        # ----------------------------------------------------------

        try:

            self.implementation_store.store(
                knowledge
            )

            statistics.records_stored += 1

        except Exception as exc:

            statistics.failed_blocks -= 1
            statistics.successful_blocks -= 1
            statistics.failed_blocks += 1

            self._record_failure(
                statistics=statistics,
                repository=repository,
                module=module,
                block_id=block_id,
                stage="storage",
                error=str(exc),
            )

            self.logger.exception(
                "Failed storing ImplementationKnowledge for %s",
                block_id,
            )

            return

        self.logger.info(
            "Completed %s: files=%d classes=%d methods=%d "
            "functions=%d bindings=%d",
            block_id,
            knowledge.analyzed_file_count,
            knowledge.classes_found,
            knowledge.methods_found,
            knowledge.functions_found,
            knowledge.bindings_found,
        )

    @staticmethod
    def _record_failure(
        *,
        statistics: BuildStatistics,
        repository: Optional[str],
        module: Optional[str],
        block_id: Optional[str],
        stage: str,
        error: str,
    ) -> None:
        """
        Add an isolated block failure to the build report.
        """

        statistics.failures.append(
            BuildFailure(
                repository=repository,
                module=module,
                block_id=block_id,
                stage=stage,
                error=error,
            )
        )

    def build_one(
        self,
        repository: str,
        module: str,
        block_id: str,
    ) -> BuildStatistics:
        """
        Convenience method for testing one block.
        """

        return self.build(
            repository=repository,
            module=module,
            block_ids=[
                block_id
            ],
        )


def print_build_report(
    statistics: BuildStatistics,
) -> None:
    """
    Print a human-readable build report.
    """

    print()
    print("=" * 70)
    print("IMPLEMENTATION KNOWLEDGE BUILD")
    print("=" * 70)

    print(
        f"Blocks discovered      : "
        f"{statistics.blocks_discovered}"
    )

    print(
        f"References loaded      : "
        f"{statistics.references_loaded}"
    )

    print(
        f"References missing     : "
        f"{statistics.references_missing}"
    )

    print(
        f"Blocks analyzed        : "
        f"{statistics.blocks_analyzed}"
    )

    print(
        f"Successful blocks      : "
        f"{statistics.successful_blocks}"
    )

    print(
        f"Failed blocks          : "
        f"{statistics.failed_blocks}"
    )

    print(
        f"Skipped blocks         : "
        f"{statistics.skipped_blocks}"
    )

    print()

    print(
        f"Files analyzed         : "
        f"{statistics.files_analyzed}"
    )

    print(
        f"Files successful       : "
        f"{statistics.files_successful}"
    )

    print(
        f"Files failed           : "
        f"{statistics.files_failed}"
    )

    print(
        f"Files unsupported      : "
        f"{statistics.files_unsupported}"
    )

    print()

    print(
        f"Classes found          : "
        f"{statistics.classes_found}"
    )

    print(
        f"Methods found          : "
        f"{statistics.methods_found}"
    )

    print(
        f"Functions found        : "
        f"{statistics.functions_found}"
    )

    print(
        f"Bindings found         : "
        f"{statistics.bindings_found}"
    )

    print()

    print(
        f"Records stored         : "
        f"{statistics.records_stored}"
    )

    print(
        f"Elapsed seconds        : "
        f"{statistics.elapsed_seconds:.2f}"
    )

    if statistics.failures:

        print()
        print("=" * 70)
        print("FAILURES")
        print("=" * 70)

        for failure in statistics.failures:

            identity = "/".join(
                value
                for value in (
                    failure.repository,
                    failure.module,
                    failure.block_id,
                )
                if value
            )

            print(
                f"{identity} | "
                f"stage={failure.stage} | "
                f"{failure.error}"
            )

    print()
    print("=" * 70)


def main() -> None:
    """
    Default CLI entry point.

    The default mode intentionally processes all stored blocks.
    """

    builder = (
        ImplementationKnowledgeBuilder()
    )

    statistics = builder.build()

    print_build_report(
        statistics
    )


if __name__ == "__main__":
    main()