"""Game mode data models for CanvasClash Mode.

This module defines the core data structures for the drawing guessing game mode,
including game rooms, players, rounds, word banks, and game state management.
"""

from __future__ import annotations

import math
import random
import string
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class GameState(StrEnum):
    """State of the game room.

    The game progresses through these states in order:
    LOBBY -> WORD_SELECTION -> DRAWING -> ROUND_END -> (repeat or GAME_OVER)
    """

    LOBBY = "lobby"  # Waiting for players to join and host to start
    WORD_SELECTION = "word_selection"  # Drawer is choosing a word
    DRAWING = "drawing"  # Active drawing round, players guessing
    ROUND_END = "round_end"  # Round finished, showing results
    GAME_OVER = "game_over"  # All rounds complete, final scores


class GameMode(StrEnum):
    """Available game modes."""

    SKRIBBL = "skribbl"  # Drawing guessing game
    COLLABORATIVE = "collaborative"  # Free-form collaborative whiteboard


class PlayerState(StrEnum):
    """Connection state of a player."""

    CONNECTED = "connected"  # Active connection
    DISCONNECTED = "disconnected"  # Temporarily disconnected
    LEFT = "left"  # Permanently left the game


class WordCategory(StrEnum):
    """Categories for word banks."""

    ANIMALS = "animals"
    OBJECTS = "objects"
    ACTIONS = "actions"
    FOOD = "food"
    PLACES = "places"
    PEOPLE = "people"
    NATURE = "nature"
    TECHNOLOGY = "technology"
    SPORTS = "sports"
    ENTERTAINMENT = "entertainment"
    CUSTOM = "custom"  # User-defined words


class ChatMessageType(StrEnum):
    """Type of chat message."""

    GUESS = "guess"  # Player guess attempt
    SYSTEM = "system"  # System notification (user joined/left, etc.)
    HINT = "hint"  # Close guess hint
    CORRECT = "correct"  # Correct guess notification
    DRAWER = "drawer"  # Message from drawer (only when round ends)


class GuessResult(StrEnum):
    """Result of a guess attempt."""

    CORRECT = "correct"  # Exact match
    CLOSE = "close"  # Close to the word (Levenshtein distance)
    WRONG = "wrong"  # Not close
    ALREADY_GUESSED = "already_guessed"  # Player already guessed correctly
    DRAWER = "drawer"  # Drawer cannot guess
    INVALID = "invalid"  # Invalid guess (too short, etc.)


@dataclass
class Player:
    """Represents a player in the game room.

    Tracks player identity, score, connection state, and game progress.

    Attributes:
        id: Unique identifier for the player.
        user_id: User ID from the session/auth system.
        user_name: Display name shown to other players.
        avatar_url: Optional URL to player's avatar image.
        score: Current total score across all rounds.
        is_host: Whether this player is the room host.
        is_spectator: Whether this player is a spectator (cannot draw/guess).
        connection_state: Current connection status.
        has_guessed: Whether player has guessed correctly in current round.
        guess_time: Time taken to guess (for scoring calculation).
        joined_at: When the player joined the room.
        last_seen: Last activity timestamp for connection tracking.
    """

    id: UUID = field(default_factory=uuid4)
    user_id: str = ""
    user_name: str = "Anonymous"
    avatar_url: str | None = None
    auth_user_id: UUID | None = None  # Linked auth user for stats tracking
    score: int = 0
    is_host: bool = False
    is_spectator: bool = False
    connection_state: PlayerState = PlayerState.CONNECTED
    has_guessed: bool = False
    guess_time: float | None = None
    joined_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_seen: datetime = field(default_factory=lambda: datetime.now(UTC))

    def reset_round_state(self) -> None:
        """Reset per-round state (has_guessed, guess_time)."""
        self.has_guessed = False
        self.guess_time = None

    def award_points(self, points: int) -> None:
        """Add points to player's total score.

        Args:
            points: Number of points to award.
        """
        self.score += points

    def mark_active(self) -> None:
        """Update last_seen timestamp to current time."""
        self.last_seen = datetime.now(UTC)


@dataclass
class WordBank:
    """Collection of words organized by category.

    Attributes:
        id: Unique identifier for the word bank.
        name: Display name for the word bank.
        category: Category this word bank belongs to.
        words: List of words available for selection.
        difficulty: Difficulty level (1-5, affects scoring).
        is_default: Whether this is a built-in word bank.
        created_by: User ID of creator (for custom word banks).
        created_at: When the word bank was created.
    """

    id: UUID = field(default_factory=uuid4)
    name: str = "Default Words"
    category: WordCategory = WordCategory.OBJECTS
    words: list[str] = field(default_factory=list)
    difficulty: int = 1  # 1-5 scale
    is_default: bool = True
    created_by: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def get_random_words(self, count: int = 3) -> list[str]:
        """Get random words for selection.

        Args:
            count: Number of random words to return.

        Returns:
            List of random words from the bank.
        """
        if len(self.words) < count:
            return self.words.copy()
        return random.sample(self.words, count)

    def add_word(self, word: str) -> None:
        """Add a word to the bank if not already present.

        Args:
            word: Word to add (will be lowercased and stripped).
        """
        normalized = word.lower().strip()
        if normalized and normalized not in self.words:
            self.words.append(normalized)

    def remove_word(self, word: str) -> None:
        """Remove a word from the bank.

        Args:
            word: Word to remove.
        """
        normalized = word.lower().strip()
        if normalized in self.words:
            self.words.remove(normalized)


@dataclass
class Guess:
    """Represents a player's guess attempt.

    Attributes:
        id: Unique identifier for the guess.
        player_id: ID of the player who made the guess.
        player_name: Name of the player (for display).
        guess_text: The guessed word/phrase.
        result: Result of the guess (correct/close/wrong).
        points_awarded: Points awarded for correct guess.
        time_elapsed: Seconds elapsed since round start.
        timestamp: When the guess was made.
    """

    id: UUID = field(default_factory=uuid4)
    player_id: UUID = field(default_factory=uuid4)
    player_name: str = ""
    guess_text: str = ""
    result: GuessResult = GuessResult.WRONG
    points_awarded: int = 0
    time_elapsed: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ChatMessage:
    """Chat message for guessing and communication.

    Attributes:
        id: Unique identifier for the message.
        message_type: Type of message (guess, system, hint, etc.).
        sender_id: ID of the player who sent the message.
        sender_name: Name of the sender for display.
        content: Message text content.
        metadata: Additional data (e.g., points awarded, guess result).
        timestamp: When the message was sent.
    """

    id: UUID = field(default_factory=uuid4)
    message_type: ChatMessageType = ChatMessageType.GUESS
    sender_id: UUID | None = None
    sender_name: str = "System"
    content: str = ""
    metadata: dict[str, str | int | float | bool] | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def system(cls, content: str, **metadata: str | float | bool) -> ChatMessage:
        """Create a system message.

        Args:
            content: Message text.
            **metadata: Additional metadata key-value pairs.

        Returns:
            System chat message.
        """
        return cls(message_type=ChatMessageType.SYSTEM, content=content, metadata=metadata or None)

    @classmethod
    def hint(cls, player_name: str, **metadata: str | float | bool) -> ChatMessage:
        """Create a hint message for close guesses.

        Args:
            player_name: Name of the player who made the close guess.
            **metadata: Additional metadata.

        Returns:
            Hint chat message.
        """
        return cls(
            message_type=ChatMessageType.HINT,
            sender_name=player_name,
            content=f"{player_name} is close!",
            metadata=metadata or None,
        )


@dataclass
class Round:
    """Represents a single game round.

    Attributes:
        id: Unique identifier for the round.
        round_number: Sequential round number (1-indexed).
        drawer_id: ID of the player drawing this round.
        word: The word being drawn (hidden from guessers).
        word_hint: Partially revealed word (e.g., "_ _ _ _ _").
        word_options: Three words offered to drawer for selection.
        canvas_id: ID of the canvas for this round.
        start_time: When the round started.
        end_time: When the round ended (or will end).
        duration_seconds: Total round duration in seconds.
        guesses: All guess attempts made during the round.
        chat_messages: All chat messages from the round.
        scores: Points awarded to each player this round.
        is_active: Whether the round is currently in progress.
    """

    id: UUID = field(default_factory=uuid4)
    round_number: int = 1
    drawer_id: UUID = field(default_factory=uuid4)
    word: str = ""
    word_hint: str = ""
    word_options: list[str] = field(default_factory=list)
    canvas_id: UUID = field(default_factory=uuid4)
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_seconds: int = 80
    guesses: list[Guess] = field(default_factory=list)
    chat_messages: list[ChatMessage] = field(default_factory=list)
    scores: dict[str, int] = field(default_factory=dict)  # player_id -> points
    strokes: list[dict] = field(default_factory=list)  # Drawing strokes for replay
    is_active: bool = False

    def add_stroke(self, stroke: dict) -> None:
        """Add a drawing stroke to the round.

        Args:
            stroke: Stroke data (color, width, from_x, from_y, to_x, to_y).
        """
        self.strokes.append(stroke)

    def clear_strokes(self) -> None:
        """Clear all strokes (when canvas is cleared)."""
        self.strokes.clear()

    def start(self, word: str) -> None:
        """Start the round with the selected word.

        Args:
            word: The word to be drawn.
        """
        self.word = word.lower().strip()
        # Generate hint with word separation for multi-word phrases
        # Each word gets underscores, separated by 3 spaces between words
        words = self.word.split(" ")
        word_hints = []
        for w in words:
            # Each letter gets an underscore with space between
            word_hints.append(" ".join("_" * len(w)))
        # Join words with 3 spaces for visual separation
        self.word_hint = "   ".join(word_hints)
        self.start_time = datetime.now(UTC)
        self.end_time = self.start_time + timedelta(seconds=self.duration_seconds)
        self.is_active = True

    def end(self) -> None:
        """Mark the round as ended."""
        self.is_active = False
        if not self.end_time:
            self.end_time = datetime.now(UTC)

    def add_guess(self, guess: Guess) -> None:
        """Add a guess to the round.

        Args:
            guess: The guess attempt.
        """
        self.guesses.append(guess)

    def add_chat_message(self, message: ChatMessage) -> None:
        """Add a chat message to the round.

        Args:
            message: The chat message.
        """
        self.chat_messages.append(message)

    def calculate_points(self, time_elapsed: float, max_points: int = 1000) -> int:
        """Calculate points based on guess time.

        Faster guesses award more points using exponential decay.

        Args:
            time_elapsed: Seconds since round start.
            max_points: Maximum points for instant guess.

        Returns:
            Points to award (100 minimum for correct guess).
        """
        if time_elapsed <= 0:
            return max_points

        # Exponential decay: points = max_points * e^(-time/duration)
        ratio = time_elapsed / self.duration_seconds
        points = int(max_points * math.exp(-2 * ratio))
        return max(points, 100)  # Minimum 100 points

    def _get_hint_char_mapping(self) -> list[int]:
        """Get mapping from word letter indices to hint character indices.

        Returns:
            List where index i gives the hint position for word letter i.
            Only maps non-space characters in the word.
        """
        mapping = []
        hint_pos = 0
        words = self.word.split(" ")

        for word_idx, w in enumerate(words):
            for char_idx in range(len(w)):
                mapping.append(hint_pos)
                hint_pos += 2  # Each letter takes 2 positions (char + space)
            hint_pos -= 1  # Remove trailing space from word
            if word_idx < len(words) - 1:
                hint_pos += 4  # Add 3 spaces + 1 for next char position

        return mapping

    def reveal_hint(self, reveal_count: int = 1) -> str:
        """Reveal additional letters in the word hint.

        Args:
            reveal_count: Number of letters to reveal.

        Returns:
            Updated word hint.
        """
        if not self.word:
            return self.word_hint

        # Build mapping from word letter index to hint position
        # Only consider non-space characters
        letter_indices = [(i, char) for i, char in enumerate(self.word) if char != " "]
        mapping = self._get_hint_char_mapping()

        # Find unrevealed positions (only letters, not spaces)
        unrevealed = []
        for letter_idx, (word_idx, char) in enumerate(letter_indices):
            hint_pos = mapping[letter_idx]
            if hint_pos < len(self.word_hint) and self.word_hint[hint_pos] == "_":
                unrevealed.append((letter_idx, word_idx, char))

        if not unrevealed:
            return self.word_hint

        # Reveal random positions
        to_reveal = random.sample(unrevealed, min(reveal_count, len(unrevealed)))

        hint_chars = list(self.word_hint)
        for letter_idx, word_idx, char in to_reveal:
            hint_pos = mapping[letter_idx]
            hint_chars[hint_pos] = char

        self.word_hint = "".join(hint_chars)
        return self.word_hint

    def is_expired(self) -> bool:
        """Check if round time has expired.

        Returns:
            True if current time is past end_time.
        """
        if not self.end_time:
            return False
        return datetime.now(UTC) >= self.end_time

    def time_remaining(self) -> float:
        """Get remaining time in seconds.

        Returns:
            Seconds remaining, or 0 if expired.
        """
        if not self.end_time:
            return 0.0

        remaining = (self.end_time - datetime.now(UTC)).total_seconds()
        return max(remaining, 0.0)


@dataclass
class GameSettings:
    """Configurable settings for a game room.

    Attributes:
        id: Unique identifier for settings.
        is_public: Whether the room is visible in public lobby list.
        round_duration_seconds: Time limit for each round (60-120).
        rounds_per_game: Total rounds before game ends.
        max_players: Maximum number of players (2-12).
        word_bank_ids: IDs of word banks to use.
        allow_custom_words: Whether players can add custom words.
        custom_words: List of custom words added by players.
        custom_words_only: If True, only use custom words (no default word bank).
        hints_enabled: Whether to show hints during rounds.
        hint_intervals: Seconds between automatic hints.
        drawer_points_multiplier: Multiplier for drawer points.
        close_guess_threshold: Levenshtein distance for "close" guesses.
        require_exact_match: Whether to require exact spelling.
    """

    id: UUID = field(default_factory=uuid4)
    is_public: bool = False  # Private by default, require room code to join
    round_duration_seconds: int = 80
    rounds_per_game: int = 8
    max_players: int = 8
    word_bank_ids: list[UUID] = field(default_factory=list)
    allow_custom_words: bool = True
    custom_words: list[str] = field(default_factory=list)
    custom_words_only: bool = False  # If True, only use custom words (no default bank)
    hints_enabled: bool = True
    hint_intervals: list[int] = field(default_factory=lambda: [20, 40, 60])  # Seconds when to show hints
    drawer_points_multiplier: float = 0.5  # Drawer gets 50% of points awarded to guessers
    close_guess_threshold: int = 2  # Max edit distance for "close" hint
    require_exact_match: bool = False  # If false, ignore case/punctuation

    def add_custom_word(self, word: str) -> None:
        """Add a custom word to the game.

        Args:
            word: Word to add.
        """
        normalized = word.lower().strip()
        if normalized and normalized not in self.custom_words:
            self.custom_words.append(normalized)

    def remove_custom_word(self, word: str) -> None:
        """Remove a custom word from the game.

        Args:
            word: Word to remove.
        """
        normalized = word.lower().strip()
        if normalized in self.custom_words:
            self.custom_words.remove(normalized)


@dataclass
class GameRoom:
    """Game lobby/room for CanvasClash mode.

    Manages the entire game lifecycle including players, rounds, state transitions,
    and game logic.

    Attributes:
        id: Unique identifier for the room.
        room_code: Short code for joining (e.g., "ABCD1234").
        name: Display name for the room.
        game_mode: Type of game mode.
        game_state: Current state of the game.
        settings: Game configuration settings.
        host_id: ID of the player who created the room.
        players: All players in the room (active and disconnected).
        current_round: The active round (if any).
        round_history: All completed rounds.
        current_round_number: Current round index (0-indexed).
        canvas_id: ID of the active canvas.
        created_at: When the room was created.
        started_at: When the game started (left lobby).
        ended_at: When the game ended.
    """

    id: UUID = field(default_factory=uuid4)
    room_code: str = ""
    name: str = "Untitled Game"
    game_mode: GameMode = GameMode.SKRIBBL
    game_state: GameState = GameState.LOBBY
    settings: GameSettings = field(default_factory=GameSettings)
    host_id: UUID | None = None
    players: list[Player] = field(default_factory=list)
    banned_user_ids: set[str] = field(default_factory=set)  # User IDs that are banned
    current_round: Round | None = None
    round_history: list[Round] = field(default_factory=list)
    current_round_number: int = 0
    canvas_id: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    ended_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Generate room code if not provided."""
        if not self.room_code:
            # Generate 6-character alphanumeric code
            self.room_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

    def add_player(self, player: Player) -> None:
        """Add a player to the room.

        Spectators can join regardless of room capacity or game state (except GAME_OVER).
        Regular players can only join in LOBBY state when room is not full.

        Args:
            player: Player to add.

        Raises:
            ValueError: If room is full (non-spectators), banned, or cannot join in current state.
        """
        # Check if user is banned
        if player.user_id and player.user_id in self.banned_user_ids:
            raise ValueError("You have been banned from this room")

        if player.is_spectator:
            # Spectators can join anytime except game over
            if self.game_state == GameState.GAME_OVER:
                raise ValueError("Cannot spectate: game is over")
        else:
            # Regular players have restrictions
            if len(self.active_guessers()) >= self.settings.max_players:
                raise ValueError("Room is full")

            if self.game_state not in (GameState.LOBBY, GameState.DRAWING):
                raise ValueError("Cannot join: game already in progress")

        # First non-spectator player becomes host
        if not self.players and not player.is_spectator:
            player.is_host = True
            self.host_id = player.id

        self.players.append(player)

    def remove_player(self, player_id: UUID) -> None:
        """Remove a player from the room.

        Args:
            player_id: ID of player to remove.
        """
        player = self.get_player(player_id)
        if player:
            player.connection_state = PlayerState.LEFT

            # Transfer host if needed
            if player.is_host:
                active = self.active_players()
                if active:
                    active[0].is_host = True
                    self.host_id = active[0].id
                else:
                    self.host_id = None

    def get_player(self, player_id: UUID) -> Player | None:
        """Get player by ID.

        Args:
            player_id: Player ID to find.

        Returns:
            Player if found, None otherwise.
        """
        return next((p for p in self.players if p.id == player_id), None)

    def active_players(self) -> list[Player]:
        """Get all connected players (including spectators).

        Returns:
            List of players with CONNECTED state.
        """
        return [p for p in self.players if p.connection_state == PlayerState.CONNECTED]

    def active_guessers(self) -> list[Player]:
        """Get all connected non-spectator players (those who can draw/guess).

        Returns:
            List of connected players who are not spectators.
        """
        return [p for p in self.players if p.connection_state == PlayerState.CONNECTED and not p.is_spectator]

    def spectators(self) -> list[Player]:
        """Get all connected spectators.

        Returns:
            List of connected players who are spectators.
        """
        return [p for p in self.players if p.connection_state == PlayerState.CONNECTED and p.is_spectator]

    def start_game(self) -> None:
        """Start the game, transitioning from LOBBY to first round."""
        if self.game_state != GameState.LOBBY:
            raise ValueError("Game already started")

        if len(self.active_guessers()) < 2:
            raise ValueError("Need at least 2 players to start")

        self.started_at = datetime.now(UTC)
        self.game_state = GameState.WORD_SELECTION
        self.current_round_number = 0

    def next_round(self) -> Round:
        """Create and start the next turn (each player drawing once = 1 turn).

        Returns:
            The new round instance.

        Raises:
            ValueError: If game is over or not in correct state.
        """
        if self.current_round_number >= self.total_turns():
            self.game_state = GameState.GAME_OVER
            self.ended_at = datetime.now(UTC)
            raise ValueError("Game is over")

        # Get next drawer (round-robin from non-spectators only)
        guessers = self.active_guessers()
        if not guessers:
            raise ValueError("No active players")

        drawer = guessers[self.current_round_number % len(guessers)]

        # Reset player round state (only for guessers)
        for player in guessers:
            player.reset_round_state()

        # Create new round
        new_round = Round(
            round_number=self.current_round_number + 1,
            drawer_id=drawer.id,
            duration_seconds=self.settings.round_duration_seconds,
            canvas_id=self.canvas_id or uuid4(),
        )

        self.current_round = new_round
        self.game_state = GameState.WORD_SELECTION

        return new_round

    def end_round(self) -> None:
        """End the current round and update game state."""
        if not self.current_round:
            return

        self.current_round.end()
        self.round_history.append(self.current_round)
        self.game_state = GameState.ROUND_END
        self.current_round_number += 1

    def get_leaderboard(self) -> list[tuple[Player, int]]:
        """Get sorted leaderboard of players and scores (excludes spectators).

        Returns:
            List of (player, score) tuples sorted by score descending.
        """
        return sorted(
            [(p, p.score) for p in self.active_guessers()],
            key=lambda x: x[1],
            reverse=True,
        )

    def total_turns(self) -> int:
        """Calculate total turns in the game.

        Each player draws once per round, so total turns = rounds × players.

        Returns:
            Total number of turns in the game.
        """
        num_players = len(self.active_guessers())
        if num_players == 0:
            return self.settings.rounds_per_game
        return self.settings.rounds_per_game * num_players

    def current_display_round(self) -> int:
        """Get the current round number for display (1-indexed).

        A round is complete when every player has drawn once.

        Returns:
            Current round number (1 to rounds_per_game).
        """
        num_players = len(self.active_guessers())
        if num_players == 0 or self.current_round_number == 0:
            return 1
        # Use (turn - 1) // players + 1 so turn 1-4 = round 1, turn 5-8 = round 2, etc.
        return ((self.current_round_number - 1) // num_players) + 1

    def is_game_over(self) -> bool:
        """Check if all rounds are complete.

        Returns:
            True if game is finished.
        """
        return self.current_round_number >= self.total_turns()

    def is_host(self, player_id: UUID) -> bool:
        """Check if a player is the host.

        Args:
            player_id: Player ID to check.

        Returns:
            True if player is the host.
        """
        return self.host_id == player_id

    def kick_player(self, kicker_id: UUID, target_id: UUID) -> Player | None:
        """Kick a player from the room (host only).

        The kicked player can rejoin the room.

        Args:
            kicker_id: ID of the player performing the kick (must be host).
            target_id: ID of the player to kick.

        Returns:
            The kicked player, or None if not found or not authorized.

        Raises:
            ValueError: If kicker is not the host or target is the host.
        """
        if not self.is_host(kicker_id):
            raise ValueError("Only the host can kick players")

        target = self.get_player(target_id)
        if not target:
            return None

        if target.is_host:
            raise ValueError("Cannot kick the host")

        target.connection_state = PlayerState.LEFT
        return target

    def ban_player(self, banner_id: UUID, target_id: UUID) -> Player | None:
        """Ban a player from the room (host only).

        The banned player cannot rejoin the room.

        Args:
            banner_id: ID of the player performing the ban (must be host).
            target_id: ID of the player to ban.

        Returns:
            The banned player, or None if not found or not authorized.

        Raises:
            ValueError: If banner is not the host or target is the host.
        """
        if not self.is_host(banner_id):
            raise ValueError("Only the host can ban players")

        target = self.get_player(target_id)
        if not target:
            return None

        if target.is_host:
            raise ValueError("Cannot ban the host")

        # Add to banned list
        if target.user_id:
            self.banned_user_ids.add(target.user_id)

        target.connection_state = PlayerState.LEFT
        return target

    def unban_player(self, unbanner_id: UUID, user_id: str) -> bool:
        """Unban a player from the room (host only).

        Args:
            unbanner_id: ID of the player performing the unban (must be host).
            user_id: User ID to unban.

        Returns:
            True if user was unbanned, False if not found in ban list.

        Raises:
            ValueError: If unbanner is not the host.
        """
        if not self.is_host(unbanner_id):
            raise ValueError("Only the host can unban players")

        if user_id in self.banned_user_ids:
            self.banned_user_ids.remove(user_id)
            return True
        return False

    def transfer_host(self, current_host_id: UUID, new_host_id: UUID) -> bool:
        """Transfer host privileges to another player.

        Args:
            current_host_id: ID of the current host.
            new_host_id: ID of the new host.

        Returns:
            True if transfer succeeded, False otherwise.

        Raises:
            ValueError: If current_host_id is not the host.
        """
        if not self.is_host(current_host_id):
            raise ValueError("Only the host can transfer host privileges")

        current_host = self.get_player(current_host_id)
        new_host = self.get_player(new_host_id)

        if not current_host or not new_host:
            return False

        if new_host.connection_state != PlayerState.CONNECTED:
            raise ValueError("Cannot transfer host to disconnected player")

        if new_host.is_spectator:
            raise ValueError("Cannot transfer host to a spectator")

        current_host.is_host = False
        new_host.is_host = True
        self.host_id = new_host_id
        return True
