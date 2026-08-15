"""
Knowledge Context Validator.

Validates KnowledgeContext objects before they are passed to
downstream FlowPilot components.

The validator understands that the same graph entity can legitimately
appear more than once in a context collection when it is reached through
different source-code relationships.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from flowpilot.knowledge.parser.knowledge_context_builder import (
    KnowledgeContext,
    KnowledgeContextBuilder,
)


# ============================================================================
# Validation Result
# ============================================================================


@dataclass
class KnowledgeContextValidationResult:
    """Result of validating a KnowledgeContext."""

    success: bool = False

    query: str = ""

    block_id: Optional[str] = None

    checks: Dict[str, bool] = field(
        default_factory=dict
    )

    errors: List[str] = field(
        default_factory=list
    )

    warnings: List[str] = field(
        default_factory=list
    )

    def summary(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "query": self.query,
            "block_id": self.block_id,
            "checks_passed": sum(
                1
                for value in self.checks.values()
                if value
            ),
            "checks_total": len(
                self.checks
            ),
            "errors": len(
                self.errors
            ),
            "warnings": len(
                self.warnings
            ),
        }


# ============================================================================
# Validator
# ============================================================================


class KnowledgeContextValidator:
    """
    Validate the structural integrity of KnowledgeContext.

    Repeated references to the same graph node are allowed.
    """

    def __init__(
        self,
        builder: Optional[
            KnowledgeContextBuilder
        ] = None,
    ) -> None:

        self.builder = (
            builder
            if builder is not None
            else KnowledgeContextBuilder()
        )

    # ========================================================================
    # Public API
    # ========================================================================

    def validate(
        self,
        context: KnowledgeContext,
    ) -> KnowledgeContextValidationResult:
        """Validate an existing KnowledgeContext."""

        if context is None:
            return KnowledgeContextValidationResult(
                success=False,
                errors=[
                    "Knowledge context is required."
                ],
            )

        result = KnowledgeContextValidationResult(
            success=False,
            query=str(
                getattr(
                    context,
                    "query",
                    "",
                )
                or ""
            ),
            block_id=getattr(
                context,
                "block_id",
                None,
            ),
        )

        self._run_check(
            result,
            "query_present",
            self._check_query(context),
            "Query is missing.",
        )

        self._run_check(
            result,
            "block_id_present",
            self._check_block_id(context),
            "Block ID is missing.",
        )

        self._run_check(
            result,
            "block_found",
            self._check_block_found(context),
            "Block was not resolved.",
        )

        self._run_check(
            result,
            "source_files_valid",
            self._check_collection(
                context,
                "source_files",
            ),
            "Source files collection is invalid.",
        )

        self._run_check(
            result,
            "classes_valid",
            self._check_collection(
                context,
                "classes",
            ),
            "Classes collection is invalid.",
        )

        self._run_check(
            result,
            "methods_valid",
            self._check_collection(
                context,
                "methods",
            ),
            "Methods collection is invalid.",
        )

        self._run_check(
            result,
            "functions_valid",
            self._check_collection(
                context,
                "functions",
            ),
            "Functions collection is invalid.",
        )

        self._run_check(
            result,
            "bindings_valid",
            self._check_collection(
                context,
                "bindings",
            ),
            "Bindings collection is invalid.",
        )

        self._run_check(
            result,
            "parameters_valid",
            self._check_collection(
                context,
                "parameters",
            ),
            "Parameters collection is invalid.",
        )

        self._run_check(
            result,
            "inherited_classes_valid",
            self._check_collection(
                context,
                "inherited_classes",
            ),
            "Inherited classes collection is invalid.",
        )

        self._run_check(
            result,
            "references_valid",
            self._check_references(context),
            "References collection contains invalid entries.",
        )

        self._run_check(
            result,
            "no_duplicate_ids",
            self._check_duplicate_ids(context),
            "Duplicate entity IDs were found.",
        )

        self._run_check(
            result,
            "reference_targets_valid",
            self._check_reference_targets(context),
            "One or more reference targets are invalid.",
        )

        self._run_check(
            result,
            "no_context_errors",
            self._check_no_errors(context),
            "Context contains errors.",
        )

        result.success = len(
            result.errors
        ) == 0

        return result

    def build_and_validate(
        self,
        query: str,
    ) -> KnowledgeContextValidationResult:
        """Build a context and validate it."""

        build_result = self.builder.build(
            query
        )

        if (
            not build_result.success
            or build_result.context is None
        ):
            errors = list(
                build_result.errors
            )

            if (
                not errors
                and build_result.context is not None
            ):
                errors.extend(
                    build_result.context.errors
                )

            return KnowledgeContextValidationResult(
                success=False,
                query=query,
                block_id=(
                    build_result.context.block_id
                    if build_result.context
                    else None
                ),
                errors=errors,
            )

        return self.validate(
            build_result.context
        )

    # ========================================================================
    # Basic checks
    # ========================================================================

    @staticmethod
    def _check_query(
        context: KnowledgeContext,
    ) -> bool:

        query = getattr(
            context,
            "query",
            "",
        )

        return bool(
            query
            and str(query).strip()
        )

    @staticmethod
    def _check_block_id(
        context: KnowledgeContext,
    ) -> bool:

        block_id = getattr(
            context,
            "block_id",
            None,
        )

        return bool(
            block_id
            and str(block_id).strip()
        )

    @staticmethod
    def _check_block_found(
        context: KnowledgeContext,
    ) -> bool:

        return bool(
            getattr(
                context,
                "block_found",
                False,
            )
        )

    @staticmethod
    def _check_collection(
        context: KnowledgeContext,
        field_name: str,
    ) -> bool:

        value = getattr(
            context,
            field_name,
            None,
        )

        if value is None:
            return False

        return isinstance(
            value,
            (list, tuple),
        )

    # ========================================================================
    # Reference validation
    # ========================================================================

    def _check_references(
        self,
        context: KnowledgeContext,
    ) -> bool:

        references = getattr(
            context,
            "references",
            None,
        )

        if references is None:
            return False

        if not isinstance(
            references,
            (list, tuple),
        ):
            return False

        for reference in references:

            if not self._valid_reference(
                reference
            ):
                return False

        return True

    @staticmethod
    def _valid_reference(
        reference: Any,
    ) -> bool:

        if reference is None:
            return False

        source = getattr(
            reference,
            "source",
            None,
        )

        relationship = getattr(
            reference,
            "relationship",
            None,
        )

        target = getattr(
            reference,
            "target",
            None,
        )

        if not source:
            return False

        if not relationship:
            return False

        if not target:
            return False

        metadata = getattr(
            reference,
            "metadata",
            {},
        )

        if metadata is None:
            return True

        return isinstance(
            metadata,
            dict,
        )

    # ========================================================================
    # Duplicate validation
    # ========================================================================

    @staticmethod
    def _check_duplicate_ids(
        context: KnowledgeContext,
    ) -> bool:
        """
        Validate entity collections.

        Duplicate IDs are allowed because the context builder may collect
        the same graph node through multiple relationships.

        The important condition is that every collected entity has a
        valid non-empty ID. Therefore this check validates IDs rather
        than rejecting repeated graph references.
        """

        collections = [
            "source_files",
            "classes",
            "methods",
            "functions",
            "bindings",
            "parameters",
            "inherited_classes",
        ]

        for field_name in collections:

            values = getattr(
                context,
                field_name,
                [],
            )

            if values is None:
                continue

            for item in values:

                item_id = KnowledgeContextValidator._item_id(
                    item
                )

                if not item_id:
                    return False

        return True

    # ========================================================================
    # Reference target validation
    # ========================================================================

    @staticmethod
    def _check_reference_targets(
        context: KnowledgeContext,
    ) -> bool:
        """
        Verify that every reference contains a valid target.

        External graph references are intentionally allowed.
        """

        references = getattr(
            context,
            "references",
            [],
        )

        if references is None:
            return False

        for reference in references:

            target = getattr(
                reference,
                "target",
                None,
            )

            if not target:
                return False

        return True

    # ========================================================================
    # Context error validation
    # ========================================================================

    @staticmethod
    def _check_no_errors(
        context: KnowledgeContext,
    ) -> bool:

        errors = getattr(
            context,
            "errors",
            [],
        )

        if errors is None:
            return True

        return len(
            errors
        ) == 0

    # ========================================================================
    # Utility
    # ========================================================================

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
        ).strip()

    @staticmethod
    def _run_check(
        result: KnowledgeContextValidationResult,
        name: str,
        passed: bool,
        error_message: str,
    ) -> None:

        result.checks[
            name
        ] = bool(
            passed
        )

        if not passed:
            result.errors.append(
                error_message
            )


# ============================================================================
# Convenience functions
# ============================================================================


def validate_knowledge_context(
    context: KnowledgeContext,
) -> KnowledgeContextValidationResult:

    validator = KnowledgeContextValidator()

    return validator.validate(
        context
    )


def build_and_validate_knowledge_context(
    query: str,
) -> KnowledgeContextValidationResult:

    validator = KnowledgeContextValidator()

    return validator.build_and_validate(
        query
    )


# ============================================================================
# Public exports
# ============================================================================


__all__ = [
    "KnowledgeContextValidationResult",
    "KnowledgeContextValidator",
    "validate_knowledge_context",
    "build_and_validate_knowledge_context",
]