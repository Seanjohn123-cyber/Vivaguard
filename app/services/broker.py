import asyncio
import json
from collections import defaultdict
from typing import Any

from app.services.rate_limiter import RateLimiter


class SessionBroker:
    def __init__(self, rate_limiter: RateLimiter | None = None) -> None:
        self._sessions: dict[str, set[Any]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self.rate_limiter = rate_limiter or RateLimiter()

    async def register_connection(self, session_id: str, websocket: Any) -> None:
        """Registers an active WebSocket client connection under the specified session ID."""
        async with self._lock:
            self._sessions[session_id].add(websocket)

    async def unregister_connection(self, session_id: str, websocket: Any) -> None:
        """Unregisters a WebSocket client connection and cleans up session key if no clients remain."""
        async with self._lock:
            clients = self._sessions.get(session_id, set())
            if websocket in clients:
                clients.remove(websocket)
            if not clients:
                self._sessions.pop(session_id, None)

    async def broadcast(self, session_id: str, message: Any) -> None:
        """Broadcasts a JSON string or dict message to all registered WebSocket clients for a session ID."""
        async with self._lock:
            clients = list(self._sessions.get(session_id, set()))

        for client in clients:
            try:
                payload = message if isinstance(message, str) else json.dumps(message)
                await client.send_text(payload)
            except Exception:
                await self.unregister_connection(session_id, client)

    async def route_event(self, session_id: str, event: dict[str, Any]) -> None:
        """Enforces session rate limiting and routes event payload to session clients via broadcast.

        Raises PermissionError if session exceeds allowed request rate.
        """
        if not self.rate_limiter.allow(session_id):
            raise PermissionError(f"Rate limit exceeded for session {session_id}")
        await self.broadcast(session_id, event)
