"""Backwards compatibility shim re-exporting app.services.session_manager."""
from app.services.session_manager import SessionManager, SessionRecord

__all__ = ["SessionManager", "SessionRecord"]
