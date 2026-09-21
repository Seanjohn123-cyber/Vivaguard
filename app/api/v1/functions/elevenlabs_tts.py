import base64
import os
from typing import Optional, Union

from dotenv import load_dotenv
from fastapi import Body, HTTPException, Query, Response
from elevenlabs.client import ElevenLabs

from app.core.config import settings
from app.schemas.tts import ElevenLabsTTSRequest, ElevenLabsTTSResponse

load_dotenv()


async def convert_elevenlabs_tts(
    payload: Optional[ElevenLabsTTSRequest] = Body(None),
    text: Optional[str] = Query(None),
    voice_id: Optional[str] = Query("JBFqnCBsd6RMkjVDRZzb"),
    model_id: Optional[str] = Query("eleven_v3"),
    output_format: Optional[str] = Query("mp3_44100_128"),
    return_json: Optional[bool] = Query(False),
) -> Union[Response, ElevenLabsTTSResponse]:
    """
    Accepts text payload and synthesizes high-quality speech audio via ElevenLabs API.
    Returns binary MP3 audio directly or JSON response payload.
    """
    input_text = "The first move is what sets everything in motion."
    target_voice_id = "JBFqnCBsd6RMkjVDRZzb"
    target_model_id = "eleven_v3"
    target_output_format = "mp3_44100_128"
    should_return_json = False

    if payload is not None and payload.text:
        input_text = payload.text
        target_voice_id = payload.voice_id or "JBFqnCBsd6RMkjVDRZzb"
        target_model_id = payload.model_id or "eleven_v3"
        target_output_format = payload.output_format or "mp3_44100_128"
        should_return_json = payload.return_json or False
    elif text:
        input_text = text
        target_voice_id = voice_id or "JBFqnCBsd6RMkjVDRZzb"
        target_model_id = model_id or "eleven_v3"
        target_output_format = output_format or "mp3_44100_128"
        should_return_json = return_json or False

    input_text = input_text.strip()
    if not input_text:
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")

    api_key = os.getenv("ELEVENLABS_API_KEY") or getattr(settings, "elevenlabs_api_key", None)
    if not api_key:
        load_dotenv(override=True)
        api_key = os.getenv("ELEVENLABS_API_KEY") or getattr(settings, "elevenlabs_api_key", None)

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="ELEVENLABS_API_KEY environment variable or setting is not configured."
        )

    try:
        client = ElevenLabs(api_key=api_key)
        audio_generator = client.text_to_speech.convert(
            text=input_text,
            voice_id=target_voice_id,
            model_id=target_model_id,
            output_format=target_output_format,
        )
        
        # Consume byte generator into bytes
        if isinstance(audio_generator, (bytes, bytearray)):
            audio_bytes = bytes(audio_generator)
        else:
            audio_bytes = b"".join(chunk for chunk in audio_generator if chunk)

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"ElevenLabs TTS generation error: {str(exc)}"
        ) from exc

    if should_return_json:
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        return ElevenLabsTTSResponse(
            status="success",
            text=input_text,
            voice_id=target_voice_id,
            model_id=target_model_id,
            output_format=target_output_format,
            audio_base64=audio_b64,
        )

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": 'inline; filename="elevenlabs-speech.mp3"'
        }
    )
