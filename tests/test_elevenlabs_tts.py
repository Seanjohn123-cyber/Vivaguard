import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.schemas.tts import ElevenLabsTTSRequest
from app.main import app


class TestElevenLabsTTSEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("app.api.v1.functions.elevenlabs_tts.ElevenLabs")
    def test_elevenlabs_binary_mp3_response(self, mock_elevenlabs_cls):
        mock_instance = MagicMock()
        mock_instance.text_to_speech.convert.return_value = [b"FAKE_MP3_AUDIO_DATA"]
        mock_elevenlabs_cls.return_value = mock_instance

        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test_key"}):
            response = self.client.post(
                "/api/v1/elevenlabs/tts",
                json={
                    "text": "The first move is what sets everything in motion.",
                    "voice_id": "JBFqnCBsd6RMkjVDRZzb",
                    "model_id": "eleven_v3",
                    "output_format": "mp3_44100_128",
                    "return_json": False,
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["content-type"], "audio/mpeg")
            self.assertEqual(response.content, b"FAKE_MP3_AUDIO_DATA")

    @patch("app.api.v1.functions.elevenlabs_tts.ElevenLabs")
    def test_elevenlabs_json_response(self, mock_elevenlabs_cls):
        mock_instance = MagicMock()
        mock_instance.text_to_speech.convert.return_value = [b"FAKE_MP3_BYTES"]
        mock_elevenlabs_cls.return_value = mock_instance

        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test_key"}):
            response = self.client.post(
                "/api/v1/elevenlabs/tts",
                json={
                    "text": "The first move is what sets everything in motion.",
                    "return_json": True,
                },
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["voice_id"], "JBFqnCBsd6RMkjVDRZzb")
            self.assertEqual(data["model_id"], "eleven_v3")
            self.assertTrue(len(data["audio_base64"]) > 0)


if __name__ == "__main__":
    unittest.main()
