import base64
from typing import Optional, Union

from fastapi import Body, HTTPException, Query, Response

from app.schemas.tts import TTSRequest, TTSResponse
from app.services.assemblyai_tts import generate_llm_reply, generate_voice_agent_audio


async def convert_text_to_audio(
    req: Optional[TTSRequest] = Body(None),
    text: Optional[str] = Query(None),
    voice: Optional[str] = Query("default"),
    sample_rate: Optional[int] = Query(24000),
    return_json: Optional[bool] = Query(False),
    system_prompt: Optional[str] = Query(None),
    generate_reply: Optional[bool] = Query(True),
) -> Union[Response, TTSResponse]:
    """Receives an input text message/prompt, generates an LLM response message, and synthesizes the response into spoken audio using AssemblyAI Voice Agent."""
    input_text = ""
    target_voice = "default"
    target_sample_rate = 24000
    should_return_json = False
    sys_prompt = None
    should_generate_reply = True

    if req is not None and req.text:
        input_text = req.text
        target_voice = req.voice or "default"
        target_sample_rate = req.sample_rate or 24000
        should_return_json = req.return_json or False
        sys_prompt = req.system_prompt
        should_generate_reply = req.generate_reply if req.generate_reply is not None else True
    elif text:
        input_text = text
        target_voice = voice or "default"
        target_sample_rate = sample_rate or 24000
        should_return_json = return_json or False
        sys_prompt = system_prompt
        should_generate_reply = generate_reply if generate_reply is not None else True

    input_text = input_text.strip()
    if not input_text:
        raise HTTPException(status_code=400, detail="Input text prompt cannot be empty.")

    # 1. Generate LLM AI response message if requested
    if should_generate_reply:
        try:
            reply_text = await generate_llm_reply(prompt=input_text, system_prompt=sys_prompt)
        except Exception as exc:
            reply_text = f"Received: '{input_text}'."
    else:
        reply_text = input_text

    # 2. Synthesize generated LLM reply to audio via AssemblyAI Voice Agent
    try:
        audio_bytes, duration, fmt = await generate_voice_agent_audio(
            text=reply_text,
            voice=target_voice,
            sample_rate=target_sample_rate,
            system_prompt=sys_prompt,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AssemblyAI Voice Agent conversion failed: {str(exc)}",
        ) from exc

    # 3. Return JSON metadata response or binary WAV stream
    if should_return_json:
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        return TTSResponse(
            status="success",
            text=input_text,
            reply_text=reply_text,
            format=fmt,
            sample_rate=target_sample_rate,
            audio_base64=audio_b64,
            duration_seconds=round(duration, 2),
        )

    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={
            "Content-Disposition": 'attachment; filename="speech.wav"',
            "X-Audio-Duration": str(round(duration, 2)),
            "X-LLM-Reply": reply_text.replace("\n", " "),
        },
    )
