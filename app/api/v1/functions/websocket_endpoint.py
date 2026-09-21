import json
from fastapi import WebSocket, WebSocketDisconnect
from app.api.deps import broker


async def websocket_endpoint(websocket: WebSocket) -> None:
    """Generic session-based WebSocket endpoint for real-time messaging and event broadcasting."""
    session_id = websocket.query_params.get("session_id")
    if not session_id:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    await broker.register_connection(session_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                if isinstance(payload, dict):
                    if not broker.rate_limiter.allow(session_id):
                        await websocket.send_text(json.dumps({"type": "error", "message": "Rate limit exceeded"}))
                        continue
                    await broker.broadcast(session_id, payload)
            except json.JSONDecodeError:
                await broker.broadcast(session_id, {"type": "error", "message": "Invalid JSON"})
    except WebSocketDisconnect:
        await broker.unregister_connection(session_id, websocket)
    except Exception:
        await broker.unregister_connection(session_id, websocket)
        raise
