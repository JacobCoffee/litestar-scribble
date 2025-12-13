"""Authentication and authorization for scribbl-py."""

from __future__ import annotations

from scribbl_py.auth.config import OAuthConfig
from scribbl_py.auth.controller import AuthController
from scribbl_py.auth.models import OAuthProvider, Session, User, UserStats
from scribbl_py.auth.service import AuthService

__all__ = [
    "AuthController",
    "AuthService",
    "OAuthConfig",
    "OAuthProvider",
    "Session",
    "User",
    "UserStats",
]
