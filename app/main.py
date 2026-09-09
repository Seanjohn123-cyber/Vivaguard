import asyncio
import json

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.assemblyai_client import AssemblyAIClient
from app.broker import SessionBroker
from app.config import settings
from app.rate_limiter import RateLimiter
from app.schemas import BrokerEvent, BrokerResponse, HealthResponse

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

broker = SessionBroker(
    rate_limiter=RateLimiter(
        max_requests_per_minute=settings.max_requests_per_minute,
        tokens_per_request=settings.tokens_per_request,
        token_bucket_capacity=settings.token_bucket_capacity,
        token_bucket_refill_rate=settings.token_bucket_refill_rate,
    )
)
assemblyai = AssemblyAIClient(
    api_key=settings.assemblyai_api_key,
    base_url=settings.assemblyai_realtime_url,
    sample_rate=settings.assemblyai_sample_rate,
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@app.post("/api/v1/route", response_model=BrokerResponse)
async def route_event(event: BrokerEvent) -> BrokerResponse:
    try:
        await broker.route_event(event.session_id, event.model_dump())
    except PermissionError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    return BrokerResponse(ok=True, message="Event routed", event_id=event.event_id)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
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


@app.websocket("/ws/audio")
async def audio_websocket_endpoint(websocket: WebSocket) -> None:
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
