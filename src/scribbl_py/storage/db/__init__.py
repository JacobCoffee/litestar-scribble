"""Database storage backend for scribbl-py.

This module provides SQLAlchemy-based persistent storage.
Requires the `db` optional dependency: `pip install scribbl-py[db]`
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scribbl_py.storage.db.auth_models import SessionModel, UserModel, UserStatsModel
    from scribbl_py.storage.db.auth_storage import AuthDatabaseStorage
    from scribbl_py.storage.db.models import CanvasModel, ElementModel
    from scribbl_py.storage.db.setup import DatabaseManager
    from scribbl_py.storage.db.storage import DatabaseStorage

__all__ = [
    "AuthDatabaseStorage",
    "CanvasModel",
    "DatabaseManager",
    "DatabaseStorage",
    "ElementModel",
    "SessionModel",
    "UserModel",
    "UserStatsModel",
]


def __getattr__(name: str) -> object:
    """Lazy import database components to avoid import errors without db extra."""
    if name == "DatabaseStorage":
        from scribbl_py.storage.db.storage import DatabaseStorage

        return DatabaseStorage
    if name == "CanvasModel":
        from scribbl_py.storage.db.models import CanvasModel

        return CanvasModel
    if name == "ElementModel":
        from scribbl_py.storage.db.models import ElementModel

        return ElementModel
    if name == "DatabaseManager":
        from scribbl_py.storage.db.setup import DatabaseManager

        return DatabaseManager
    if name == "AuthDatabaseStorage":
        from scribbl_py.storage.db.auth_storage import AuthDatabaseStorage

        return AuthDatabaseStorage
    if name == "UserModel":
        from scribbl_py.storage.db.auth_models import UserModel

        return UserModel
    if name == "SessionModel":
        from scribbl_py.storage.db.auth_models import SessionModel

        return SessionModel
    if name == "UserStatsModel":
        from scribbl_py.storage.db.auth_models import UserStatsModel

        return UserStatsModel
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
