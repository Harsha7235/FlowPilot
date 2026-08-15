from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from flowpilot.agent.planner import CodingPlanner
from flowpilot.agent.executor import CodingExecutor


router = APIRouter(
    prefix="/api/agent",
    tags=["Agent"],
)


# ---------------------------------------------------------
# Request models
# ---------------------------------------------------------

class AgentRequest(BaseModel):
    request: str = Field(
        ...,
        min_length=1,
        description="Natural-language coding request.",
    )


# ---------------------------------------------------------
# Plan endpoint
# ---------------------------------------------------------

@router.post("/plan")
def create_plan(
    request: AgentRequest,
) -> Dict[str, Any]:

    user_request = request.request.strip()

    if not user_request:
        raise HTTPException(
            status_code=400,
            detail="Request cannot be empty.",
        )

    try:
        planner = CodingPlanner()

        result = planner.plan(
            user_request
        )

        return {
            "success": result.success,
            "request": user_request,
            "plan": _serialize(result.plan),
            "errors": getattr(
                result,
                "errors",
                [],
            ),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Planning failed: {exc}",
        ) from exc


# ---------------------------------------------------------
# Execute endpoint
# ---------------------------------------------------------

@router.post("/run")
def run_agent(
    request: AgentRequest,
) -> Dict[str, Any]:

    user_request = request.request.strip()

    if not user_request:
        raise HTTPException(
            status_code=400,
            detail="Request cannot be empty.",
        )

    try:
        planner = CodingPlanner()

        plan_result = planner.plan(
            user_request
        )

        if not plan_result.success:
            return {
                "success": False,
                "request": user_request,
                "stage": "plan",
                "errors": getattr(
                    plan_result,
                    "errors",
                    [],
                ),
            }

        executor = CodingExecutor(".")

        execution_result = executor.execute(
            plan_result.plan
        )

        return {
            "success": execution_result.success,
            "request": user_request,
            "stage": "execution",
            "summary": _call_summary(
                execution_result
            ),
            "steps": _serialize(
                getattr(
                    execution_result,
                    "steps",
                    [],
                )
            ),
            "errors": getattr(
                execution_result,
                "errors",
                [],
            ),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {exc}",
        ) from exc


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def _call_summary(
    value: Any,
) -> Dict[str, Any]:

    if value is None:
        return {}

    summary = getattr(
        value,
        "summary",
        None,
    )

    if callable(summary):
        try:
            result = summary()

            if isinstance(result, dict):
                return result

        except Exception:
            pass

    return {}


def _serialize(
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
            str(key): _serialize(item)
            for key, item in value.items()
        }

    if isinstance(
        value,
        (list, tuple),
    ):
        return [
            _serialize(item)
            for item in value
        ]

    to_dict = getattr(
        value,
        "to_dict",
        None,
    )

    if callable(to_dict):
        try:
            result = to_dict()

            if isinstance(result, dict):
                return _serialize(result)

        except Exception:
            pass

    result: Dict[str, Any] = {}

    for field_name in (
        "step_id",
        "action",
        "success",
        "output",
        "error",
        "message",
        "status",
    ):
        if hasattr(
            value,
            field_name,
        ):
            result[field_name] = _serialize(
                getattr(
                    value,
                    field_name,
                )
            )

    if result:
        return result

    return str(value)