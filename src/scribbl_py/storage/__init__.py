"""Storage backends for scribbl-py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from scribbl_py.storage.base import StorageProtocol
from scribbl_py.storage.memory import InMemoryStorage

if TYPE_CHECKING:
    from scribbl_py.storage.db import DatabaseStorage

__all__ = ["DatabaseStorage", "InMemoryStorage", "StorageProtocol"]


def __getattr__(name: str) -> object:
    """Lazy import DatabaseStorage to avoid import errors without db extra."""
    if name == "DatabaseStorage":
        from scribbl_py.storage.db import DatabaseStorage

        return DatabaseStorage
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
