import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect

from app.api.deps import assemblyai
from app.core.config import settings


async def audio_websocket_endpoint(websocket: WebSocket) -> None:
    """Streams raw client audio chunks directly to AssemblyAI real-time Speech-to-Text engine over WebSocket."""
    session_id = websocket.query_params.get("session_id")
    if not session_id:
        await websocket.close(code=1008, reason="session_id is required")
        return
    if not settings.assemblyai_api_key:
        await websocket.close(code=1011, reason="AssemblyAI API key is not configured")
        return

    await websocket.accept()
    audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=32)

    async def send_transcript(message: dict[str, object]) -> None:
        normalized = assemblyai.normalize_message(message)
        if normalized is not None:
            await websocket.send_json(normalized)

    provider_task = asyncio.create_task(
        assemblyai.stream_session(audio_queue, send_transcript)
    )

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            audio_chunk = message.get("bytes")
            if audio_chunk:
                if audio_queue.full():
                    await websocket.send_json({"type": "error", "message": "Audio buffer is full"})
                    continue
                await audio_queue.put(audio_chunk)
                continue

            text = message.get("text")
            if text:
                try:
                    control = json.loads(text)
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "message": "Invalid JSON control message"})
                    continue
                if control.get("type") == "stop":
                    break
    except WebSocketDisconnect:
        pass
    finally:
        if not provider_task.done():
            await audio_queue.put(None)
            try:
                await provider_task
            except Exception:
                provider_task.cancel()
        if websocket.client_state.value == "CONNECTED":
            await websocket.close()
