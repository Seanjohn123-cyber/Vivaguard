import json
from app.schemas import QuestionEvaluateRequest
from app.test_simulator import evaluate_question_response


def test_prd_schema_parsing():
    print("--- 1. Testing Schema Parsing with PRD Payload ---")
    prd_payload = {
        "question_id": 1,
        "question_text": "How did you handle race conditions in your shared cache implementation?",
        "evaluation_criteria": [
            "Mentions mutex locks, semaphores, or atomic operations",
            "Explains dead-lock prevention strategies",
            "Provides a concrete trade-off example"
        ],
        "transcript": (
            "To handle race conditions in our shared memory cache, we utilized std::atomic variables for reference counting "
            "and fine-grained read-write mutex locks on individual hash buckets. To prevent deadlocks, we established a strict "
            "global lock acquisition hierarchy. The primary trade-off was increased memory overhead for bucket headers in exchange "
            "for dropping lock contention by 80% under peak concurrent workloads."
        ),
        "difficulty_level": "Senior"
    }

    req = QuestionEvaluateRequest(**prd_payload)
    print(f"Parsed Question ID: {req.question_id}")
    print(f"Parsed Question Text: {req.question_text}")
    print(f"Parsed Evaluation Criteria ({len(req.evaluation_criteria)} items):")
    for idx, c in enumerate(req.evaluation_criteria, 1):
        print(f"  {idx}. {c}")
    print(f"Transcript length: {len(req.transcript)} chars")
    assert len(req.evaluation_criteria) == 3, "Failed to parse evaluation_criteria list"
    print("[SUCCESS] Schema parsing test passed successfully!\n")
    return req


def test_prd_evaluation_response(req: QuestionEvaluateRequest):
    print("--- 2. Evaluating Candidate Response against PRD Criteria ---")
    result = evaluate_question_response(
        question_id=req.question_id,
        question_text=req.question_text,
        criteria=req.evaluation_criteria,
        transcript=req.transcript,
        difficulty_level=req.difficulty_level,
        adaptive_mode=req.adaptive_mode
    )

    assert "overall_score" in result, "Missing overall_score in result"
    assert "accuracy_rating" in result, "Missing accuracy_rating in result"
    assert len(result["strengths"]) > 0, "Missing strengths in result"
    assert len(result["weaknesses"]) > 0, "Missing weaknesses in result"
    print("[SUCCESS] PRD question evaluation test completed successfully!\n")


if __name__ == "__main__":
    req = test_prd_schema_parsing()
    test_prd_evaluation_response(req)
