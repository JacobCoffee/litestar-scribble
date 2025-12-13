"""Tests for authentication service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from scribbl_py.auth.models import OAuthProvider, Session, UserStats
from scribbl_py.auth.service import AuthService


class TestAuthServiceSession:
    """Tests for session management."""

    def test_create_session_guest(self) -> None:
        """Test creating a guest session."""
        service = AuthService()
        session = service.create_session(guest_name="TestGuest")

        assert session.id
        assert session.user_id is None
        assert session.guest_name == "TestGuest"
        assert session.expires_at > datetime.now(UTC)

    def test_create_session_authenticated(self) -> None:
        """Test creating an authenticated session."""
        service = AuthService()
        user_id = uuid4()
        session = service.create_session(user_id=user_id)

        assert session.id
        assert session.user_id == user_id

    def test_get_session(self) -> None:
        """Test retrieving a session."""
        service = AuthService()
        session = service.create_session(guest_name="Test")

        retrieved = service.get_session(session.id)
        assert retrieved is not None
        assert retrieved.id == session.id

    def test_get_session_not_found(self) -> None:
        """Test retrieving non-existent session."""
        service = AuthService()
        result = service.get_session("invalid-session-id")
        assert result is None

    def test_delete_session(self) -> None:
        """Test deleting a session."""
        service = AuthService()
        session = service.create_session(guest_name="Test")

        assert service.delete_session(session.id) is True
        assert service.get_session(session.id) is None

    def test_delete_session_not_found(self) -> None:
        """Test deleting non-existent session."""
        service = AuthService()
        assert service.delete_session("invalid-session-id") is False


class TestAuthServiceUser:
    """Tests for user management."""

    def test_create_user(self) -> None:
        """Test creating a user."""
        service = AuthService()
        user = service.create_user(
            username="testuser",
            email="test@example.com",
            oauth_provider=OAuthProvider.GITHUB,
            oauth_id="12345",
        )

        assert user.id
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.oauth_provider == OAuthProvider.GITHUB

    def test_get_user(self) -> None:
        """Test retrieving a user."""
        service = AuthService()
        user = service.create_user(username="testuser")

        retrieved = service.get_user(user.id)
        assert retrieved is not None
        assert retrieved.id == user.id

    def test_get_user_by_oauth(self) -> None:
        """Test retrieving user by OAuth."""
        service = AuthService()
        user = service.create_user(
            username="testuser",
            oauth_provider=OAuthProvider.GOOGLE,
            oauth_id="google123",
        )

        retrieved = service.get_user_by_oauth(OAuthProvider.GOOGLE, "google123")
        assert retrieved is not None
        assert retrieved.id == user.id

    def test_get_or_create_user_creates(self) -> None:
        """Test get_or_create creates new user."""
        service = AuthService()
        user, created = service.get_or_create_user_from_oauth(
            provider=OAuthProvider.DISCORD,
            oauth_id="discord456",
            username="newuser",
            email="new@example.com",
        )

        assert created is True
        assert user.username == "newuser"
        assert user.oauth_provider == OAuthProvider.DISCORD

    def test_get_or_create_user_retrieves(self) -> None:
        """Test get_or_create retrieves existing user."""
        service = AuthService()
        original = service.create_user(
            username="existinguser",
            oauth_provider=OAuthProvider.GITHUB,
            oauth_id="github789",
        )

        user, created = service.get_or_create_user_from_oauth(
            provider=OAuthProvider.GITHUB,
            oauth_id="github789",
            username="differentname",
        )

        assert created is False
        assert user.id == original.id


class TestAuthServiceStats:
    """Tests for user statistics."""

    def test_user_stats_created_on_user_create(self) -> None:
        """Test that stats are initialized when user is created."""
        service = AuthService()
        user = service.create_user(username="testuser")

        stats = service.get_user_stats(user.id)
        assert stats is not None
        assert stats.games_played == 0
        assert stats.games_won == 0

    def test_record_game_result_win(self) -> None:
        """Test recording a winning game."""
        service = AuthService()
        user = service.create_user(username="winner")

        stats = service.record_game_result(
            user_id=user.id,
            score=1500,
            won=True,
            correct_guesses=5,
            total_guesses=7,
            total_guess_time_ms=15000,
            fastest_guess_ms=2000,
            drawings_completed=2,
            drawings_guessed=3,
        )

        assert stats is not None
        assert stats.games_played == 1
        assert stats.games_won == 1
        assert stats.total_score == 1500
        assert stats.correct_guesses == 5
        assert stats.current_win_streak == 1
        assert stats.fastest_guess_ms == 2000

    def test_record_game_result_loss(self) -> None:
        """Test recording a losing game."""
        service = AuthService()
        user = service.create_user(username="loser")

        # First win to start streak
        service.record_game_result(
            user_id=user.id,
            score=1000,
            won=True,
            correct_guesses=3,
            total_guesses=5,
            total_guess_time_ms=10000,
            fastest_guess_ms=3000,
            drawings_completed=1,
            drawings_guessed=2,
        )

        # Then loss to break streak
        stats = service.record_game_result(
            user_id=user.id,
            score=500,
            won=False,
            correct_guesses=2,
            total_guesses=5,
            total_guess_time_ms=8000,
            fastest_guess_ms=4000,
            drawings_completed=1,
            drawings_guessed=1,
        )

        assert stats is not None
        assert stats.games_played == 2
        assert stats.games_won == 1
        assert stats.current_win_streak == 0


class TestAuthServiceLeaderboard:
    """Tests for leaderboards."""

    def test_leaderboard_empty(self) -> None:
        """Test leaderboard with no users."""
        service = AuthService()
        leaderboard = service.get_leaderboard("wins")
        assert leaderboard == []

    def test_leaderboard_wins(self) -> None:
        """Test leaderboard sorted by wins."""
        service = AuthService()

        # Create users with different win counts
        user1 = service.create_user(username="user1")
        user2 = service.create_user(username="user2")

        # user1: 1 game, 0 wins
        service.record_game_result(
            user_id=user1.id,
            score=500,
            won=False,
            correct_guesses=2,
            total_guesses=3,
            total_guess_time_ms=5000,
            fastest_guess_ms=2000,
            drawings_completed=1,
            drawings_guessed=1,
        )

        # user2: 1 game, 1 win
        service.record_game_result(
            user_id=user2.id,
            score=1000,
            won=True,
            correct_guesses=5,
            total_guesses=5,
            total_guess_time_ms=10000,
            fastest_guess_ms=1500,
            drawings_completed=2,
            drawings_guessed=2,
        )

        leaderboard = service.get_leaderboard("wins", limit=10)
        assert len(leaderboard) == 2
        assert leaderboard[0][0].username == "user2"
        assert leaderboard[1][0].username == "user1"


class TestUserStatsProperties:
    """Tests for UserStats computed properties."""

    def test_win_rate(self) -> None:
        """Test win rate calculation."""
        stats = UserStats(user_id=uuid4(), games_played=10, games_won=7)
        assert stats.win_rate == 70.0

    def test_win_rate_no_games(self) -> None:
        """Test win rate with no games."""
        stats = UserStats(user_id=uuid4(), games_played=0, games_won=0)
        assert stats.win_rate == 0.0

    def test_guess_accuracy(self) -> None:
        """Test guess accuracy calculation."""
        stats = UserStats(user_id=uuid4(), correct_guesses=15, total_guesses=20)
        assert stats.guess_accuracy == 75.0

    def test_avg_guess_time_ms(self) -> None:
        """Test average guess time calculation."""
        stats = UserStats(
            user_id=uuid4(),
            correct_guesses=5,
            total_guess_time_ms=10000,
        )
        assert stats.avg_guess_time_ms == 2000.0


class TestSessionProperties:
    """Tests for Session computed properties."""

    def test_is_authenticated_with_user(self) -> None:
        """Test session is authenticated with user_id."""
        session = Session(
            id="test",
            user_id=uuid4(),
            created_at=datetime.now(UTC),
        )
        assert session.is_authenticated is True

    def test_is_authenticated_guest(self) -> None:
        """Test session is not authenticated without user_id."""
        session = Session(
            id="test",
            user_id=None,
            created_at=datetime.now(UTC),
        )
        assert session.is_authenticated is False

    def test_is_expired(self) -> None:
        """Test session expiration check."""
        # Not expired
        session = Session(
            id="test",
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        assert session.is_expired is False

        # Expired
        session_expired = Session(
            id="test2",
            created_at=datetime.now(UTC) - timedelta(hours=2),
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        assert session_expired.is_expired is True
