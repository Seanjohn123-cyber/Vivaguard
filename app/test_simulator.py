"""Backwards compatibility shim re-exporting app.services.test_simulator."""
from app.services.test_simulator import (
    call_assemblyai_llm_gateway,
    call_gemini,
    call_llm,
    evaluate_question_response,
    generate_cumulative_report,
    generate_test_questions,
    get_next_adaptive_difficulty,
)

__all__ = [
    "call_assemblyai_llm_gateway",
    "call_gemini",
    "call_llm",
    "evaluate_question_response",
    "generate_cumulative_report",
    "generate_test_questions",
    "get_next_adaptive_difficulty",
]
