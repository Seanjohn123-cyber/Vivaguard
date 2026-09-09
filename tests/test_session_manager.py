import unittest

from app.session_manager import SessionManager


class SessionManagerTests(unittest.TestCase):
    def test_create_session_registers_state(self):
        manager = SessionManager()
        session = manager.create_session("session-3", {"user_id": "u-1"})

        self.assertEqual(session.session_id, "session-3")
        self.assertEqual(session.status, "active")
        self.assertEqual(session.metadata["user_id"], "u-1")

    def test_add_usage_updates_tokens(self):
        manager = SessionManager()
        manager.create_session("session-4")

        manager.add_usage("session-4", input_tokens=100, output_tokens=50)
        session = manager.get_session("session-4")

        self.assertEqual(session.total_input_tokens, 100)
        self.assertEqual(session.total_output_tokens, 50)
        self.assertEqual(session.total_tokens, 150)


if __name__ == "__main__":
    unittest.main()
