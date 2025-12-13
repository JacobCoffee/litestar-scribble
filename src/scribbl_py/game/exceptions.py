"""Exception classes for game module."""

from __future__ import annotations


class GameError(Exception):
    """Base exception for all game-related errors."""


class WordBankError(GameError):
    """Raised when word bank operations fail."""


class InvalidCategoryError(WordBankError):
    """Raised when an invalid category is requested."""

    def __init__(self, category: str) -> None:
        """Initialize the exception.

        Args:
            category: The invalid category that was requested.
        """
        super().__init__(f"Invalid word category: {category}")
        self.category = category


class InvalidDifficultyError(WordBankError):
    """Raised when an invalid difficulty level is requested."""

    def __init__(self, difficulty: str) -> None:
        """Initialize the exception.

        Args:
            difficulty: The invalid difficulty that was requested.
        """
        super().__init__(f"Invalid difficulty level: {difficulty}")
        self.difficulty = difficulty


class InsufficientWordsError(WordBankError):
    """Raised when there aren't enough words available for selection."""

    def __init__(self, requested: int, available: int) -> None:
        """Initialize the exception.

        Args:
            requested: Number of words requested.
            available: Number of words available.
        """
        super().__init__(f"Requested {requested} words but only {available} available")
        self.requested = requested
        self.available = available
