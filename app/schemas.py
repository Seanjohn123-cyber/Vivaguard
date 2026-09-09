from typing import Any, Literal

from pydantic import BaseModel, Field


class BrokerEvent(BaseModel):
    event_id: str = Field(..., description="Unique event id")
    session_id: str = Field(..., description="Target session")
    type: Literal["audio", "transcript", "tool_call", "status", "error"]
    payload: dict[str, Any] = Field(default_factory=dict)


class BrokerResponse(BaseModel):
    ok: bool = True
    message: str = "Event routed"
    event_id: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "vivaguard-broker"
