import asyncio
import unittest
from app.schemas.test_interview import QuestionEvaluateRequest
from app.api.v1.functions.evaluate_test_question import evaluate_test_question


class TestEvaluationAudioFeedback(unittest.TestCase):
    def test_evaluation_returns_voice_agent_audio(self):
        req = QuestionEvaluateRequest(
            question_id=1,
            question_text="Explain the principles of shared cache line invalidation.",
            evaluation_criteria=["Cache coherence", "MESI protocol"],
            transcript="Cache line invalidation ensures coherence across CPU cores by transitioning states to Invalid using the MESI protocol when a core writes to memory.",
            difficulty_level="Mid-Level",
            adaptive_mode=True
        )
        res = asyncio.run(evaluate_test_question(req))
        self.assertIsNotNone(res.audio_base64)
        self.assertGreater(len(res.audio_base64), 0)
        self.assertIsNotNone(res.actionable_improvements)
        self.assertIsNotNone(res.ideal_response_summary)


if __name__ == "__main__":
    unittest.main()
