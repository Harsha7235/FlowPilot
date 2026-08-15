from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ContextItem:
    content: str
    source: str = ""
    priority: float = 1.0
    token_estimate: int = 0

    def __post_init__(self) -> None:
        if self.token_estimate <= 0:
            self.token_estimate = (
                len(self.content) + 3
            ) // 4

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "source": self.source,
            "priority": self.priority,
            "token_estimate": self.token_estimate,
        }


@dataclass
class ContextBuildResult:
    success: bool
    text: str = ""
    items_selected: int = 0
    estimated_tokens: int = 0
    truncated: bool = False
    errors: List[str] = field(
        default_factory=list
    )

    def summary(self) -> dict:
        return {
            "success": self.success,
            "items_selected": self.items_selected,
            "estimated_tokens": self.estimated_tokens,
            "text_length": len(self.text),
            "truncated": self.truncated,
            "errors": len(self.errors),
        }


class ContextManager:
    """
    Controls how much retrieved knowledge is placed
    into a model prompt.

    The knowledge base can be much larger than the
    model context window. Only the most relevant
    context is selected.
    """

    def __init__(
        self,
        max_tokens: int = 12000,
        reserved_tokens: int = 4000,
    ) -> None:

        if max_tokens <= 0:
            raise ValueError(
                "max_tokens must be positive."
            )

        if reserved_tokens < 0:
            raise ValueError(
                "reserved_tokens cannot be negative."
            )

        if reserved_tokens >= max_tokens:
            raise ValueError(
                "reserved_tokens must be smaller "
                "than max_tokens."
            )

        self.max_tokens = max_tokens
        self.reserved_tokens = (
            reserved_tokens
        )

    @property
    def context_budget(self) -> int:
        return (
            self.max_tokens
            - self.reserved_tokens
        )

    def estimate_tokens(
        self,
        text: str,
    ) -> int:

        if not text:
            return 0

        return (
            len(text) + 3
        ) // 4

    def build(
        self,
        items: List[ContextItem],
        query: str = "",
    ) -> ContextBuildResult:

        if not items:

            return ContextBuildResult(
                success=True,
                text="",
            )

        ranked = self._rank_items(
            items,
            query,
        )

        selected: List[
            ContextItem
        ] = []

        used_tokens = 0
        truncated = False

        for item in ranked:

            item_tokens = (
                item.token_estimate
            )

            if (
                used_tokens
                + item_tokens
                <= self.context_budget
            ):

                selected.append(item)
                used_tokens += item_tokens

                continue

            remaining = (
                self.context_budget
                - used_tokens
            )

            if remaining > 20:

                shortened = (
                    self._truncate_item(
                        item,
                        remaining,
                    )
                )

                if shortened is not None:

                    selected.append(
                        shortened
                    )

                    used_tokens += (
                        shortened.token_estimate
                    )

            truncated = True
            break

        text = self._render(
            selected
        )

        return ContextBuildResult(
            success=True,
            text=text,
            items_selected=len(
                selected
            ),
            estimated_tokens=used_tokens,
            truncated=truncated,
        )

    def build_from_texts(
        self,
        texts: List[str],
        query: str = "",
    ) -> ContextBuildResult:

        items = [
            ContextItem(
                content=text,
                source=f"context_{index}",
            )
            for index, text in enumerate(
                texts
            )
            if text and text.strip()
        ]

        return self.build(
            items,
            query,
        )

    def _rank_items(
        self,
        items: List[ContextItem],
        query: str,
    ) -> List[ContextItem]:

        query_terms = {
            term.lower()
            for term in query.split()
            if len(term) > 2
        }

        scored = []

        for index, item in enumerate(items):

            content_lower = (
                item.content.lower()
            )

            matches = sum(
                1
                for term in query_terms
                if term in content_lower
            )

            score = (
                item.priority
                + matches * 2.0
            )

            scored.append(
                (
                    score,
                    -index,
                    item,
                )
            )

        scored.sort(
            key=lambda value: (
                value[0],
                value[1],
            ),
            reverse=True,
        )

        return [
            item
            for _, _, item in scored
        ]

    def _truncate_item(
        self,
        item: ContextItem,
        available_tokens: int,
    ) -> Optional[ContextItem]:

        if available_tokens <= 20:
            return None

        max_chars = (
            available_tokens * 4
        )

        content = item.content[
            :max_chars
        ]

        if not content:
            return None

        return ContextItem(
            content=(
                content
                + "\n...[context truncated]"
            ),
            source=item.source,
            priority=item.priority,
        )

    def _render(
        self,
        items: List[ContextItem],
    ) -> str:

        sections = []

        for index, item in enumerate(
            items,
            start=1,
        ):

            header = (
                f"## CONTEXT {index}"
            )

            if item.source:
                header += (
                    f" [{item.source}]"
                )

            sections.append(
                header
                + "\n"
                + item.content
            )

        return "\n\n".join(
            sections
        )


__all__ = [
    "ContextItem",
    "ContextBuildResult",
    "ContextManager",
]