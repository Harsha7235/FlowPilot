from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from flowpilot.api.routes_agent import router as agent_router
from flowpilot.api.routes_chat import router as chat_router
from flowpilot.api.routes_knowledge import router as knowledge_router
from flowpilot.api.routes_repository import router as repository_router
from flowpilot.api.routes_sessions import router as sessions_router
from flowpilot.api.routes_system import router as system_router


APP_NAME = "FlowPilot API"
APP_VERSION = "0.1.0"


app = FastAPI(
    title=APP_NAME,
    description=(
        "HTTP API for the FlowPilot GNU Radio "
        "and SDCS engineering assistant."
    ),
    version=APP_VERSION,
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# API ROUTERS
# =========================================================

app.include_router(
    knowledge_router
)

app.include_router(
    sessions_router
)

app.include_router(
    agent_router
)

app.include_router(
    repository_router
)

app.include_router(
    system_router
)

app.include_router(
    chat_router
)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "service": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": APP_NAME,
        "version": APP_VERSION,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }


# =========================================================
# STATUS
# =========================================================

@app.get("/api/status")
def status() -> Dict[str, Any]:
    return {
        "backend": {
            "status": "ready",
        },
        "knowledge": {
            "status": "ready",
        },
        "agent": {
            "status": "ready",
        },
        "sessions": {
            "status": "ready",
        },
        "chat": {
            "status": "ready",
            "endpoint": "/api/chat",
        },
        "ai_provider": {
            "status": "under_development",
        },
    }
