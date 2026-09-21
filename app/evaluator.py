"""Backwards compatibility shim re-exporting app.services.evaluator."""
from app.services.evaluator import evaluate_transcript, generate_debrief

__all__ = ["evaluate_transcript", "generate_debrief"]
