"""Custom exceptions for scribbl-py."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID


class ScribblError(Exception):
    """Base exception class for all scribbl-py errors."""


class CanvasNotFoundError(ScribblError):
    """Raised when a canvas with the specified ID cannot be found.

    Attributes:
        canvas_id: The UUID of the canvas that was not found.
    """

    def __init__(self, canvas_id: UUID) -> None:
        """Initialize the exception with the canvas ID.

        Args:
            canvas_id: The UUID of the canvas that was not found.
        """
        self.canvas_id = canvas_id
        super().__init__(f"Canvas with ID {canvas_id} not found")


class ElementNotFoundError(ScribblError):
    """Raised when an element with the specified ID cannot be found.

    Attributes:
        element_id: The UUID of the element that was not found.
    """

    def __init__(self, element_id: UUID) -> None:
        """Initialize the exception with the element ID.

        Args:
            element_id: The UUID of the element that was not found.
        """
        self.element_id = element_id
        super().__init__(f"Element with ID {element_id} not found")


class InvalidElementError(ScribblError):
    """Raised when an element is invalid or malformed.

    This exception is used for validation errors related to element data.
    """

    def __init__(self, message: str) -> None:
        """Initialize the exception with a custom message.

        Args:
            message: Description of why the element is invalid.
        """
        super().__init__(message)
