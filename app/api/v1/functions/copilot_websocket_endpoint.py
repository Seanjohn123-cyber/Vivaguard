import asyncio
import json
from typing import Any
from fastapi import WebSocket, WebSocketDisconnect

from app.api.deps import assemblyai, broker
from app.core.config import settings
from app.services.evaluator import evaluate_transcript


async def copilot_websocket_endpoint(websocket: WebSocket) -> None:
    """Full-duplex real-time copilot WebSocket session for live microphone speech evaluation and traffic light signaling."""
    await websocket.accept()

    session_id = websocket.query_params.get("session_id", "copilot_default")
    await broker.register_connection(session_id, websocket)

    ground_truth = ""
    target_question = ""
    current_transcript = ""

    audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=32)

    async def on_assembly_message(msg: dict[str, Any]) -> None:
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
