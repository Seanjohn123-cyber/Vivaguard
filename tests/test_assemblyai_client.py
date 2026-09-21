import unittest
from unittest.mock import AsyncMock, patch

from app.assemblyai_client import AssemblyAIClient


class AssemblyAIClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_connect_adds_keyterms_prompt_to_stream_url(self):
        client = AssemblyAIClient(
            api_key="test-key",
            base_url="wss://streaming.example/v3/ws?sample_rate=16000",
        )
        fake_websocket = object()

        with patch("app.assemblyai_client.websockets.connect", new_callable=AsyncMock) as connect:
            connect.return_value = fake_websocket
            await client.connect(["Redis", "quorum reads"])

        url = connect.call_args.args[0]
        self.assertIn("keyterms_prompt=%5B%22Redis%22%2C+%22quorum+reads%22%5D", url)
        self.assertEqual(connect.call_args.kwargs["extra_headers"], {"Authorization": "test-key"})


if __name__ == "__main__":
    unittest.main()