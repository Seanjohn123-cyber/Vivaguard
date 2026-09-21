"""Backwards compatibility shim re-exporting app.api.deps."""
from app.api.deps import assemblyai, broker

__all__ = ["assemblyai", "broker"]
