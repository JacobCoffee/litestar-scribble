"""OAuth configuration for scribbl-py."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class OAuthConfig:
    """Configuration for OAuth providers.

    Environment variables:
        GOOGLE_CLIENT_ID: Google OAuth client ID
        GOOGLE_CLIENT_SECRET: Google OAuth client secret
        DISCORD_CLIENT_ID: Discord OAuth client ID
        DISCORD_CLIENT_SECRET: Discord OAuth client secret
        GITHUB_CLIENT_ID: GitHub OAuth client ID
        GITHUB_CLIENT_SECRET: GitHub OAuth client secret
        SESSION_SECRET: Secret key for session signing
        BASE_URL: Base URL for OAuth callbacks (e.g., http://localhost:8000)
    """

    # Google OAuth
    google_client_id: str = field(default_factory=lambda: os.getenv("GOOGLE_CLIENT_ID", ""))
    google_client_secret: str = field(default_factory=lambda: os.getenv("GOOGLE_CLIENT_SECRET", ""))

    # Discord OAuth
    discord_client_id: str = field(default_factory=lambda: os.getenv("DISCORD_CLIENT_ID", ""))
    discord_client_secret: str = field(default_factory=lambda: os.getenv("DISCORD_CLIENT_SECRET", ""))

    # GitHub OAuth
    github_client_id: str = field(default_factory=lambda: os.getenv("GITHUB_CLIENT_ID", ""))
    github_client_secret: str = field(default_factory=lambda: os.getenv("GITHUB_CLIENT_SECRET", ""))

    # Session configuration
    session_secret: str = field(default_factory=lambda: os.getenv("SESSION_SECRET", "change-me-in-production"))
    session_cookie_name: str = "scribbl_session"
    session_max_age: int = 60 * 60 * 24 * 30  # 30 days

    # Base URL for callbacks
    base_url: str = field(default_factory=lambda: os.getenv("BASE_URL", "http://localhost:8000"))

    @property
    def google_enabled(self) -> bool:
        """Check if Google OAuth is configured."""
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def discord_enabled(self) -> bool:
        """Check if Discord OAuth is configured."""
        return bool(self.discord_client_id and self.discord_client_secret)

    @property
    def github_enabled(self) -> bool:
        """Check if GitHub OAuth is configured."""
        return bool(self.github_client_id and self.github_client_secret)

    @property
    def any_oauth_enabled(self) -> bool:
        """Check if any OAuth provider is configured."""
        return self.google_enabled or self.discord_enabled or self.github_enabled


# OAuth provider URLs
OAUTH_URLS = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scopes": ["openid", "email", "profile"],
    },
    "discord": {
        "authorize_url": "https://discord.com/api/oauth2/authorize",
        "token_url": "https://discord.com/api/oauth2/token",
        "userinfo_url": "https://discord.com/api/users/@me",
        "scopes": ["identify", "email"],
    },
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scopes": ["read:user", "user:email"],
    },
}
