from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter


router = APIRouter(
    prefix="/api/system",
    tags=["System"],
)


@router.get("/status")
def system_status() -> Dict[str, Any]:
    """
    Return the current status of the major FlowPilot
    subsystems.

    This endpoint reports architecture/integration
    status. It does not claim that a real AI provider
    is connected.
    """

    return {
        "success": True,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "system": {
            "name": "FlowPilot",
            "version": "0.1.0",
            "status": "running",
        },
        "components": {
            "api": {
                "status": "ready",
            },
            "knowledge_graph": {
                "status": "ready",
            },
            "retrieval": {
                "status": "ready",
            },
            "context_builder": {
                "status": "ready",
            },
            "context_validator": {
                "status": "ready",
            },
            "prompt_builder": {
                "status": "ready",
            },
            "agent": {
                "status": "ready",
            },
            "tools": {
                "status": "ready",
            },
            "sessions": {
                "status": "ready",
            },
            "inference": {
                "status": "under_development",
            },
            "ai_provider": {
                "status": "not_configured",
            },
        },
        "knowledge": {
            "nodes": 26778,
            "edges": 29620,
            "source_files": 1922,
            "classes": 2938,
            "methods": 5199,
            "functions": 3933,
            "parameters": 11756,
        },
    }


@router.get("/capabilities")
def capabilities() -> Dict[str, Any]:
    """
    Describe what FlowPilot currently exposes and
    what is still under development.
    """

    return {
        "success": True,
        "available": [
            "knowledge_retrieval",
            "knowledge_context",
            "context_validation",
            "prompt_building",
            "code_search",
            "filesystem_tools",
            "command_runner",
            "git_tools",
            "coding_planner",
            "coding_executor",
            "code_validation",
            "repair_workflow",
            "agent_sessions",
            "repository_information",
        ],
        "under_development": [
            "real_ai_inference",
            "long_conversation_summarization",
            "advanced_context_memory",
            "production_chat_interface",
            "full_end_to_end_ai_coding",
        ],
        "not_configured": [
            "ai_provider",
        ],
    }