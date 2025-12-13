"""Litestar controllers for scribbl-py API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar
from uuid import UUID

from litestar import Controller, delete, get, patch, post
from litestar.response import Response
from litestar.status_codes import HTTP_204_NO_CONTENT

from scribbl_py.core.models import Point
from scribbl_py.exceptions import CanvasNotFoundError, ElementNotFoundError
from scribbl_py.services.canvas import CanvasService
from scribbl_py.services.export import ExportService
from scribbl_py.web.dto import (
    CanvasDetailDTO,
    CanvasResponseDTO,
    CreateCanvasDTO,
    CreateShapeDTO,
    CreateStrokeDTO,
    CreateTextDTO,
    ElementResponseDTO,
    UpdateCanvasDTO,
    canvas_to_detail,
    canvas_to_response,
    element_to_response,
    point_from_dto,
    style_from_dto,
)

if TYPE_CHECKING:
    from typing import Any


class CanvasController(Controller):
    """Controller for canvas-related operations.

    This controller handles HTTP endpoints for managing canvases,
    including creation, retrieval, updating, and deletion.
    """

    path = "/canvases"
    tags: ClassVar[list[str]] = ["Canvases"]

    @post("/")
    async def create_canvas(self, data: CreateCanvasDTO, service: CanvasService) -> CanvasResponseDTO:
        """Create a new canvas.

        Args:
            data: The canvas creation data.
            service: The canvas service instance (injected).

        Returns:
            The created canvas.

        Raises:
            StorageError: If the canvas cannot be created.
        """
        canvas = await service.create_canvas(
            name=data.name,
            width=data.width,
            height=data.height,
            background_color=data.background_color,
        )
        return canvas_to_response(canvas)

    @get("/")
    async def list_canvases(self, service: CanvasService) -> list[CanvasResponseDTO]:
        """List all canvases.

        Args:
            service: The canvas service instance (injected).

        Returns:
            A list of all canvases.

        Raises:
            StorageError: If the list operation fails.
        """
        canvases = await service.list_canvases()
        return [canvas_to_response(c) for c in canvases]

    @get("/{canvas_id:uuid}")
    async def get_canvas(self, canvas_id: UUID, service: CanvasService) -> CanvasDetailDTO:
        """Get a canvas with all its elements.

        Args:
            canvas_id: The unique identifier of the canvas.
            service: The canvas service instance (injected).

        Returns:
            The canvas with all its elements.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            StorageError: If the retrieval operation fails.
        """
        canvas = await service.get_canvas(canvas_id)
        return canvas_to_detail(canvas)

    @patch("/{canvas_id:uuid}")
    async def update_canvas(self, canvas_id: UUID, data: UpdateCanvasDTO, service: CanvasService) -> CanvasResponseDTO:
        """Update canvas properties.

        Only provided fields are updated. Fields with None values are ignored.

        Args:
            canvas_id: The unique identifier of the canvas.
            data: The canvas update data.
            service: The canvas service instance (injected).

        Returns:
            The updated canvas.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            StorageError: If the update operation fails.
        """
        canvas = await service.update_canvas(
            canvas_id,
            name=data.name,
            width=data.width,
            height=data.height,
            background_color=data.background_color,
        )
        return canvas_to_response(canvas)

    @delete("/{canvas_id:uuid}", status_code=HTTP_204_NO_CONTENT)
    async def delete_canvas(self, canvas_id: UUID, service: CanvasService) -> None:
        """Delete a canvas.

        Args:
            canvas_id: The unique identifier of the canvas to delete.
            service: The canvas service instance (injected).

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            StorageError: If the delete operation fails.
        """
        deleted = await service.delete_canvas(canvas_id)
        if not deleted:
            raise CanvasNotFoundError(canvas_id)

    @get("/{canvas_id:uuid}/export/json")
    async def export_json(
        self,
        canvas_id: UUID,
        service: CanvasService,
        export_service: ExportService,
    ) -> dict[str, Any]:
        """Export canvas as JSON.

        Args:
            canvas_id: The unique identifier of the canvas.
            service: The canvas service instance (injected).
            export_service: The export service instance (injected).

        Returns:
            The canvas data as a dictionary.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
        """
        canvas = await service.get_canvas(canvas_id)
        return export_service.to_dict(canvas)

    @get("/{canvas_id:uuid}/export/svg")
    async def export_svg(
        self,
        canvas_id: UUID,
        service: CanvasService,
        export_service: ExportService,
    ) -> Response[str]:
        """Export canvas as SVG.

        Args:
            canvas_id: The unique identifier of the canvas.
            service: The canvas service instance (injected).
            export_service: The export service instance (injected).

        Returns:
            SVG content as a response with appropriate content type.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
        """
        canvas = await service.get_canvas(canvas_id)
        svg_content = export_service.to_svg(canvas)
        return Response(
            content=svg_content,
            media_type="image/svg+xml",
            headers={"Content-Disposition": f'inline; filename="{canvas.name}.svg"'},
        )

    @get("/{canvas_id:uuid}/export/png")
    async def export_png(
        self,
        canvas_id: UUID,
        service: CanvasService,
        export_service: ExportService,
        scale: float = 1.0,
    ) -> Response[bytes]:
        """Export canvas as PNG.

        Requires the 'export' optional dependency to be installed.

        Args:
            canvas_id: The unique identifier of the canvas.
            service: The canvas service instance (injected).
            export_service: The export service instance (injected).
            scale: Scale factor for the output image (default: 1.0).

        Returns:
            PNG image as a response with appropriate content type.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            ImportError: If cairosvg is not installed.
        """
        canvas = await service.get_canvas(canvas_id)
        png_content = export_service.to_png(canvas, scale=scale)
        return Response(
            content=png_content,
            media_type="image/png",
            headers={"Content-Disposition": f'inline; filename="{canvas.name}.png"'},
        )


class ElementController(Controller):
    """Controller for element-related operations.

    This controller handles HTTP endpoints for managing elements on canvases,
    including adding different types of elements and managing them.
    """

    path = "/canvases/{canvas_id:uuid}/elements"
    tags: ClassVar[list[str]] = ["Elements"]

    @get("/")
    async def list_elements(self, canvas_id: UUID, service: CanvasService) -> list[ElementResponseDTO]:
        """List all elements on a canvas.

        Args:
            canvas_id: The unique identifier of the canvas.
            service: The canvas service instance (injected).

        Returns:
            A list of all elements on the canvas.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            StorageError: If the list operation fails.
        """
        elements = await service.list_elements(canvas_id)
        return [element_to_response(e) for e in elements]

    @post("/strokes")
    async def add_stroke(self, canvas_id: UUID, data: CreateStrokeDTO, service: CanvasService) -> ElementResponseDTO:
        """Add a stroke to the canvas.

        Args:
            canvas_id: The unique identifier of the canvas.
            data: The stroke creation data.
            service: The canvas service instance (injected).

        Returns:
            The created stroke element.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            StorageError: If the add operation fails.
        """
        # Convert DTO points to domain Points
        points = [point_from_dto(p) for p in data.points]

        # Convert style if provided
        style = style_from_dto(data.style) if data.style else None

        stroke = await service.add_stroke(
            canvas_id,
            points=points,
            style=style,
            smoothing=data.smoothing,
        )
        return element_to_response(stroke)

    @post("/shapes")
    async def add_shape(self, canvas_id: UUID, data: CreateShapeDTO, service: CanvasService) -> ElementResponseDTO:
        """Add a shape to the canvas.

        Args:
            canvas_id: The unique identifier of the canvas.
            data: The shape creation data.
            service: The canvas service instance (injected).

        Returns:
            The created shape element.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            StorageError: If the add operation fails.
        """
        # Create position point
        position = Point(x=data.x, y=data.y)

        # Convert style if provided
        style = style_from_dto(data.style) if data.style else None

        shape = await service.add_shape(
            canvas_id,
            shape_type=data.shape_type,
            position=position,
            width=data.width,
            height=data.height,
            style=style,
            rotation=data.rotation,
        )
        return element_to_response(shape)

    @post("/texts")
    async def add_text(self, canvas_id: UUID, data: CreateTextDTO, service: CanvasService) -> ElementResponseDTO:
        """Add text to the canvas.

        Args:
            canvas_id: The unique identifier of the canvas.
            data: The text creation data.
            service: The canvas service instance (injected).

        Returns:
            The created text element.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            StorageError: If the add operation fails.
        """
        # Create position point
        position = Point(x=data.x, y=data.y)

        # Convert style if provided
        style = style_from_dto(data.style) if data.style else None

        text = await service.add_text(
            canvas_id,
            content=data.content,
            position=position,
            style=style,
            font_size=data.font_size,
            font_family=data.font_family,
        )
        return element_to_response(text)

    @delete("/{element_id:uuid}", status_code=HTTP_204_NO_CONTENT)
    async def delete_element(self, canvas_id: UUID, element_id: UUID, service: CanvasService) -> None:
        """Delete an element from the canvas.

        Args:
            canvas_id: The unique identifier of the canvas.
            element_id: The unique identifier of the element to delete.
            service: The canvas service instance (injected).

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            ElementNotFoundError: If the element does not exist.
            StorageError: If the delete operation fails.
        """
        deleted = await service.delete_element(canvas_id, element_id)
        if not deleted:
            raise ElementNotFoundError(element_id)
