import asyncio
from fastapi import HTTPException

from app.api.deps import broker
from app.schemas.test_interview import QuestionEvaluateRequest, QuestionEvaluateResponse
from app.services.test_simulator import evaluate_question_response


async def llm_response_endpoint(req: QuestionEvaluateRequest) -> QuestionEvaluateResponse:
    """Evaluates candidate response transcript against criteria using Gemini LLM and yields score, feedback, and model summary."""
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
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM evaluation response generation failed: {str(exc)}") from exc

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
