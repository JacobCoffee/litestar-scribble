"""User and authentication models for scribbl-py."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4


class OAuthProvider(str, Enum):
    """Supported OAuth providers."""

    GOOGLE = "google"
    DISCORD = "discord"
    GITHUB = "github"


@dataclass
class User:
    """User account model.

    Represents a registered user with OAuth authentication.
    Users can have multiple OAuth connections (e.g., Google + Discord).

    Attributes:
        id: Unique user identifier.
        username: Display name (can be changed).
        email: Primary email address.
        avatar_url: URL to user's avatar image.
        oauth_provider: Primary OAuth provider used.
        oauth_id: ID from the OAuth provider.
        is_active: Whether the account is active.
        is_admin: Whether the user has admin privileges.
        created_at: Account creation timestamp.
        last_login: Last login timestamp.
    """

    id: UUID = field(default_factory=uuid4)
    username: str = "Anonymous"
    email: str | None = None
    avatar_url: str | None = None
    oauth_provider: OAuthProvider | None = None
    oauth_id: str | None = None
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_login: datetime | None = None

    @property
    def is_guest(self) -> bool:
        """Check if user is a guest (not authenticated)."""
        return self.oauth_provider is None


@dataclass
class UserStats:
    """User gameplay statistics.

    Tracks all-time stats for leaderboards and profiles.

    Attributes:
        user_id: Reference to the user.
        games_played: Total number of games completed.
        games_won: Total wins (highest score in a game).
        total_score: Cumulative score across all games.
        correct_guesses: Total correct guesses made.
        total_guesses: Total guesses made (for accuracy calc).
        total_guess_time_ms: Total time spent guessing (for avg calc).
        fastest_guess_ms: Fastest single correct guess.
        drawings_completed: Total drawings completed as drawer.
        drawings_guessed: How many of user's drawings were guessed correctly.
        best_game_score: Highest score in a single game.
        current_win_streak: Current consecutive wins.
        best_win_streak: Highest win streak achieved.
        updated_at: Last stats update timestamp.
    """

    user_id: UUID
    games_played: int = 0
    games_won: int = 0
    total_score: int = 0
    correct_guesses: int = 0
    total_guesses: int = 0
    total_guess_time_ms: int = 0
    fastest_guess_ms: int | None = None
    drawings_completed: int = 0
    drawings_guessed: int = 0
    best_game_score: int = 0
    current_win_streak: int = 0
    best_win_streak: int = 0
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def guess_accuracy(self) -> float:
        """Calculate guess accuracy percentage."""
        if self.total_guesses == 0:
            return 0.0
        return (self.correct_guesses / self.total_guesses) * 100

    @property
    def avg_guess_time_ms(self) -> float:
        """Calculate average time to correct guess in milliseconds."""
        if self.correct_guesses == 0:
            return 0.0
        return self.total_guess_time_ms / self.correct_guesses

    @property
    def drawing_success_rate(self) -> float:
        """Calculate percentage of drawings that were guessed correctly."""
        if self.drawings_completed == 0:
            return 0.0
        return (self.drawings_guessed / self.drawings_completed) * 100

    @property
    def avg_score_per_game(self) -> float:
        """Calculate average score per game."""
        if self.games_played == 0:
            return 0.0
        return self.total_score / self.games_played

    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage."""
        if self.games_played == 0:
            return 0.0
        return (self.games_won / self.games_played) * 100


@dataclass
class Session:
    """User session model.

    Represents an active user session (logged in or guest).

    Attributes:
        id: Session identifier (stored in cookie).
        user_id: Associated user ID (None for guests).
        guest_name: Display name for guest users.
        created_at: Session creation timestamp.
        expires_at: Session expiration timestamp.
        ip_address: Client IP address.
        user_agent: Client user agent string.
    """

    id: str
    user_id: UUID | None = None
    guest_name: str = "Anonymous"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    ip_address: str | None = None
    user_agent: str | None = None

    @property
    def is_authenticated(self) -> bool:
        """Check if session has an authenticated user."""
        return self.user_id is not None

    @property
    def display_name(self) -> str:
        """Get display name for this session."""
        return self.guest_name  # Will be replaced with user.username if authenticated

    @property
    def is_expired(self) -> bool:
        """Check if session has expired."""
        if self.expires_at is None:
            return False
        return self.expires_at < datetime.now(UTC)
