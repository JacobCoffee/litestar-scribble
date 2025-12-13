"""Authentication controller for OAuth routes."""

from __future__ import annotations

import secrets
from typing import Any, ClassVar

import structlog
from litestar import Controller, get
from litestar.connection import Request  # noqa: TC002
from litestar.response import Redirect, Template

from scribbl_py.auth.models import OAuthProvider
from scribbl_py.auth.service import AuthService  # noqa: TC001

logger = structlog.get_logger(__name__)


class AuthController(Controller):
    """Controller for authentication routes.

    Handles OAuth login/callback flows and session management.
    """

    path = "/auth"
    tags: ClassVar[list[str]] = ["Authentication"]

    @get("/login")
    async def login_page(self, request: Request, auth_service: AuthService) -> Template:
        """Render login page with available OAuth providers.

        Args:
            request: The request object.
            auth_service: Auth service instance.

        Returns:
            Rendered login template.
        """
        # Check if already logged in
        session_id = request.cookies.get(auth_service._config.session_cookie_name)
        if session_id:
            session = auth_service.get_session(session_id)
            if session and session.is_authenticated:
                return Redirect(path="/canvas-clash/")

        providers = []
        if auth_service._config.google_enabled:
            providers.append({"name": "google", "label": "Google", "icon": "google"})
        if auth_service._config.discord_enabled:
            providers.append({"name": "discord", "label": "Discord", "icon": "discord"})
        if auth_service._config.github_enabled:
            providers.append({"name": "github", "label": "GitHub", "icon": "github"})

        return Template(
            template_name="auth/login.html",
            context={
                "providers": providers,
                "guest_enabled": True,
            },
        )

    @get("/login/{provider:str}")
    async def oauth_login(
        self,
        provider: str,
        request: Request,
        auth_service: AuthService,
    ) -> Redirect:
        """Initiate OAuth login flow.

        Args:
            provider: OAuth provider name.
            request: The request object.
            auth_service: Auth service instance.

        Returns:
            Redirect to OAuth provider.
        """
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Store state in session cookie (temporary)
        request.set_session({"oauth_state": state})

        # Get authorization URL
        auth_url = auth_service.get_oauth_authorize_url(provider, state)
        if not auth_url:
            logger.warning("OAuth provider not configured", provider=provider)
            return Redirect(path="/auth/login?error=provider_not_configured")

        logger.info("Starting OAuth flow", provider=provider)
        return Redirect(path=auth_url)

    @get("/{provider:str}/callback")
    async def oauth_callback(
        self,
        provider: str,
        request: Request,
        auth_service: AuthService,
        code: str | None = None,
        error: str | None = None,
    ) -> Redirect:
        """Handle OAuth callback.

        Args:
            provider: OAuth provider name.
            request: The request object.
            auth_service: Auth service instance.
            code: Authorization code from provider.
            error: Error message if OAuth failed.

        Returns:
            Redirect to app or login page.
        """
        # Check for OAuth errors
        if error:
            logger.warning("OAuth error", provider=provider, error=error)
            return Redirect(path=f"/auth/login?error={error}")

        if not code:
            return Redirect(path="/auth/login?error=no_code")

        # Verify state (CSRF protection) - get from query string
        oauth_state = request.query_params.get("state")
        session_state = request.session.get("oauth_state")
        if not session_state or session_state != oauth_state:
            logger.warning("OAuth state mismatch", provider=provider)
            return Redirect(path="/auth/login?error=invalid_state")

        # Exchange code for user info
        user_info = await auth_service.exchange_oauth_code(provider, code)
        if not user_info:
            return Redirect(path="/auth/login?error=exchange_failed")

        # Get or create user
        oauth_provider = OAuthProvider(provider)
        user, created = auth_service.get_or_create_user_from_oauth(
            provider=oauth_provider,
            oauth_id=user_info["id"],
            username=user_info["username"],
            email=user_info.get("email"),
            avatar_url=user_info.get("avatar_url"),
        )

        logger.info(
            "OAuth login successful",
            provider=provider,
            user_id=str(user.id),
            username=user.username,
            created=created,
        )

        # Create or update session
        session_id = request.cookies.get(auth_service._config.session_cookie_name)
        if session_id:
            session = auth_service.get_session(session_id)
            if session:
                auth_service.update_session_user(session_id, user)
            else:
                session = auth_service.create_session(user_id=user.id)
        else:
            session = auth_service.create_session(
                user_id=user.id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )

        # Clear OAuth state from session
        request.clear_session()

        # Redirect with session cookie
        response = Redirect(path="/canvas-clash/")
        response.set_cookie(
            key=auth_service._config.session_cookie_name,
            value=session.id,
            max_age=auth_service._config.session_max_age,
            httponly=True,
            samesite="lax",
            secure=request.url.scheme == "https",
        )
        return response

    @get("/logout")
    async def logout(self, request: Request, auth_service: AuthService) -> Redirect:
        """Log out the current user.

        Args:
            request: The request object.
            auth_service: Auth service instance.

        Returns:
            Redirect to home page.
        """
        session_id = request.cookies.get(auth_service._config.session_cookie_name)
        if session_id:
            auth_service.delete_session(session_id)

        response = Redirect(path="/")
        response.delete_cookie(auth_service._config.session_cookie_name)
        return response

    @get("/guest")
    async def guest_login(self, request: Request, auth_service: AuthService) -> Redirect:
        """Create a guest session.

        Args:
            request: The request object.
            auth_service: Auth service instance.

        Returns:
            Redirect to game lobby.
        """
        session = auth_service.create_session(
            guest_name="Guest",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        response = Redirect(path="/canvas-clash/")
        response.set_cookie(
            key=auth_service._config.session_cookie_name,
            value=session.id,
            max_age=auth_service._config.session_max_age,
            httponly=True,
            samesite="lax",
            secure=request.url.scheme == "https",
        )
        return response

    @get("/me")
    async def get_current_user(
        self,
        request: Request,
        auth_service: AuthService,
    ) -> dict[str, Any]:
        """Get current user info.

        Args:
            request: The request object.
            auth_service: Auth service instance.

        Returns:
            User info or guest info.
        """
        session_id = request.cookies.get(auth_service._config.session_cookie_name)
        if not session_id:
            return {"authenticated": False, "guest": True}

        session = auth_service.get_session(session_id)
        if not session:
            return {"authenticated": False, "guest": True}

        if session.user_id:
            user = auth_service.get_user(session.user_id)
            if user:
                stats = auth_service.get_user_stats(user.id)
                return {
                    "authenticated": True,
                    "guest": False,
                    "user": {
                        "id": str(user.id),
                        "username": user.username,
                        "email": user.email,
                        "avatar_url": user.avatar_url,
                        "created_at": user.created_at.isoformat(),
                    },
                    "stats": {
                        "games_played": stats.games_played if stats else 0,
                        "games_won": stats.games_won if stats else 0,
                        "win_rate": stats.win_rate if stats else 0,
                        "best_game_score": stats.best_game_score if stats else 0,
                    }
                    if stats
                    else None,
                }

        return {
            "authenticated": False,
            "guest": True,
            "guest_name": session.guest_name,
        }

    @get("/profile")
    async def profile_page(
        self,
        request: Request,
        auth_service: AuthService,
    ) -> Template | Redirect:
        """Render user profile page.

        Args:
            request: The request object.
            auth_service: Auth service instance.

        Returns:
            Profile template or redirect to login.
        """
        session_id = request.cookies.get(auth_service._config.session_cookie_name)
        if not session_id:
            return Redirect(path="/auth/login")

        session = auth_service.get_session(session_id)
        if not session or not session.user_id:
            return Redirect(path="/auth/login")

        user = auth_service.get_user(session.user_id)
        if not user:
            return Redirect(path="/auth/login")

        stats = auth_service.get_user_stats(user.id)

        return Template(
            template_name="auth/profile.html",
            context={
                "user": user,
                "stats": stats,
            },
        )

    @get("/navbar")
    async def navbar_auth_status(
        self,
        request: Request,
        auth_service: AuthService,
    ) -> Template:
        """Return navbar auth status partial.

        Args:
            request: The request object.
            auth_service: Auth service instance.

        Returns:
            Navbar partial template.
        """
        session_id = request.cookies.get(auth_service._config.session_cookie_name)
        user = None
        guest_name = None

        if session_id:
            session = auth_service.get_session(session_id)
            if session:
                if session.user_id:
                    user = auth_service.get_user(session.user_id)
                elif session.guest_name:
                    guest_name = session.guest_name

        return Template(
            template_name="auth/navbar.html",
            context={
                "user": user,
                "guest_name": guest_name,
            },
        )

    @get("/leaderboard")
    async def leaderboard_page(
        self,
        auth_service: AuthService,
        category: str = "wins",
    ) -> Template:
        """Render leaderboard page.

        Args:
            auth_service: Auth service instance.
            category: Leaderboard category (wins, fastest, drawer, games).

        Returns:
            Leaderboard template.
        """
        # Validate category
        valid_categories = ["wins", "fastest", "drawer", "games"]
        if category not in valid_categories:
            category = "wins"

        entries = auth_service.get_leaderboard(category=category, limit=10)

        return Template(
            template_name="auth/leaderboard.html",
            context={
                "entries": entries,
                "category": category,
            },
        )
