"""Compatibility alias for exam models."""

from app.models.exam import Question, Quiz, QuizAttempt

__all__ = ["Quiz", "Question", "QuizAttempt"]
