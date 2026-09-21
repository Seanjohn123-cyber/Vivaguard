from datetime import datetime, timedelta, timezone
import hmac
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


def _require_auth_config() -> None:
    if not settings.auth_jwt_secret:
        raise HTTPException(status_code=503, detail="Authentication is not configured")


def authenticate_user(username: str, password: str) -> bool:
    return bool(
        settings.auth_username
        and settings.auth_password
        and hmac.compare_digest(username, settings.auth_username)
        and hmac.compare_digest(password, settings.auth_password)
    )


def create_access_token(subject: str) -> str:
    _require_auth_config()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.auth_token_expire_minutes)
    payload = {"sub": subject, "exp": expires_at, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, settings.auth_jwt_secret, algorithm="HS256")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    _require_auth_config()
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")

    try:
        payload: dict[str, Any] = jwt.decode(
            credentials.credentials,
            settings.auth_jwt_secret,
            algorithms=["HS256"],
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token subject is missing")
    return subject


def authenticate_websocket_token(token: str | None) -> str:
    _require_auth_config()
    if not token:
        raise ValueError("Bearer token required")

    try:
        payload: dict[str, Any] = jwt.decode(token, settings.auth_jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise ValueError("Invalid or expired token") from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ValueError("Token subject is missing")
    return subject