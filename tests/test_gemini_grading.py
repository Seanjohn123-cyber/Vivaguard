import unittest
from unittest.mock import patch

from app.test_simulator import evaluate_question_response


class GeminiGradingTests(unittest.TestCase):
    @patch("app.test_simulator.call_gemini")
    def test_grading_returns_frontend_score_payload(self, call_gemini):
        call_gemini.return_value = (
            '{"overall_score": 92, "accuracy_rating": "Strong Answer", '
            '"strengths": ["Explains quorum reads"], '
            '"weaknesses": ["Needs latency figures"], '
            '"actionable_improvements": "Quantify read latency.", '
            '"ideal_response_summary": "Use quorum reads with bounded staleness."}'
        )

        result = evaluate_question_response(
            question_id=1,
            question_text="How would you prevent stale reads?",
            criteria=["Addresses quorum reads"],
            transcript="I would use quorum reads.",
            difficulty_level="Senior",
            adaptive_mode=True,
        )

        self.assertEqual(result["score"], 92)
        self.assertEqual(result["overall_score"], 92)
        self.assertEqual(result["next_recommended_difficulty"], "Senior")
        self.assertIn("strengths", result)
        self.assertIn("weaknesses", result)


if __name__ == "__main__":
    unittest.main()