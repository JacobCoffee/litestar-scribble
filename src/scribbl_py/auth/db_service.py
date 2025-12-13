"""Database-backed authentication service."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import structlog

from scribbl_py.auth.config import OAUTH_URLS, OAuthConfig
from scribbl_py.auth.models import OAuthProvider, Session, User, UserStats

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from scribbl_py.storage.db.auth_storage import AuthDatabaseStorage

logger = structlog.get_logger(__name__)


class DatabaseAuthService:
    """Database-backed authentication service.

    Persists users, sessions, and stats to the database so they
    survive server restarts.
    """

    def __init__(
        self,
        config: OAuthConfig | None = None,
        session_factory: Any = None,
    ) -> None:
        """Initialize the auth service.

        Args:
            config: OAuth configuration.
            session_factory: SQLAlchemy async session factory.
        """
        self._config = config or OAuthConfig()
        self._session_factory = session_factory

    def _get_storage(self, db_session: AsyncSession) -> AuthDatabaseStorage:
        """Get storage instance for database operations."""
        from scribbl_py.storage.db.auth_storage import AuthDatabaseStorage  # noqa: PLC0415

        return AuthDatabaseStorage(db_session)

    # === Session Management ===

    async def create_session(
        self,
        user_id: UUID | None = None,
        guest_name: str = "Anonymous",
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Session:
        """Create a new session."""
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

        if self._session_factory:
            async with self._session_factory() as db_session:
                storage = self._get_storage(db_session)
                await storage.create_session(session)
                await db_session.commit()

        logger.info(
            "Session created",
            session_id=session_id[:8] + "...",
            user_id=str(user_id) if user_id else None,
            is_guest=user_id is None,
        )
        return session

    async def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID."""
        if not self._session_factory:
            return None

        async with self._session_factory() as db_session:
            storage = self._get_storage(db_session)
            session = await storage.get_session(session_id)

            if not session:
                return None

            # Check expiration
            if session.expires_at and session.expires_at < datetime.now(UTC):
                await storage.delete_session(session_id)
                await db_session.commit()
                return None

            return session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session (logout)."""
        if not self._session_factory:
            return False

        async with self._session_factory() as db_session:
            storage = self._get_storage(db_session)
            result = await storage.delete_session(session_id)
            await db_session.commit()
            logger.info("Session deleted", session_id=session_id[:8] + "...")
            return result

    async def update_session_user(self, session_id: str, user: User) -> Session | None:
        """Update a session with authenticated user."""
        session = await self.get_session(session_id)
        if not session:
            return None

        session.user_id = user.id
        session.guest_name = user.username

        # Update in database
        if self._session_factory:
            async with self._session_factory() as db_session:
                storage = self._get_storage(db_session)
                # Delete old and create new with updated data
                await storage.delete_session(session_id)
                await storage.create_session(session)
                await db_session.commit()

        return session

    # === User Management ===

    async def get_user(self, user_id: UUID) -> User | None:
        """Get a user by ID."""
        if not self._session_factory:
            return None

        async with self._session_factory() as db_session:
            storage = self._get_storage(db_session)
            return await storage.get_user(user_id)

    async def get_user_by_oauth(self, provider: OAuthProvider, oauth_id: str) -> User | None:
        """Get a user by OAuth provider and ID."""
        if not self._session_factory:
            return None

        async with self._session_factory() as db_session:
            storage = self._get_storage(db_session)
            return await storage.get_user_by_oauth(provider.value, oauth_id)

    async def create_user(
        self,
        username: str,
        email: str | None = None,
        avatar_url: str | None = None,
        oauth_provider: OAuthProvider | None = None,
        oauth_id: str | None = None,
    ) -> User:
        """Create a new user."""
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

        if self._session_factory:
            async with self._session_factory() as db_session:
                storage = self._get_storage(db_session)
                user = await storage.create_user(user)
                # Initialize stats
                stats = UserStats(user_id=user.id)
                await storage.create_stats(stats)
                await db_session.commit()

        logger.info(
            "User created",
            user_id=str(user.id),
            username=username,
            oauth_provider=oauth_provider.value if oauth_provider else None,
        )
        return user

    async def update_user(self, user: User) -> User:
        """Update a user."""
        if self._session_factory:
            async with self._session_factory() as db_session:
                storage = self._get_storage(db_session)
                user = await storage.update_user(user)
                await db_session.commit()
        return user

    async def get_or_create_user_from_oauth(
        self,
        provider: OAuthProvider,
        oauth_id: str,
        username: str,
        email: str | None = None,
        avatar_url: str | None = None,
    ) -> tuple[User, bool]:
        """Get existing user or create new one from OAuth data."""
        existing = await self.get_user_by_oauth(provider, oauth_id)
        if existing:
            # Update last login
            existing.last_login = datetime.now(UTC)
            # Optionally update avatar if changed
            if avatar_url and existing.avatar_url != avatar_url:
                existing.avatar_url = avatar_url
            await self.update_user(existing)
            return existing, False

        # Create new user
        user = await self.create_user(
            username=username,
            email=email,
            avatar_url=avatar_url,
            oauth_provider=provider,
            oauth_id=oauth_id,
        )
        return user, True

    # === Stats Management ===

    async def get_user_stats(self, user_id: UUID) -> UserStats | None:
        """Get stats for a user."""
        if not self._session_factory:
            return None

        async with self._session_factory() as db_session:
            storage = self._get_storage(db_session)
            return await storage.get_stats(user_id)

    async def update_user_stats(self, stats: UserStats) -> UserStats:
        """Update user stats."""
        stats.updated_at = datetime.now(UTC)
        if self._session_factory:
            async with self._session_factory() as db_session:
                storage = self._get_storage(db_session)
                stats = await storage.update_stats(stats)
                await db_session.commit()
        return stats

    async def record_game_result(
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
        """Record a game result for a user."""
        stats = await self.get_user_stats(user_id)
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

        return await self.update_user_stats(stats)

    # === Leaderboards ===

    async def get_leaderboard(
        self,
        category: str = "wins",
        limit: int = 10,
    ) -> list[tuple[User, UserStats]]:
        """Get leaderboard for a category."""
        if not self._session_factory:
            return []

        async with self._session_factory() as db_session:
            storage = self._get_storage(db_session)
            return await storage.get_leaderboard(category, limit)

    # === OAuth Helpers (same as sync version) ===

    def get_oauth_authorize_url(self, provider: str, state: str) -> str | None:
        """Get the OAuth authorization URL for a provider."""
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
        """Exchange OAuth code for user info."""
        try:
            import httpx  # noqa: PLC0415
        except ImportError:
            logger.error("httpx not installed - run: uv add httpx")
            return None

        urls = OAUTH_URLS.get(provider)
        if not urls:
            return None

        client_id = getattr(self._config, f"{provider}_client_id")
        client_secret = getattr(self._config, f"{provider}_client_secret")
        redirect_uri = f"{self._config.base_url}/auth/{provider}/callback"

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

            headers = {"Authorization": f"Bearer {access_token}"}
            resp = await client.get(urls["userinfo_url"], headers=headers)

            if resp.status_code != 200:
                logger.error("User info fetch failed", provider=provider, status=resp.status_code)
                return None

            user_info = resp.json()
            return self._normalize_user_info(provider, user_info)

    def _normalize_user_info(self, provider: str, info: dict[str, Any]) -> dict[str, Any]:
        """Normalize user info from different providers."""
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
