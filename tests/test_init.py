"""Basic tests for scribbl-py package."""

from __future__ import annotations

import scribbl_py


def test_version() -> None:
    """Test that version is defined."""
    assert scribbl_py.__version__ == "0.1.0"
