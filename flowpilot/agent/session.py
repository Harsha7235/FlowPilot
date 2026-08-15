from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional

from flowpilot.agent.orchestrator import (
    AgentRunResult,
    CodingAgent,
)


@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = (
                datetime.now(timezone.utc)
                .isoformat()
            )

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }


@dataclass
class SessionTurn:
    user_message: ChatMessage
    agent_result: Optional[AgentRunResult] = None

    def to_dict(self) -> dict:
        return {
            "user_message": (
                self.user_message.to_dict()
            ),
            "agent_result": (
                self.agent_result.to_dict()
                if self.agent_result is not None
                else None
            ),
        }


@dataclass
class AgentSession:
    session_id: str
    workspace: str = "."
    messages: List[ChatMessage] = field(
        default_factory=list
    )
    turns: List[SessionTurn] = field(
        default_factory=list
    )

    def summary(self) -> dict:
        return {
            "session_id": self.session_id,
            "workspace": self.workspace,
            "messages": len(self.messages),
            "turns": len(self.turns),
        }

    def add_message(
        self,
        role: str,
        content: str,
    ) -> ChatMessage:

        message = ChatMessage(
            role=role,
            content=content,
        )

        self.messages.append(message)

        return message

    def history(
        self,
        limit: Optional[int] = None,
    ) -> List[ChatMessage]:

        if limit is None:
            return list(self.messages)

        if limit <= 0:
            return []

        return list(
            self.messages[-limit:]
        )

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "workspace": self.workspace,
            "messages": [
                message.to_dict()
                for message in self.messages
            ],
            "turns": [
                turn.to_dict()
                for turn in self.turns
            ],
        }


class AgentSessionManager:
    """
    Manages user-facing FlowPilot coding sessions.

    Each session keeps:
        - conversation history
        - agent turns
        - workspace
        - execution results
    """

    def __init__(
        self,
        workspace: str = ".",
    ) -> None:

        self.workspace = workspace

        self._sessions: dict[
            str,
            AgentSession,
        ] = {}

        self._agents: dict[
            str,
            CodingAgent,
        ] = {}

    def create_session(
        self,
        session_id: str,
    ) -> AgentSession:

        session_id = session_id.strip()

        if not session_id:
            raise ValueError(
                "Session ID cannot be empty."
            )

        if session_id in self._sessions:
            return self._sessions[
                session_id
            ]

        session = AgentSession(
            session_id=session_id,
            workspace=self.workspace,
        )

        self._sessions[
            session_id
        ] = session

        self._agents[
            session_id
        ] = CodingAgent(
            workspace=self.workspace
        )

        return session

    def get_session(
        self,
        session_id: str,
    ) -> Optional[AgentSession]:

        return self._sessions.get(
            session_id
        )

    def require_session(
        self,
        session_id: str,
    ) -> AgentSession:

        session = self.get_session(
            session_id
        )

        if session is None:
            raise KeyError(
                f"Session '{session_id}' does not exist."
            )

        return session

    def send(
        self,
        session_id: str,
        message: str,
    ) -> AgentRunResult:

        message = message.strip()

        if not message:
            raise ValueError(
                "Message cannot be empty."
            )

        session = self.require_session(
            session_id
        )

        agent = self._agents[
            session_id
        ]

        user_message = session.add_message(
            role="user",
            content=message,
        )

        result = agent.run(message)

        session.turns.append(
            SessionTurn(
                user_message=user_message,
                agent_result=result,
            )
        )

        assistant_text = self._result_text(
            result
        )

        session.add_message(
            role="assistant",
            content=assistant_text,
        )

        return result

    def list_sessions(self) -> List[str]:
        return sorted(
            self._sessions.keys()
        )

    def delete_session(
        self,
        session_id: str,
    ) -> bool:

        if session_id not in self._sessions:
            return False

        del self._sessions[
            session_id
        ]

        self._agents.pop(
            session_id,
            None,
        )

        return True

    @staticmethod
    def _result_text(
        result: AgentRunResult,
    ) -> str:

        if result.success:
            return (
                "FlowPilot completed the requested "
                "coding workflow successfully."
            )

        if result.errors:
            return (
                "FlowPilot could not complete the "
                "workflow.\n\n"
                + "\n".join(
                    f"- {error}"
                    for error in result.errors
                )
            )

        return (
            "FlowPilot stopped before completing "
            "the requested workflow."
        )


__all__ = [
    "ChatMessage",
    "SessionTurn",
    "AgentSession",
    "AgentSessionManager",
]