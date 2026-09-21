from app.schemas.test_interview import TestGenerateRequest, TestGenerateResponse
from app.services.test_simulator import generate_test_questions


async def generate_test_interview(req: TestGenerateRequest) -> TestGenerateResponse:
    """Generates structured interview or defense questions tailored to a specific domain and difficulty tier."""
    res = generate_test_questions(
        domain=req.domain,
        question_count=req.question_count,
        difficulty_level=req.difficulty_level,
        adaptive_mode=req.adaptive_mode,
        format_name=req.format,
    )
    return TestGenerateResponse(**res)
