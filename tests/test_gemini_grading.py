import unittest
from unittest.mock import patch

from app.services.test_simulator import call_llm, evaluate_question_response


class GeminiGradingTests(unittest.TestCase):
    @patch("app.services.test_simulator.call_gemini")
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

    @patch("app.services.test_simulator.call_assemblyai_llm_gateway")
    @patch("app.services.test_simulator.call_gemini")
    def test_llm_fallback_to_assemblyai(self, mock_call_gemini, mock_call_assemblyai):
        mock_call_gemini.return_value = None
        mock_call_assemblyai.return_value = "AssemblyAI Response"

        res = call_llm("test prompt")
        self.assertEqual(res, "AssemblyAI Response")
        mock_call_gemini.assert_called_once_with("test prompt")
        mock_call_assemblyai.assert_called_once_with("test prompt")


if __name__ == "__main__":
    unittest.main()