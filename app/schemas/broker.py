from typing import Any, Literal
from pydantic import BaseModel, Field


class BrokerEvent(BaseModel):
    event_id: str = Field(..., description="Unique UUID or string identifying the event", example="evt-98765")
    session_id: str = Field(..., description="Target session ID for live WebSocket client broadcasting", example="session-123")
    type: Literal["audio", "transcript", "tool_call", "status", "error"] = Field(..., description="Category type of the broker event", example="transcript")
    payload: dict[str, Any] = Field(default_factory=dict, description="Event payload dictionary passed to subscribers", example={"text": "Hello VivaGuard", "final": True})


class BrokerResponse(BaseModel):
    ok: bool = Field(True, description="Indicates whether the event routing succeeded", example=True)
    message: str = Field("Event routed", description="Status message detailing routing execution", example="Event routed")
    event_id: str | None = Field(None, description="Event ID that was dispatched", example="evt-98765")

