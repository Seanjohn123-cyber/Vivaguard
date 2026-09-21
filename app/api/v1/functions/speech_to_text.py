import asyncio
from fastapi import File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.services.assemblyai_stt import transcribe_audio_file


class SpeechToTextResponse(BaseModel):
    status: str = Field("success", description="Status of the transcription request")
    transcript: str = Field(..., description="Transcribed text content from uploaded audio")


async def speech_to_text_endpoint(
    audio_file: UploadFile = File(...)
) -> SpeechToTextResponse:
    """Accepts an uploaded audio binary file and transcribes speech to text via AssemblyAI STT."""
    audio_bytes = await audio_file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded audio file content is empty.")

    try:
        transcript = await asyncio.to_thread(transcribe_audio_file, audio_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AssemblyAI speech-to-text transcription error: {str(exc)}"
        ) from exc

    return SpeechToTextResponse(
        status="success",
        transcript=transcript
    )
