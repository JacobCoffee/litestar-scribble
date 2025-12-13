"""Authentication service for OAuth and session management."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import structlog

from scribbl_py.auth.config import OAUTH_URLS, OAuthConfig
from scribbl_py.auth.models import OAuthProvider, Session, User, UserStats

logger = structlog.get_logger(__name__)


class AuthService:
    """Service for authentication and session management.

    Handles OAuth authentication flow, session creation/validation,
    and user management. Uses in-memory storage by default.
    """

    def __init__(self, config: OAuthConfig | None = None) -> None:
        """Initialize the auth service.

        Args:
            config: OAuth configuration. Uses defaults if not provided.
        """
        self._config = config or OAuthConfig()

        # In-memory storage (replace with database in production)
        self._users: dict[UUID, User] = {}
        self._users_by_oauth: dict[str, UUID] = {}  # "provider:oauth_id" -> user_id
        self._sessions: dict[str, Session] = {}
        self._stats: dict[UUID, UserStats] = {}

    # === Session Management ===

    def create_session(
        self,
        user_id: UUID | None = None,
        guest_name: str = "Anonymous",
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Session:
        """Create a new session.

        Args:
            user_id: User ID for authenticated sessions.
            guest_name: Display name for guest sessions.
            ip_address: Client IP address.
            user_agent: Client user agent.

        Returns:
            New session instance.
        """
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(seconds=self._config.session_max_age)

        session = Session(
            id=session_id,
            user_id=user_id,
            guest_name=guest_name,
            created_at=datetime.now(UTC),
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self._sessions[session_id] = session
        logger.info(
            "Session created",
            session_id=session_id[:8] + "...",
            user_id=str(user_id) if user_id else None,
            is_guest=user_id is None,
        )
        return session

    def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID.

        Args:
            session_id: The session identifier.

        Returns:
            Session if found and not expired, None otherwise.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Check expiration
        if session.expires_at and session.expires_at < datetime.now(UTC):
            del self._sessions[session_id]
            return None

        return session

    def delete_session(self, session_id: str) -> bool:
        """Delete a session (logout).

        Args:
            session_id: The session identifier.

        Returns:
            True if session was deleted, False if not found.
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("Session deleted", session_id=session_id[:8] + "...")
            return True
        return False

    def update_session_user(self, session_id: str, user: User) -> Session | None:
        """Update a session with authenticated user.

        Args:
            session_id: The session identifier.
            user: The authenticated user.

        Returns:
            Updated session or None if not found.
        """
        session = self.get_session(session_id)
        if not session:
            return None

        session.user_id = user.id
        session.guest_name = user.username
        return session

    # === User Management ===

    def get_user(self, user_id: UUID) -> User | None:
        """Get a user by ID.

        Args:
            user_id: The user identifier.

        Returns:
            User if found, None otherwise.
        """
        return self._users.get(user_id)

    def get_user_by_oauth(self, provider: OAuthProvider, oauth_id: str) -> User | None:
        """Get a user by OAuth provider and ID.

        Args:
            provider: The OAuth provider.
            oauth_id: The user's ID from the provider.

        Returns:
            User if found, None otherwise.
        """
        key = f"{provider.value}:{oauth_id}"
        user_id = self._users_by_oauth.get(key)
        if user_id:
            return self._users.get(user_id)
        return None

    def create_user(
        self,
        username: str,
        email: str | None = None,
        avatar_url: str | None = None,
        oauth_provider: OAuthProvider | None = None,
        oauth_id: str | None = None,
    ) -> User:
        """Create a new user.

        Args:
            username: Display name.
            email: Email address.
            avatar_url: Avatar URL.
            oauth_provider: OAuth provider used for registration.
            oauth_id: User's ID from the OAuth provider.

        Returns:
            New user instance.
        """
        user = User(
            id=uuid4(),
            username=username,
            email=email,
            avatar_url=avatar_url,
            oauth_provider=oauth_provider,
            oauth_id=oauth_id,
            created_at=datetime.now(UTC),
            last_login=datetime.now(UTC),
        )

        self._users[user.id] = user

        # Index by OAuth for lookup
        if oauth_provider and oauth_id:
            key = f"{oauth_provider.value}:{oauth_id}"
            self._users_by_oauth[key] = user.id

        # Initialize stats
        self._stats[user.id] = UserStats(user_id=user.id)

        logger.info(
            "User created",
            user_id=str(user.id),
            username=username,
            oauth_provider=oauth_provider.value if oauth_provider else None,
        )
        return user

    def update_user(self, user: User) -> User:
        """Update a user.

        Args:
            user: The user with updated fields.

        Returns:
            Updated user.
        """
        self._users[user.id] = user
        return user

    def get_or_create_user_from_oauth(
        self,
        provider: OAuthProvider,
        oauth_id: str,
        username: str,
        email: str | None = None,
        avatar_url: str | None = None,
    ) -> tuple[User, bool]:
        """Get existing user or create new one from OAuth data.

        Args:
            provider: OAuth provider.
            oauth_id: User's ID from the provider.
            username: Display name from provider.
            email: Email from provider.
            avatar_url: Avatar URL from provider.

        Returns:
            Tuple of (user, was_created).
        """
        existing = self.get_user_by_oauth(provider, oauth_id)
        if existing:
            # Update last login
            existing.last_login = datetime.now(UTC)
            # Optionally update avatar if changed
            if avatar_url and existing.avatar_url != avatar_url:
                existing.avatar_url = avatar_url
            return existing, False

        # Create new user
        user = self.create_user(
            username=username,
            email=email,
            avatar_url=avatar_url,
            oauth_provider=provider,
            oauth_id=oauth_id,
        )
        return user, True

    # === Stats Management ===

    def get_user_stats(self, user_id: UUID) -> UserStats | None:
        """Get stats for a user.

        Args:
            user_id: The user identifier.

        Returns:
            UserStats if found, None otherwise.
        """
        return self._stats.get(user_id)

    def update_user_stats(self, stats: UserStats) -> UserStats:
        """Update user stats.

        Args:
            stats: The stats with updated fields.

        Returns:
            Updated stats.
        """
        stats.updated_at = datetime.now(UTC)
        self._stats[stats.user_id] = stats
        return stats

    def record_game_result(
        self,
        user_id: UUID,
        score: int,
        won: bool,
        correct_guesses: int,
        total_guesses: int,
        total_guess_time_ms: int,
        fastest_guess_ms: int | None,
        drawings_completed: int,
        drawings_guessed: int,
    ) -> UserStats | None:
        """Record a game result for a user.

        Args:
            user_id: The user identifier.
            score: Points earned in the game.
            won: Whether the user won (highest score).
            correct_guesses: Number of correct guesses.
            total_guesses: Total guesses made.
            total_guess_time_ms: Total time spent on correct guesses.
            fastest_guess_ms: Fastest correct guess time.
            drawings_completed: Number of drawings completed.
            drawings_guessed: Number of user's drawings that were guessed.

        Returns:
            Updated stats or None if user not found.
        """
        stats = self.get_user_stats(user_id)
        if not stats:
            return None

        stats.games_played += 1
        stats.total_score += score
        stats.correct_guesses += correct_guesses
        stats.total_guesses += total_guesses
        stats.total_guess_time_ms += total_guess_time_ms
        stats.drawings_completed += drawings_completed
        stats.drawings_guessed += drawings_guessed

        if won:
            stats.games_won += 1
            stats.current_win_streak += 1
            stats.best_win_streak = max(stats.best_win_streak, stats.current_win_streak)
        else:
            stats.current_win_streak = 0

        stats.best_game_score = max(stats.best_game_score, score)

        if fastest_guess_ms is not None and (
            stats.fastest_guess_ms is None or fastest_guess_ms < stats.fastest_guess_ms
        ):
            stats.fastest_guess_ms = fastest_guess_ms

        return self.update_user_stats(stats)

    # === Leaderboards ===

    def get_leaderboard(
        self,
        category: str = "wins",
        limit: int = 10,
    ) -> list[tuple[User, UserStats]]:
        """Get leaderboard for a category.

        Args:
            category: Leaderboard category (wins, fastest, drawer, games).
            limit: Maximum number of entries.

        Returns:
            List of (user, stats) tuples sorted by the category.
        """
        entries: list[tuple[User, UserStats]] = []

        for user_id, stats in self._stats.items():
            user = self._users.get(user_id)
            if user and stats.games_played > 0:  # Only include users who have played
                entries.append((user, stats))

        # Sort by category
        if category == "wins":
            entries.sort(key=lambda x: x[1].games_won, reverse=True)
        elif category == "fastest":
            # Filter to users with at least one correct guess
            entries = [e for e in entries if e[1].fastest_guess_ms is not None]
            entries.sort(key=lambda x: x[1].fastest_guess_ms or float("inf"))
        elif category == "drawer":
            entries.sort(key=lambda x: x[1].drawing_success_rate, reverse=True)
        elif category == "games":
            entries.sort(key=lambda x: x[1].games_played, reverse=True)
        else:
            entries.sort(key=lambda x: x[1].total_score, reverse=True)

        return entries[:limit]

    # === OAuth Helpers ===

    def get_oauth_authorize_url(self, provider: str, state: str) -> str | None:
        """Get the OAuth authorization URL for a provider.

        Args:
            provider: Provider name (google, discord, github).
            state: State parameter for CSRF protection.

        Returns:
            Authorization URL or None if provider not configured.
        """
        if provider == "google" and not self._config.google_enabled:
            return None
        if provider == "discord" and not self._config.discord_enabled:
            return None
        if provider == "github" and not self._config.github_enabled:
            return None

        urls = OAUTH_URLS.get(provider)
        if not urls:
            return None

        client_id = getattr(self._config, f"{provider}_client_id")
        redirect_uri = f"{self._config.base_url}/auth/{provider}/callback"
        scopes = " ".join(urls["scopes"])

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scopes,
            "state": state,
        }

        # Provider-specific params
        if provider == "google":
            params["access_type"] = "offline"
            params["prompt"] = "select_account"
        elif provider == "discord":
            params["prompt"] = "consent"

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{urls['authorize_url']}?{query}"

    async def exchange_oauth_code(
        self,
        provider: str,
        code: str,
    ) -> dict[str, Any] | None:
        """Exchange OAuth code for user info.

        Args:
            provider: Provider name.
            code: Authorization code from callback.

        Returns:
            User info dict or None on failure.
        """
        try:
            import httpx
        except ImportError:
            logger.error("httpx not installed - run: uv add httpx")
            return None

        urls = OAUTH_URLS.get(provider)
        if not urls:
            return None

        client_id = getattr(self._config, f"{provider}_client_id")
        client_secret = getattr(self._config, f"{provider}_client_secret")
        redirect_uri = f"{self._config.base_url}/auth/{provider}/callback"

        # Exchange code for token
        async with httpx.AsyncClient() as client:
            token_data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }

            headers = {"Accept": "application/json"}
            resp = await client.post(urls["token_url"], data=token_data, headers=headers)

            if resp.status_code != 200:
                logger.error("Token exchange failed", provider=provider, status=resp.status_code)
                return None

            token_resp = resp.json()
            access_token = token_resp.get("access_token")

            if not access_token:
                logger.error("No access token in response", provider=provider)
                return None

            # Fetch user info
            headers = {"Authorization": f"Bearer {access_token}"}
            resp = await client.get(urls["userinfo_url"], headers=headers)

            if resp.status_code != 200:
                logger.error("User info fetch failed", provider=provider, status=resp.status_code)
                return None

            user_info = resp.json()

            # Normalize user info across providers
            return self._normalize_user_info(provider, user_info)

    def _normalize_user_info(self, provider: str, info: dict[str, Any]) -> dict[str, Any]:
        """Normalize user info from different providers.

        Args:
            provider: Provider name.
            info: Raw user info from provider.

        Returns:
            Normalized user info dict.
        """
        if provider == "google":
            return {
                "id": info.get("sub"),
                "username": info.get("name", info.get("email", "").split("@")[0]),
                "email": info.get("email"),
                "avatar_url": info.get("picture"),
            }
        elif provider == "discord":
            avatar_hash = info.get("avatar")
            user_id = info.get("id")
            avatar_url = None
            if avatar_hash and user_id:
                avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png"
            return {
                "id": user_id,
                "username": info.get("global_name") or info.get("username"),
                "email": info.get("email"),
                "avatar_url": avatar_url,
            }
        elif provider == "github":
            return {
                "id": str(info.get("id")),
                "username": info.get("login"),
                "email": info.get("email"),
                "avatar_url": info.get("avatar_url"),
            }
        return info
