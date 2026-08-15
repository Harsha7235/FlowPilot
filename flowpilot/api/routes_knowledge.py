from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from flowpilot.knowledge.parser.knowledge_context_builder import (
    KnowledgeContextBuilder,
)
from flowpilot.knowledge.parser.knowledge_context_renderer import (
    KnowledgeContextRenderer,
)
from flowpilot.knowledge.parser.knowledge_context_validator import (
    KnowledgeContextValidator,
)


router = APIRouter(
    prefix="/api/knowledge",
    tags=["Knowledge"],
)


# ---------------------------------------------------------
# Request models
# ---------------------------------------------------------

class KnowledgeQueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description="Natural-language knowledge query.",
    )


# ---------------------------------------------------------
# Query endpoint
# ---------------------------------------------------------

@router.post("/query")
def knowledge_query(
    request: KnowledgeQueryRequest,
) -> Dict[str, Any]:
    """
    Run a natural-language query through the existing
    FlowPilot knowledge pipeline.

    Pipeline:

        Query
          ↓
        Context Builder
          ↓
        Context Validator
          ↓
        Context Renderer
    """

    query = request.query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty.",
        )

    try:
        builder = KnowledgeContextBuilder()

        build_result = builder.build(query)

        context = build_result.context

        validator = KnowledgeContextValidator()

        validation = validator.build_and_validate(
            query
        )

        renderer = KnowledgeContextRenderer()

        rendered = renderer.render(context)

        return {
            "success": validation.success,
            "query": query,
            "summary": validation.summary(),
            "checks": validation.checks,
            "errors": validation.errors,
            "warnings": validation.warnings,
            "context": {
                "text": rendered,
                "length": len(rendered),
            },
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Knowledge query failed: {exc}",
        ) from exc


# ---------------------------------------------------------
# Compact query endpoint
# ---------------------------------------------------------

@router.post("/query/compact")
def knowledge_query_compact(
    request: KnowledgeQueryRequest,
) -> Dict[str, Any]:
    """
    Return a compact representation of the retrieved
    knowledge context.
    """

    query = request.query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty.",
        )

    try:
        builder = KnowledgeContextBuilder()

        result = builder.build(query)

        context = result.context

        renderer = KnowledgeContextRenderer()

        rendered = renderer.render_compact(
            context
        )

        return {
            "success": True,
            "query": query,
            "context": rendered,
            "length": len(rendered),
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Compact knowledge query failed: "
                f"{exc}"
            ),
        ) from exc