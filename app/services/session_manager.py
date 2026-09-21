from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionRecord:
    session_id: str
    status: str = "active"
    metadata: dict[str, Any] = field(default_factory=dict)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    created_at: float = 0.0


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}

    def create_session(self, session_id: str, metadata: dict[str, Any] | None = None) -> SessionRecord:
        """Creates and returns a new SessionRecord for session_id, or returns existing record if present."""
        if session_id in self._sessions:
            return self._sessions[session_id]

        session = SessionRecord(
            session_id=session_id,
            metadata=metadata or {},
            created_at=0.0,
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> SessionRecord | None:
        """Retrieves SessionRecord for session_id, or returns None if session does not exist."""
        return self._sessions.get(session_id)

    def update_status(self, session_id: str, status: str) -> SessionRecord | None:
        """Updates operational status (e.g. 'active', 'completed') of a session."""
        session = self._sessions.get(session_id)
        if session is None:
            return None
        session.status = status
        return session

    def add_usage(self, session_id: str, input_tokens: int = 0, output_tokens: int = 0) -> SessionRecord | None:
        """Increments input, output, and total token counters for a session."""
        session = self._sessions.get(session_id)
        if session is None:
            return None

        session.total_input_tokens += input_tokens
        session.total_output_tokens += output_tokens
        session.total_tokens += input_tokens + output_tokens
        return session
