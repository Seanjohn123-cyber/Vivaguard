import asyncio
import unittest
from fastapi.testclient import TestClient

from app.schemas.tts import TTSRequest
from app.api.v1.functions.convert_text_to_audio import convert_text_to_audio
from app.main import app


class TestTTSEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_tts_json_conversion(self):
        req = TTSRequest(text="Hello, who are you?", return_json=True)
        res = asyncio.run(convert_text_to_audio(req=req))
        self.assertEqual(res.status, "success")
        self.assertEqual(res.text, "Hello, who are you?")
        self.assertIsNotNone(res.reply_text)
        self.assertTrue(len(res.reply_text) > 0)
        self.assertTrue(len(res.audio_base64) > 0)

    def test_tts_binary_wav_conversion(self):
        req = TTSRequest(text="Hello, describe your system features.", return_json=False)
        res = asyncio.run(convert_text_to_audio(req=req))
        self.assertEqual(res.media_type, "audio/wav")
        self.assertTrue(len(res.body) > 44)  # Valid WAV header + PCM frames
        self.assertEqual(res.body[:4], b"RIFF")  # RIFF magic header
        self.assertIn("X-LLM-Reply", res.headers)

    def test_tts_endpoint_via_client(self):
        response = self.client.post("/api/v1/tts", json={"text": "Hello VivaGuard", "return_json": True})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("reply_text", data)
        self.assertIn("audio_base64", data)

    def test_text_to_speech_json_body(self):
        response = self.client.post("/api/text-to-speech", json={"text": "Hello, welcome to VivaGuard.", "return_json": True})
        self.assertNotEqual(response.status_code, 422)

    def test_text_to_speech_query_param(self):
        response = self.client.post("/api/text-to-speech?text=Hello")
        self.assertNotEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()


