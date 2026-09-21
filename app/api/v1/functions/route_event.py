from fastapi import HTTPException
from app.api.deps import broker
from app.schemas.broker import BrokerEvent, BrokerResponse


async def route_event(event: BrokerEvent) -> BrokerResponse:
    """Routes an incoming broker event to all active WebSocket subscriber connections for a given session ID."""
    try:
        await broker.route_event(event.session_id, event.model_dump())
    except PermissionError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    return BrokerResponse(ok=True, message="Event routed", event_id=event.event_id)
