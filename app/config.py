"""Backwards compatibility shim re-exporting app.core.config."""
from app.core.config import Settings, settings

__all__ = ["Settings", "settings"]
