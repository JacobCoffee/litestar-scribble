"""Database storage implementation for scribbl-py."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from scribbl_py.core.exceptions import CanvasNotFoundError, ElementNotFoundError
from scribbl_py.storage.db.models import (
    CanvasModel,
    ElementModel,
    canvas_from_model,
    canvas_to_model,
    element_from_model,
    element_to_model,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from scribbl_py.core.models import Canvas, Element


class DatabaseStorage:
    """Async database storage implementation using SQLAlchemy.

    This storage backend persists canvases and elements to a relational database
    using SQLAlchemy's async session. It implements the StorageProtocol interface.

    Attributes:
        _session: SQLAlchemy async session for database operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the database storage with an async session.

        Args:
            session: SQLAlchemy async session for database operations.
        """
        self._session = session

    async def create_canvas(self, canvas: Canvas) -> Canvas:
        """Create a new canvas in the database.

        Args:
            canvas: The canvas to create.

        Returns:
            The created canvas with database-assigned timestamps.
        """
        model = canvas_to_model(canvas)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return canvas_from_model(model, include_elements=False)

    async def get_canvas(self, canvas_id: UUID) -> Canvas | None:
        """Retrieve a canvas by its ID.

        Args:
            canvas_id: The unique identifier of the canvas.

        Returns:
            The canvas if found, None otherwise.
        """
        stmt = select(CanvasModel).where(CanvasModel.id == canvas_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return canvas_from_model(model)

    async def list_canvases(self) -> list[Canvas]:
        """List all canvases in the database.

        Returns:
            A list of all canvases, ordered by creation date (newest first).
        """
        stmt = select(CanvasModel).order_by(CanvasModel.created_at.desc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [canvas_from_model(m, include_elements=False) for m in models]

    async def update_canvas(self, canvas: Canvas) -> Canvas:
        """Update an existing canvas in the database.

        Args:
            canvas: The canvas with updated data.

        Returns:
            The updated canvas.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
        """
        stmt = select(CanvasModel).where(CanvasModel.id == canvas.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise CanvasNotFoundError(str(canvas.id))

        model.name = canvas.name
        model.width = canvas.width
        model.height = canvas.height
        model.background_color = canvas.background_color
        model.updated_at = datetime.now(UTC)

        await self._session.flush()
        await self._session.refresh(model)
        return canvas_from_model(model)

    async def delete_canvas(self, canvas_id: UUID) -> bool:
        """Delete a canvas from the database.

        Args:
            canvas_id: The unique identifier of the canvas to delete.

        Returns:
            True if the canvas was deleted, False if it did not exist.
        """
        stmt = select(CanvasModel).where(CanvasModel.id == canvas_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return False

        await self._session.delete(model)
        await self._session.flush()
        return True

    async def add_element(self, canvas_id: UUID, element: Element) -> Element:
        """Add an element to a canvas.

        Args:
            canvas_id: The unique identifier of the canvas.
            element: The element to add.

        Returns:
            The added element.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
        """
        # Verify canvas exists
        stmt = select(CanvasModel.id).where(CanvasModel.id == canvas_id)
        result = await self._session.execute(stmt)
        if result.scalar_one_or_none() is None:
            raise CanvasNotFoundError(str(canvas_id))

        model = element_to_model(element, canvas_id)
        self._session.add(model)

        # Update canvas timestamp
        canvas_stmt = select(CanvasModel).where(CanvasModel.id == canvas_id)
        canvas_result = await self._session.execute(canvas_stmt)
        canvas_model = canvas_result.scalar_one()
        canvas_model.updated_at = datetime.now(UTC)

        await self._session.flush()
        await self._session.refresh(model)
        return element_from_model(model)

    async def get_element(self, canvas_id: UUID, element_id: UUID) -> Element | None:
        """Retrieve an element from a canvas.

        Args:
            canvas_id: The unique identifier of the canvas.
            element_id: The unique identifier of the element.

        Returns:
            The element if found, None otherwise.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
        """
        # Verify canvas exists
        canvas_stmt = select(CanvasModel.id).where(CanvasModel.id == canvas_id)
        result = await self._session.execute(canvas_stmt)
        if result.scalar_one_or_none() is None:
            raise CanvasNotFoundError(str(canvas_id))

        stmt = select(ElementModel).where(
            ElementModel.canvas_id == canvas_id,
            ElementModel.id == element_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return element_from_model(model)

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
        """
        # Verify canvas exists
        canvas_stmt = select(CanvasModel).where(CanvasModel.id == canvas_id)
        result = await self._session.execute(canvas_stmt)
        canvas_model = result.scalar_one_or_none()
        if canvas_model is None:
            raise CanvasNotFoundError(str(canvas_id))

        # Find the element
        stmt = select(ElementModel).where(
            ElementModel.canvas_id == canvas_id,
            ElementModel.id == element.id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise ElementNotFoundError(str(element.id), str(canvas_id))

        # Update element from domain object
        updated = element_to_model(element, canvas_id)
        model.element_type = updated.element_type
        model.position_x = updated.position_x
        model.position_y = updated.position_y
        model.position_pressure = updated.position_pressure
        model.style_data = updated.style_data
        model.element_data = updated.element_data
        model.updated_at = datetime.now(UTC)

        # Update canvas timestamp
        canvas_model.updated_at = datetime.now(UTC)

        await self._session.flush()
        await self._session.refresh(model)
        return element_from_model(model)

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
        # Verify canvas exists
        canvas_stmt = select(CanvasModel).where(CanvasModel.id == canvas_id)
        result = await self._session.execute(canvas_stmt)
        canvas_model = result.scalar_one_or_none()
        if canvas_model is None:
            raise CanvasNotFoundError(str(canvas_id))

        # Find the element
        stmt = select(ElementModel).where(
            ElementModel.canvas_id == canvas_id,
            ElementModel.id == element_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return False

        await self._session.delete(model)

        # Update canvas timestamp
        canvas_model.updated_at = datetime.now(UTC)

        await self._session.flush()
        return True

    async def list_elements(self, canvas_id: UUID) -> list[Element]:
        """List all elements on a canvas.

        Args:
            canvas_id: The unique identifier of the canvas.

        Returns:
            A list of all elements on the canvas, ordered by creation date.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
        """
        # Verify canvas exists
        canvas_stmt = select(CanvasModel.id).where(CanvasModel.id == canvas_id)
        result = await self._session.execute(canvas_stmt)
        if result.scalar_one_or_none() is None:
            raise CanvasNotFoundError(str(canvas_id))

        stmt = select(ElementModel).where(ElementModel.canvas_id == canvas_id).order_by(ElementModel.created_at)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [element_from_model(m) for m in models]
