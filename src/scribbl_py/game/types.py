"""Type definitions for game mode functionality."""

from __future__ import annotations

from enum import StrEnum


class WordCategory(StrEnum):
    """Categories for word selection in CanvasClash mode."""

    ANIMALS = "animals"
    OBJECTS = "objects"
    ACTIONS = "actions"
    PLACES = "places"
    FOOD = "food"
    SPORTS = "sports"
    MOVIES = "movies"
    NATURE = "nature"
    TECHNOLOGY = "technology"
    PROFESSIONS = "professions"


class DifficultyLevel(StrEnum):
    """Difficulty levels for word selection."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class GameState(StrEnum):
    """Current state of a game room."""

    LOBBY = "lobby"
    IN_PROGRESS = "in_progress"
    ROUND_END = "round_end"
    GAME_END = "game_end"


class GameMode(StrEnum):
    """Available game modes."""

    SKRIBBL = "skribbl"
    COLLABORATIVE = "collaborative"


class PlayerState(StrEnum):
    """Current state of a player in the game."""

    WAITING = "waiting"
    DRAWING = "drawing"
    GUESSING = "guessing"
    SPECTATING = "spectating"


class ChatMessageType(StrEnum):
    """Type of chat message."""

    GUESS = "guess"
    SYSTEM = "system"
    CHAT = "chat"
    HINT = "hint"
