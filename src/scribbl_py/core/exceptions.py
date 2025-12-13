"""Exception classes for scribbl-py."""

from __future__ import annotations


class ScribblError(Exception):
    """Base exception for all scribbl-py errors."""


class CanvasNotFoundError(ScribblError):
    """Raised when a canvas is not found in storage."""

    def __init__(self, canvas_id: str) -> None:
        """Initialize the exception.

        Args:
            canvas_id: The ID of the canvas that was not found.
        """
        super().__init__(f"Canvas not found: {canvas_id}")
        self.canvas_id = canvas_id


class ElementNotFoundError(ScribblError):
    """Raised when an element is not found on a canvas."""

    def __init__(self, element_id: str, canvas_id: str) -> None:
        """Initialize the exception.

        Args:
            element_id: The ID of the element that was not found.
            canvas_id: The ID of the canvas.
        """
        super().__init__(f"Element {element_id} not found on canvas {canvas_id}")
        self.element_id = element_id
        self.canvas_id = canvas_id


class StorageError(ScribblError):
    """Raised when a storage operation fails."""
