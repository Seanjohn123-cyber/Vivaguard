import asyncio
import json
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.assemblyai_client import AssemblyAIClient
from app.broker import SessionBroker
from app.config import settings
from app.evaluator import evaluate_transcript, generate_debrief
from app.rate_limiter import RateLimiter
from app.schemas import (
    BrokerEvent,
    BrokerResponse,
    DebriefRequest,
    HealthResponse,
    QuestionEvaluateRequest,
    QuestionEvaluateResponse,
    TestCumulativeReportRequest,
    TestGenerateRequest,
    TestGenerateResponse,
)
from app.test_simulator import (
    evaluate_question_response,
    generate_cumulative_report,
    generate_test_questions,
)

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
    """Health check endpoint confirming broker service availability and status."""
    return HealthResponse()


@app.post("/api/v1/route", response_model=BrokerResponse)
async def route_event(event: BrokerEvent) -> BrokerResponse:
    """Routes an incoming broker event to all active WebSocket connections for a given session ID."""
    try:
        await broker.route_event(event.session_id, event.model_dump())
    except PermissionError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    return BrokerResponse(ok=True, message="Event routed", event_id=event.event_id)


@app.post("/api/debrief")
@app.post("/api/v1/debrief")
async def debrief_endpoint(req: DebriefRequest) -> dict[str, Any]:
    """Generates post-defense session debrief report containing STAR framework analysis, scores, and verdict."""
    return generate_debrief(
        ground_truth=req.ground_truth,
        target_question=req.target_question,
        full_transcript=req.full_transcript,
        history=req.history,
    )


# Test Interview Simulator (Mode A) Endpoints
@app.post("/api/v1/test-interview/generate", response_model=TestGenerateResponse)
@app.post("/api/v1/interview/questions/generate", response_model=TestGenerateResponse)
async def generate_test_interview(req: TestGenerateRequest) -> TestGenerateResponse:
    """Generates structured interview or defense questions tailored to domain, format, and baseline difficulty."""
    res = generate_test_questions(
        domain=req.domain,
        format_name=req.format,
        question_count=req.question_count,
        difficulty_level=req.difficulty_level,
        adaptive_mode=req.adaptive_mode,
    )
    return TestGenerateResponse(**res)


@app.post("/api/v1/test-interview/evaluate-question", response_model=QuestionEvaluateResponse)
@app.post("/api/v1/interview/grade", response_model=QuestionEvaluateResponse)
async def evaluate_test_question(req: QuestionEvaluateRequest) -> QuestionEvaluateResponse:
    """Grades a spoken response to a test question, returning score, strengths, weaknesses, and next difficulty tier."""
    res = evaluate_question_response(
        question_id=req.question_id,
        question_text=req.question_text,
        criteria=req.evaluation_criteria,
        transcript=req.transcript,
        difficulty_level=req.difficulty_level,
        adaptive_mode=req.adaptive_mode,
    )
    return QuestionEvaluateResponse(**res)


@app.post("/api/v1/test-interview/cumulative-report")
async def cumulative_test_report(req: TestCumulativeReportRequest) -> dict[str, Any]:
    """Generates a cumulative readiness report summarizing performance across all answered test questions."""
    return generate_cumulative_report(req.domain, req.format, req.evaluations)



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handles generic WebSocket connections for session-based messaging and broadcasting.

    Registers connection with session broker, listens for incoming text payloads, enforces rate limits,
    and broadcasts events to connected session peers.
    """
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


@app.websocket("/ws/copilot")
async def copilot_websocket_endpoint(websocket: WebSocket) -> None:
    """Manages full-duplex live copilot WebSocket session for real-time speech evaluation.

    Accepts audio binary stream and JSON control frames (setup/transcript/stop), pipes audio to
    AssemblyAI STT streaming service, runs `evaluate_transcript` on incoming text, and pushes
    real-time evaluation feedback signals back to client.
    """
    await websocket.accept()

    session_id = websocket.query_params.get("session_id", "copilot_default")
    await broker.register_connection(session_id, websocket)

    ground_truth = ""
    target_question = ""
    current_transcript = ""

    audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=32)

    async def on_assembly_message(msg: dict[str, Any]) -> None:
        """Callback invoked when transcript frame is received from AssemblyAI STT."""
        nonlocal current_transcript
        normalized = assemblyai.normalize_message(msg)
        if normalized and normalized.get("text"):
            text = normalized["text"]
            current_transcript += (" " + text)
            eval_res = evaluate_transcript(current_transcript, ground_truth, target_question)
            await websocket.send_json(eval_res)

    provider_task = None
    if settings.assemblyai_api_key:
        provider_task = asyncio.create_task(
            assemblyai.stream_session(audio_queue, on_assembly_message)
        )

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            audio_chunk = message.get("bytes")
            if audio_chunk:
                if provider_task and not audio_queue.full():
                    await audio_queue.put(audio_chunk)
                continue

            text = message.get("text")
            if text:
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "message": "Invalid JSON control message"})
                    continue

                msg_type = payload.get("type")
                if msg_type == "setup":
                    ground_truth = payload.get("ground_truth", "")
                    target_question = payload.get("target_question", "")
                    await websocket.send_json(
                        {
                            "type": "setup_ack",
                            "stt_engine": (
                                "AssemblyAI Realtime STT" if settings.assemblyai_api_key else "Web Speech Engine"
                            ),
                        }
                    )
                elif msg_type == "transcript":
                    tx = payload.get("text", "")
                    current_transcript = tx
                    eval_res = evaluate_transcript(current_transcript, ground_truth, target_question)
                    await websocket.send_json(eval_res)
                elif msg_type == "stop":
                    break
    except WebSocketDisconnect:
        pass
    finally:
        await broker.unregister_connection(session_id, websocket)
        if provider_task and not provider_task.done():
            await audio_queue.put(None)
            try:
                await provider_task
            except Exception:
                provider_task.cancel()
        if websocket.client_state.value == "CONNECTED":
            await websocket.close()


@app.websocket("/ws/audio")
async def audio_websocket_endpoint(websocket: WebSocket) -> None:
    """Streams raw client audio chunks directly to AssemblyAI real-time STT engine over WebSocket.

    Pipes incoming PCM bytes to AssemblyAI stream and returns normalized transcript JSON frames back to client.
    """
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
