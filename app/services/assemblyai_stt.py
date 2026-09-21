"""
AssemblyAI integration used to transcribe a candidate's spoken answer before
it is scored by app.services.test_simulator.evaluate_question_response.

Two ways to get a transcript are provided — pick whichever matches how your
frontend records audio:

1. transcribe_audio_file()
   The candidate records a full answer (webm/mp3/wav/m4a blob from
   MediaRecorder) and submits it once via a normal multipart upload. This
   uses AssemblyAI's standard (async, non-streaming) Speech-to-Text API and
   is the simplest, most robust option for a "record -> submit -> get score"
   flow. Recommended default.

2. LiveTranscriptionSession
   The candidate's mic audio is streamed to the backend live (raw PCM16
   frames over a WebSocket) and relayed to AssemblyAI's Realtime
   Speech-to-Text API (Universal-Streaming / Universal-3.5 Pro Realtime).
   Use this only if you actually want a live "voice agent" experience
   (partial transcripts while the candidate is still talking, barge-in,
   etc). It requires the client to send raw 16kHz mono PCM16 chunks, which
   is more work on the frontend than just uploading a recorded blob.
"""

from __future__ import annotations

import asyncio
from typing import Optional

try:
    import assemblyai as aai
    from assemblyai.streaming.v3 import (
        StreamingClient,
        StreamingClientOptions,
        StreamingEvents,
        StreamingParameters,
        TerminationEvent,
        TurnEvent,
    )
    AAI_AVAILABLE = True
except ImportError:
    aai = None
    StreamingClient = None
    StreamingClientOptions = None
    StreamingEvents = None
    StreamingParameters = None
    TerminationEvent = None
    TurnEvent = None
    AAI_AVAILABLE = False


from app.core.config import settings


def _require_api_key() -> None:
    if not settings.assemblyai_api_key:
        raise RuntimeError("ASSEMBLYAI_API_KEY is not configured")


# ---------------------------------------------------------------------------
# 1. File-based transcription (recommended default for "submit one answer")
# ---------------------------------------------------------------------------

def transcribe_audio_file(audio_bytes: bytes) -> str:
    """Uploads a fully-recorded answer to AssemblyAI and returns the transcript.

    Blocking / synchronous — call this via run_in_threadpool (or
    asyncio.to_thread) from an async FastAPI route so it doesn't stall the
    event loop.
    """
    _require_api_key()
    aai.settings.api_key = settings.assemblyai_api_key

    config = aai.TranscriptionConfig(speech_models=["universal-3-5-pro"])
    transcriber = aai.Transcriber(config=config)
    transcript = transcriber.transcribe(audio_bytes)

    if transcript.status == aai.TranscriptStatus.error:
        raise RuntimeError(f"AssemblyAI transcription failed: {transcript.error}")

    return transcript.text or ""


# ---------------------------------------------------------------------------
# 2. Realtime / streaming transcription (live mic, voice-agent style)
# ---------------------------------------------------------------------------

class LiveTranscriptionSession:
    """Wraps AssemblyAI's v3 streaming client for a single spoken answer.

    Usage inside an `async def` FastAPI websocket handler:

        session = LiveTranscriptionSession()
        session.start()
        while <audio chunks arriving>:
            session.feed(chunk)          # raw PCM16 mono 16kHz bytes
        transcript = session.finish()    # stop + return the full transcript
    """

    def __init__(self, sample_rate: int = 16000, speech_model: str = "universal-3-5-pro"):
        _require_api_key()

        self._sample_rate = sample_rate
        self._speech_model = speech_model
        self._loop = asyncio.get_running_loop()
        self._final_turns: list[str] = []
        self._latest_partial = ""
        self._turn_event = asyncio.Event()
        self._error: Optional[str] = None

        self._client = StreamingClient(
            StreamingClientOptions(
                api_key=settings.assemblyai_api_key,
                api_host="streaming.assemblyai.com",
            )
        )
        self._client.on(StreamingEvents.Turn, self._on_turn)
        self._client.on(StreamingEvents.Error, self._on_error)
        self._client.on(StreamingEvents.Termination, self._on_termination)

    # -- SDK callbacks run on a background thread, so hop back to the loop --

    def _on_turn(self, _client, event: TurnEvent) -> None:
        if event.end_of_turn and event.transcript:
            self._final_turns.append(event.transcript)
            self._latest_partial = ""
            self._loop.call_soon_threadsafe(self._turn_event.set)
        else:
            self._latest_partial = event.transcript or self._latest_partial

    def _on_error(self, _client, error) -> None:
        self._error = str(error)
        self._loop.call_soon_threadsafe(self._turn_event.set)

    def _on_termination(self, _client, _event: TerminationEvent) -> None:
        self._loop.call_soon_threadsafe(self._turn_event.set)

    # -- public API --

    def start(self) -> None:
        self._client.connect(
            StreamingParameters(
                sample_rate=self._sample_rate,
                speech_model=self._speech_model,
                format_turns=True,
            )
        )

    def feed(self, chunk: bytes) -> None:
        """Push a raw PCM16 mono audio chunk (100-1000ms recommended)."""
        self._client.stream(chunk)

    async def wait_for_turn(self, timeout: float = 8.0) -> str:
        """Optionally await one finalized turn (useful for live partial UX)."""
        try:
            await asyncio.wait_for(self._turn_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        self._turn_event.clear()
        if self._error:
            raise RuntimeError(f"AssemblyAI streaming error: {self._error}")
        return self._final_turns[-1] if self._final_turns else self._latest_partial

    def finish(self) -> str:
        """Stop the session and return the concatenated final transcript."""
        self._client.disconnect(terminate=True)
        if self._error:
            raise RuntimeError(f"AssemblyAI streaming error: {self._error}")
        return " ".join(self._final_turns).strip() or self._latest_partial.strip()
