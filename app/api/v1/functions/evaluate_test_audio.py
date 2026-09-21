import asyncio
import json
from typing import Optional

from fastapi import File, Form, HTTPException, UploadFile

from app.api.deps import broker
from app.api.v1.functions.evaluate_test_question import attach_audio_to_evaluation
from app.schemas.test_interview import QuestionEvaluateResponse
from app.services.assemblyai_stt import transcribe_audio_file
from app.services.test_simulator import evaluate_question_response


async def evaluate_test_audio(
    audio_file: UploadFile = File(...),
    question_id: int = Form(1),
    question_text: str = Form(...),
    evaluation_criteria: str = Form("[]"),
    difficulty_level: str = Form("junior"),
    adaptive_mode: bool = Form(True),
    session_id: Optional[str] = Form(None),
) -> QuestionEvaluateResponse:
    """Transcribes a recorded audio answer via AssemblyAI STT and evaluates the resulting transcript."""
    audio_bytes = await audio_file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded audio content is empty")

    try:
        transcript = await asyncio.to_thread(transcribe_audio_file, audio_bytes)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AssemblyAI transcription error: {exc}") from exc

    parsed_criteria: list[str] = []
    if evaluation_criteria:
        try:
            val = json.loads(evaluation_criteria)
            if isinstance(val, list):
                parsed_criteria = [str(x) for x in val]
            else:
                parsed_criteria = [str(val)]
        except Exception:
            parsed_criteria = [c.strip() for c in evaluation_criteria.split(",") if c.strip()]

    try:
        res = await asyncio.to_thread(
            evaluate_question_response,
            question_id=question_id,
            question_text=question_text,
            criteria=parsed_criteria,
            transcript=transcript,
            difficulty_level=difficulty_level,
            adaptive_mode=adaptive_mode,
        )
        res = await attach_audio_to_evaluation(res)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to grade the response") from exc

    response = QuestionEvaluateResponse(**res)
    if session_id:
        await broker.broadcast(
            session_id,
            {
                "type": "grade_result",
                "session_id": session_id,
                "payload": response.model_dump(),
            },
        )
    return response
