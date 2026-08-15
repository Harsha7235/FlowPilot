from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from flowpilot.knowledge.parser.knowledge_prompt_builder import (
    KnowledgePromptBuilder,
)
from flowpilot.agent.grounded_answer import (
    generate_grounded_answer,
)


router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"],
)


# =========================================================
# REQUEST / RESPONSE MODELS
# =========================================================

class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        description="Natural-language FlowPilot question.",
    )

    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    success: bool
    answer: str
    provider: str = "flowpilot"
    source: str = "knowledge_graph"
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


# =========================================================
# CHAT
# =========================================================

@router.post(
    "",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
) -> ChatResponse:

    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    try:

        # -------------------------------------------------
        # BUILD GROUNDED KNOWLEDGE CONTEXT
        # -------------------------------------------------

        prompt_builder = KnowledgePromptBuilder()

        knowledge = prompt_builder.build(
            message
        )

        if not knowledge.success:

            return ChatResponse(
                success=False,
                answer=(
                    knowledge.errors[0]
                    if knowledge.errors
                    else "FlowPilot could not retrieve knowledge."
                ),
                provider="flowpilot",
                source="knowledge_graph",
                session_id=request.session_id,
                metadata={
                    "mode": "knowledge_error",
                    "errors": list(
                        knowledge.errors
                    ),
                },
            )

        # -------------------------------------------------
        # GENERATE GROUNDED ANSWER
        # -------------------------------------------------

        answer = generate_grounded_answer(
            message,
            knowledge.context_text,
        )

        if not answer.strip():

            return ChatResponse(
                success=False,
                answer="FlowPilot generated an empty response.",
                provider="flowpilot",
                source="knowledge_graph",
                session_id=request.session_id,
                metadata={
                    "mode": "empty_answer",
                },
            )

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        return ChatResponse(
            success=True,
            answer=answer,
            provider="flowpilot",
            source="knowledge_graph",
            session_id=request.session_id,
            metadata={
                "mode": "grounded_retrieval",
                "block_id": knowledge.block_id,
                "context_length": len(
                    knowledge.context_text
                ),
            },
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "FlowPilot chat failed: "
                f"{exc}"
            ),
        ) from exc