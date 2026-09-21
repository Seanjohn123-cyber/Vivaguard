import unittest
from unittest.mock import patch

from app.auth import authenticate_user, authenticate_websocket_token, create_access_token
from app.config import settings


class AuthenticationTests(unittest.TestCase):
    def test_token_contains_subject_and_expiration(self):
        with patch.object(settings, "auth_jwt_secret", "test-secret"), patch.object(
            settings, "auth_token_expire_minutes", 30
        ):
            token = create_access_token("candidate-1")
            self.assertEqual(authenticate_websocket_token(token), "candidate-1")

    def test_credentials_are_required_and_websocket_token_is_validated(self):
        with patch.object(settings, "auth_username", "candidate"), patch.object(
            settings, "auth_password", "password"
        ), patch.object(settings, "auth_jwt_secret", "test-secret"):
            self.assertTrue(authenticate_user("candidate", "password"))
            self.assertFalse(authenticate_user("candidate", "wrong"))
            token = create_access_token("candidate")
            self.assertEqual(authenticate_websocket_token(token), "candidate")

            with self.assertRaises(ValueError):
                authenticate_websocket_token("invalid-token")


if __name__ == "__main__":
    unittest.main()