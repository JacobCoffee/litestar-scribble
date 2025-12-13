"""Storage protocol definition for scribbl-py."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from uuid import UUID

    from scribbl_py.core.models import Canvas, Element


@runtime_checkable
class StorageProtocol(Protocol):
    """Protocol defining the storage interface for scribbl-py.

    This protocol defines the contract that all storage backends must implement
    to provide persistence for canvases and elements.
    """

    async def create_canvas(self, canvas: Canvas) -> Canvas:
        """Create a new canvas in storage.

        Args:
            canvas: The canvas to create.

        Returns:
            The created canvas with any storage-specific modifications.

        Raises:
            StorageError: If the canvas cannot be created.
        """
        ...

    async def get_canvas(self, canvas_id: UUID) -> Canvas | None:
        """Retrieve a canvas by its ID.

        Args:
            canvas_id: The unique identifier of the canvas.

        Returns:
            The canvas if found, None otherwise.

        Raises:
            StorageError: If the retrieval operation fails.
        """
        ...

    async def list_canvases(self) -> list[Canvas]:
        """List all canvases in storage.

        Returns:
            A list of all canvases, ordered by creation date (newest first).

        Raises:
            StorageError: If the list operation fails.
        """
        ...

    async def update_canvas(self, canvas: Canvas) -> Canvas:
        """Update an existing canvas in storage.

        Args:
            canvas: The canvas with updated data.

        Returns:
            The updated canvas.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            StorageError: If the update operation fails.
        """
        ...

    async def delete_canvas(self, canvas_id: UUID) -> bool:
        """Delete a canvas from storage.

        Args:
            canvas_id: The unique identifier of the canvas to delete.

        Returns:
            True if the canvas was deleted, False if it did not exist.

        Raises:
            StorageError: If the delete operation fails.
        """
        ...

    async def add_element(self, canvas_id: UUID, element: Element) -> Element:
        """Add an element to a canvas.

        Args:
            canvas_id: The unique identifier of the canvas.
            element: The element to add.

        Returns:
            The added element.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            StorageError: If the add operation fails.
        """
        ...

    async def get_element(self, canvas_id: UUID, element_id: UUID) -> Element | None:
        """Retrieve an element from a canvas.

        Args:
            canvas_id: The unique identifier of the canvas.
            element_id: The unique identifier of the element.

        Returns:
            The element if found, None otherwise.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            StorageError: If the retrieval operation fails.
        """
        ...

    async def update_element(self, canvas_id: UUID, element: Element) -> Element:
        """Update an element on a canvas.

        Args:
            canvas_id: The unique identifier of the canvas.
            element: The element with updated data.

        Returns:
            The updated element.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            ElementNotFoundError: If the element does not exist.
            StorageError: If the update operation fails.
        """
        ...

    async def delete_element(self, canvas_id: UUID, element_id: UUID) -> bool:
        """Delete an element from a canvas.

        Args:
            canvas_id: The unique identifier of the canvas.
            element_id: The unique identifier of the element to delete.

        Returns:
            True if the element was deleted, False if it did not exist.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            StorageError: If the delete operation fails.
        """
        ...

    async def list_elements(self, canvas_id: UUID) -> list[Element]:
        """List all elements on a canvas.

        Args:
            canvas_id: The unique identifier of the canvas.

        Returns:
            A list of all elements on the canvas, ordered by creation date.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            StorageError: If the list operation fails.
        """
        ...
