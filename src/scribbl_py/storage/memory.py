"""In-memory storage implementation for scribbl-py."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from scribbl_py.core.exceptions import CanvasNotFoundError, ElementNotFoundError

if TYPE_CHECKING:
    from uuid import UUID

    from scribbl_py.core.models import Canvas, Element


class InMemoryStorage:
    """Thread-safe in-memory storage implementation.

    This storage backend maintains all data in memory using a dictionary. It provides
    thread safety through asyncio locks and returns immutable copies of data to prevent
    external modification.

    Note:
        All data is lost when the application stops. This storage is suitable for
        development, testing, or ephemeral sessions.

    Attributes:
        _canvases: Internal dictionary mapping canvas IDs to Canvas instances.
        _lock: Asyncio lock for thread-safe operations.
    """

    def __init__(self) -> None:
        """Initialize the in-memory storage with an empty canvas dictionary."""
        self._canvases: dict[UUID, Canvas] = {}
        self._lock = asyncio.Lock()

    async def create_canvas(self, canvas: Canvas) -> Canvas:
        """Create a new canvas in storage.

        Args:
            canvas: The canvas to create.

        Returns:
            A copy of the created canvas.
        """
        async with self._lock:
            # Store a copy to prevent external modification
            self._canvases[canvas.id] = replace(canvas)
            return replace(canvas)

    async def get_canvas(self, canvas_id: UUID) -> Canvas | None:
        """Retrieve a canvas by its ID.

        Args:
            canvas_id: The unique identifier of the canvas.

        Returns:
            A copy of the canvas if found, None otherwise.
        """
        async with self._lock:
            canvas = self._canvases.get(canvas_id)
            return replace(canvas) if canvas else None

    async def list_canvases(self) -> list[Canvas]:
        """List all canvases in storage.

        Returns:
            A list of canvas copies, ordered by creation date (newest first).
        """
        async with self._lock:
            canvases = [replace(canvas) for canvas in self._canvases.values()]
            return sorted(canvases, key=lambda c: c.created_at, reverse=True)

    async def update_canvas(self, canvas: Canvas) -> Canvas:
        """Update an existing canvas in storage.

        Args:
            canvas: The canvas with updated data.

        Returns:
            A copy of the updated canvas.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
        """
        async with self._lock:
            if canvas.id not in self._canvases:
                raise CanvasNotFoundError(str(canvas.id))

            # Update the timestamp
            updated_canvas = replace(canvas, updated_at=datetime.now(UTC))
            self._canvases[canvas.id] = updated_canvas
            return replace(updated_canvas)

    async def delete_canvas(self, canvas_id: UUID) -> bool:
        """Delete a canvas from storage.

        Args:
            canvas_id: The unique identifier of the canvas to delete.

        Returns:
            True if the canvas was deleted, False if it did not exist.
        """
        async with self._lock:
            if canvas_id in self._canvases:
                del self._canvases[canvas_id]
                return True
            return False

    async def add_element(self, canvas_id: UUID, element: Element) -> Element:
        """Add an element to a canvas.

        Args:
            canvas_id: The unique identifier of the canvas.
            element: The element to add.

        Returns:
            A copy of the added element.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
        """
        async with self._lock:
            canvas = self._canvases.get(canvas_id)
            if not canvas:
                raise CanvasNotFoundError(str(canvas_id))

            # Create updated canvas with new element and updated timestamp
            new_elements = [*canvas.elements, replace(element)]
            updated_canvas = replace(
                canvas,
                elements=new_elements,
                updated_at=datetime.now(UTC),
            )
            self._canvases[canvas_id] = updated_canvas
            return replace(element)

    async def get_element(self, canvas_id: UUID, element_id: UUID) -> Element | None:
        """Retrieve an element from a canvas.

        Args:
            canvas_id: The unique identifier of the canvas.
            element_id: The unique identifier of the element.

        Returns:
            A copy of the element if found, None otherwise.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
        """
        async with self._lock:
            canvas = self._canvases.get(canvas_id)
            if not canvas:
                raise CanvasNotFoundError(str(canvas_id))

            for element in canvas.elements:
                if element.id == element_id:
                    return replace(element)
            return None

    async def update_element(self, canvas_id: UUID, element: Element) -> Element:
        """Update an element on a canvas.

        Args:
            canvas_id: The unique identifier of the canvas.
            element: The element with updated data.

        Returns:
            A copy of the updated element.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            ElementNotFoundError: If the element does not exist.
        """
        async with self._lock:
            canvas = self._canvases.get(canvas_id)
            if not canvas:
                raise CanvasNotFoundError(str(canvas_id))

            # Find and update the element
            element_found = False
            updated_elements = []
            for existing_element in canvas.elements:
                if existing_element.id == element.id:
                    updated_elements.append(replace(element))
                    element_found = True
                else:
                    updated_elements.append(existing_element)

            if not element_found:
                raise ElementNotFoundError(str(element.id), str(canvas_id))

            # Update canvas with modified elements and timestamp
            updated_canvas = replace(
                canvas,
                elements=updated_elements,
                updated_at=datetime.now(UTC),
            )
            self._canvases[canvas_id] = updated_canvas
            return replace(element)

    async def delete_element(self, canvas_id: UUID, element_id: UUID) -> bool:
        """Delete an element from a canvas.

        Args:
            canvas_id: The unique identifier of the canvas.
            element_id: The unique identifier of the element to delete.

        Returns:
            True if the element was deleted, False if it did not exist.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
        """
        async with self._lock:
            canvas = self._canvases.get(canvas_id)
            if not canvas:
                raise CanvasNotFoundError(str(canvas_id))

            # Filter out the element to delete
            initial_count = len(canvas.elements)
            updated_elements = [e for e in canvas.elements if e.id != element_id]

            # Check if element was actually removed
            if len(updated_elements) == initial_count:
                return False

            # Update canvas with modified elements and timestamp
            updated_canvas = replace(
                canvas,
                elements=updated_elements,
                updated_at=datetime.now(UTC),
            )
            self._canvases[canvas_id] = updated_canvas
            return True

    async def list_elements(self, canvas_id: UUID) -> list[Element]:
        """List all elements on a canvas.

        Args:
            canvas_id: The unique identifier of the canvas.

        Returns:
            A list of element copies, ordered by creation date.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
        """
        async with self._lock:
            canvas = self._canvases.get(canvas_id)
            if not canvas:
                raise CanvasNotFoundError(str(canvas_id))

            return [replace(element) for element in canvas.elements]
