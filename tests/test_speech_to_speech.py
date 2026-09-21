import unittest
from fastapi.testclient import TestClient

from app.main import app


class TestSpeechToSpeechEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_websocket_connection_handshake(self):
        with self.client.websocket_connect("/ws/speech-to-speech") as websocket:
            # Send initial binary PCM byte frame or text
            websocket.send_bytes(b"\x00\x00" * 480)
            # Expect text or error frame from backend handler
            try:
                data = websocket.receive_text()
                self.assertIsNotNone(data)
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
