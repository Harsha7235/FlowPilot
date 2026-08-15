from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from flowpilot.agent.session import AgentSessionManager


router = APIRouter(
    prefix="/api/sessions",
    tags=["Sessions"],
)


# ---------------------------------------------------------
# Shared session manager
# ---------------------------------------------------------

_session_manager = AgentSessionManager(".")


# ---------------------------------------------------------
# Request models
# ---------------------------------------------------------

class CreateSessionRequest(BaseModel):
    session_id: str = Field(
        ...,
        min_length=1,
        description="Unique session identifier.",
    )


class MessageRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        description="User message.",
    )


# ---------------------------------------------------------
# Create session
# ---------------------------------------------------------

@router.post("")
def create_session(
    request: CreateSessionRequest,
) -> Dict[str, Any]:
    session_id = request.session_id.strip()

    if not session_id:
        raise HTTPException(
            status_code=400,
            detail="Session ID cannot be empty.",
        )

    try:
        session = _session_manager.create_session(
            session_id
        )

        return {
            "success": True,
            "session_id": session_id,
            "session": _serialize_session(
                session
            ),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Session creation failed: {exc}",
        ) from exc


# ---------------------------------------------------------
# Get session
# ---------------------------------------------------------

@router.get("/{session_id}")
def get_session(
    session_id: str,
) -> Dict[str, Any]:

    try:
        session = _session_manager.get_session(
            session_id
        )

        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Session not found.",
            )

        return {
            "success": True,
            "session": _serialize_session(
                session
            ),
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Session lookup failed: {exc}",
        ) from exc


# ---------------------------------------------------------
# Send message
# ---------------------------------------------------------

@router.post("/{session_id}/messages")
def send_message(
    session_id: str,
    request: MessageRequest,
) -> Dict[str, Any]:

    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    try:
        session = _session_manager.get_session(
            session_id
        )

        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Session not found.",
            )

        result = _session_manager.send(
            session_id,
            message,
        )

        updated_session = (
            _session_manager.get_session(
                session_id
            )
        )

        return {
            "success": result.success,
            "result": _serialize_result(
                result
            ),
            "session": (
                _serialize_session(
                    updated_session
                )
                if updated_session is not None
                else None
            ),
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Message processing failed: {exc}",
        ) from exc


# ---------------------------------------------------------
# Session history
# ---------------------------------------------------------

@router.get("/{session_id}/history")
def get_history(
    session_id: str,
) -> Dict[str, Any]:

    try:
        session = _session_manager.get_session(
            session_id
        )

        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Session not found.",
            )

        history = session.history()

        return {
            "success": True,
            "session_id": session_id,
            "messages": [
                _serialize_message(item)
                for item in history
            ],
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"History lookup failed: {exc}",
        ) from exc


# ---------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------

def _serialize_session(
    session: Any,
) -> Dict[str, Any]:

    if session is None:
        return {}

    data: Dict[str, Any] = {}

    if hasattr(session, "to_dict"):
        try:
            value = session.to_dict()

            if isinstance(value, dict):
                data.update(value)

        except Exception:
            pass

    if not data:
        for field_name in (
            "session_id",
            "created_at",
            "updated_at",
            "messages",
            "turns",
        ):
            if hasattr(
                session,
                field_name,
            ):
                data[field_name] = getattr(
                    session,
                    field_name,
                )

    if hasattr(session, "messages"):
        try:
            data["messages"] = [
                _serialize_message(
                    message
                )
                for message in session.messages
            ]
        except Exception:
            pass

    return _safe_json(data)


def _serialize_message(
    message: Any,
) -> Dict[str, Any]:

    if isinstance(message, dict):
        return _safe_json(message)

    if hasattr(message, "to_dict"):
        try:
            value = message.to_dict()

            if isinstance(value, dict):
                return _safe_json(value)

        except Exception:
            pass

    result: Dict[str, Any] = {}

    for field_name in (
        "role",
        "content",
        "timestamp",
        "created_at",
    ):
        if hasattr(
            message,
            field_name,
        ):
            result[field_name] = getattr(
                message,
                field_name,
            )

    return _safe_json(result)


def _serialize_result(
    result: Any,
) -> Dict[str, Any]:

    if result is None:
        return {}

    if hasattr(result, "to_dict"):
        try:
            value = result.to_dict()

            if isinstance(value, dict):
                return _safe_json(value)

        except Exception:
            pass

    if hasattr(result, "summary"):
        try:
            value = result.summary()

            if isinstance(value, dict):
                return _safe_json(value)

        except Exception:
            pass

    data: Dict[str, Any] = {}

    for field_name in (
        "success",
        "text",
        "error",
        "provider",
        "model",
    ):
        if hasattr(
            result,
            field_name,
        ):
            data[field_name] = getattr(
                result,
                field_name,
            )

    return _safe_json(data)


def _safe_json(
    value: Any,
) -> Any:

    if value is None:
        return None

    if isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    if isinstance(value, dict):
        return {
            str(key): _safe_json(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _safe_json(item)
            for item in value
        ]

    return str(value)