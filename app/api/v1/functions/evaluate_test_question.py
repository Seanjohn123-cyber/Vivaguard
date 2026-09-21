import asyncio
import base64
from typing import Any

from fastapi import HTTPException

from app.api.deps import broker
from app.schemas.test_interview import QuestionEvaluateRequest, QuestionEvaluateResponse
from app.services.assemblyai_tts import generate_voice_agent_audio
from app.services.test_simulator import evaluate_question_response


async def attach_audio_to_evaluation(res: dict[str, Any]) -> dict[str, Any]:
    """Feeds the AI evaluation feedback text into AssemblyAI Voice Agent TTS to generate spoken feedback audio."""
    feedback_text = (
        f"{res.get('accuracy_rating', '')}. Score: {res.get('overall_score', '')} out of 100. "
        f"{res.get('actionable_improvements', '')} {res.get('ideal_response_summary', '')}"
    ).strip()
    if feedback_text:
        try:
            wav_bytes, _, _ = await generate_voice_agent_audio(feedback_text)
            res["audio_base64"] = base64.b64encode(wav_bytes).decode("utf-8")
        except Exception as exc:
            print(f"[AssemblyAI Voice Agent Audio Feedback Notice] {exc}")
    return res


async def evaluate_test_question(req: QuestionEvaluateRequest) -> QuestionEvaluateResponse:
    """Grades a candidate's text response to a test question, returning score, strengths, weaknesses, and AssemblyAI spoken audio feedback."""
    try:
        res = await asyncio.to_thread(
            evaluate_question_response,
            question_id=req.question_id,
            question_text=req.question_text,
            criteria=req.evaluation_criteria,
            transcript=req.transcript,
            difficulty_level=req.difficulty_level,
            adaptive_mode=req.adaptive_mode,
        )
        res = await attach_audio_to_evaluation(res)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to grade the response") from exc

    response = QuestionEvaluateResponse(**res)
    if req.session_id:
        await broker.broadcast(
            req.session_id,
            {
                "type": "grade_result",
                "session_id": req.session_id,
                "payload": response.model_dump(),
            },
        )
    return response
