import asyncio
import base64
import json
import os
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv

from app.core.config import settings

load_dotenv()

ASSEMBLYAI_API_KEY = getattr(settings, "assemblyai_api_key", None) or os.getenv("ASSEMBLYAI_API_KEY", "")
# Official AssemblyAI Voice Agent WebSocket endpoint
ASSEMBLYAI_VOICE_AGENT_WS = "wss://agents.assemblyai.com/v1/ws"


async def speech_to_speech_endpoint(client_ws: WebSocket):
    """
    Bi-directional Speech-to-Speech WebSocket conforming to official AssemblyAI Voice Agent specification:
    1. Client connects to backend WebSocket.
    2. Backend connects to AssemblyAI Voice Agent WS (wss://agents.assemblyai.com/v1/ws) with Authorization.
    3. Backend initializes session config via `session.update`.
    4. Client streams audio -> backend packages as `input.audio` JSON -> sent to AssemblyAI.
    5. AssemblyAI streams events & responses (`session.ready`, `reply.audio`, `transcript.agent`, etc.) -> backend relays to client.
    """
    await client_ws.accept()

    api_key = ASSEMBLYAI_API_KEY or getattr(settings, "assemblyai_api_key", "")
    if not api_key:
        print("[S2S Warning] ASSEMBLYAI_API_KEY is not set. Speech-to-Speech agent connection requires API key.")

    headers = {
        "Authorization": api_key
    }

    try:
        async with websockets.connect(
            ASSEMBLYAI_VOICE_AGENT_WS,
            extra_headers=headers,
            open_timeout=5.0,
            close_timeout=2.0,
        ) as aai_ws:
            # 1. Initialize session configuration for VivaGuard AI Voice Agent
            session_config = {
                "type": "session.update",
                "session": {
                    "instructions": (
                        "You are VivaGuard AI, an attentive voice security and defense agent. "
                        "Keep answers conversational, friendly, and concise in 1 to 2 sentences."
                    ),
                    "output_format": {
                        "encoding": "pcm_s16le",
                        "sample_rate": 24000
                    }
                }
            }
            await aai_ws.send(json.dumps(session_config))

            # Forward client audio/control frames to AssemblyAI Voice Agent
            async def forward_client_audio_to_agent():
                try:
                    while True:
                        data = await client_ws.receive()
                        if "bytes" in data and data["bytes"]:
                            # Convert raw binary PCM audio bytes to input.audio JSON payload
                            raw_pcm = data["bytes"]
                            audio_b64 = base64.b64encode(raw_pcm).decode("utf-8")
                            payload = {
                                "type": "input.audio",
                                "audio": audio_b64
                            }
                            await aai_ws.send(json.dumps(payload))
                        elif "text" in data and data["text"]:
                            # Control events (mute, interrupt, session updates, or pre-formatted JSON)
                            text_msg = data["text"]
                            # If client sent raw text prompt, convert to input.text
                            try:
                                parsed = json.loads(text_msg)
                                await aai_ws.send(json.dumps(parsed))
                            except Exception:
                                # Raw string text prompt
                                payload = {
                                    "type": "input.text",
                                    "text": text_msg
                                }
                                await aai_ws.send(json.dumps(payload))
                except (WebSocketDisconnect, asyncio.CancelledError):
                    pass

            # Stream events and speech responses from AssemblyAI Voice Agent back to client
            async def forward_agent_speech_to_client():
                try:
                    async for message in aai_ws:
                        if isinstance(message, bytes):
                            # Binary audio frame from AssemblyAI -> send binary bytes to client
                            await client_ws.send_bytes(message)
                        else:
                            # JSON event message (reply.audio, transcript, etc.) -> relay text to client
                            await client_ws.send_text(message)
                except (WebSocketDisconnect, asyncio.CancelledError):
                    pass

            # Run both bi-directional streaming loops concurrently
            await asyncio.gather(
                forward_client_audio_to_agent(),
                forward_agent_speech_to_client()
            )

    except WebSocketDisconnect:
        print("[S2S] Client disconnected cleanly.")
    except Exception as e:
        print(f"[S2S] Voice Agent connection notice/error: {e}")
        try:
            await client_ws.send_text(json.dumps({
                "type": "error",
                "message": f"AssemblyAI Voice Agent connection notice: {str(e)}"
            }))
            await client_ws.close(code=1011, reason=str(e))
        except Exception:
            pass


# Standalone runner app if executed directly
app = FastAPI(title="VivaGuard - AssemblyAI Speech-to-Speech Agent")
app.add_api_websocket_route("/ws/speech-to-speech", speech_to_speech_endpoint)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("speech_to_speech:app", host="0.0.0.0", port=8001, reload=True)