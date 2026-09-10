import asyncio
import json
from typing import Any, Awaitable, Callable

import websockets


class AssemblyAIClient:
    def __init__(self, api_key: str, base_url: str, sample_rate: int = 16000) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.sample_rate = sample_rate

    def headers(self) -> dict[str, str]:
        """Returns HTTP header dictionary with Authorization header containing AssemblyAI API key."""
        return {"Authorization": self.api_key}

    async def connect(self) -> Any:
        """Establishes an asynchronous WebSocket connection to AssemblyAI's real-time streaming server.

        Raises ValueError if AssemblyAI API key is missing.
        """
        if not self.api_key:
            raise ValueError("AssemblyAI API key is missing")

        return await websockets.connect(
            self.base_url,
            extra_headers=self.headers(),
        )

    async def begin_session(
        self,
        websocket: Any,
        *,
        speaker_labels: bool = False,
        formatters: list[str] | None = None,
    ) -> None:
        """Initializes AssemblyAI streaming session (AssemblyAI v3 sends Begin event automatically)."""
        # v3 sends the Begin event after the connection opens; no client message is required.
        return None

    async def send_audio_chunk(self, websocket: Any, audio_chunk: bytes) -> None:
        """Sends raw PCM audio byte chunk over the active AssemblyAI WebSocket connection."""
        if audio_chunk:
            await websocket.send(audio_chunk)

    @staticmethod
    def normalize_message(message: dict[str, Any]) -> dict[str, Any] | None:
        """Normalizes raw AssemblyAI JSON response into standard transcript payload dictionary.

        Returns normalized dictionary containing transcript text, finality status, confidence score,
        and word timestamps, or None if message type is not a transcript event.
        """
        message_type = message.get("message_type")
        if message.get("type") == "Turn":
            return {
                "type": "transcript",
                "final": bool(message.get("end_of_turn", False)),
                "text": message.get("transcript", ""),
                "confidence": message.get("end_of_turn_confidence"),
                "words": message.get("words", []),
            }
        if message_type not in {"partial_transcript", "final_transcript"}:
            return None

        return {
            "type": "transcript",
            "final": message_type == "final_transcript",
            "text": message.get("text", ""),
            "confidence": message.get("confidence"),
            "words": message.get("words", []),
        }

    async def receive_messages(
        self,
        websocket: Any,
        callback: Callable[[dict[str, Any]], Awaitable[None] | None],
    ) -> None:
        """Listens for WebSocket frames from AssemblyAI, parses JSON, and invokes callback function."""
        async for raw in websocket:
            if isinstance(raw, bytes):
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if callable(callback):
                result = callback(payload)
                if asyncio.iscoroutine(result):
                    await result

    async def stream_session(
        self,
        audio_queue: asyncio.Queue[bytes | None],
        on_message: Callable[[dict[str, Any]], Awaitable[None] | None],
    ) -> None:
        """Orchestrates bidirectional streaming session with AssemblyAI real-time STT engine.

        Concurrently runs an audio sender task to pull chunks from `audio_queue` and a transcript
        receiver task to invoke `on_message` on incoming transcripts.
        """
        websocket = await self.connect()
        try:
            await self.begin_session(websocket)

            async def send_audio() -> None:
                while True:
                    chunk = await audio_queue.get()
                    if chunk is None:
                        await websocket.send(json.dumps({"message_type": "Terminate"}))
                        return
                    await self.send_audio_chunk(websocket, chunk)

            async def receive_transcripts() -> None:
                await self.receive_messages(websocket, on_message)

            sender = asyncio.create_task(send_audio())
            receiver = asyncio.create_task(receive_transcripts())
            done, pending = await asyncio.wait(
                {sender, receiver},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            for task in done:
                task.result()
        finally:
            await websocket.close()
