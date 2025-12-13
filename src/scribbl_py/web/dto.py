"""Data Transfer Objects (DTOs) for the scribbl-py API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from scribbl_py.core.models import Point as DomainPoint
from scribbl_py.core.models import Shape, Stroke, Text
from scribbl_py.core.style import ElementStyle
from scribbl_py.core.types import ElementType, ShapeType

if TYPE_CHECKING:
    from scribbl_py.core.models import Canvas, Element


# Canvas DTOs


@dataclass
class CreateCanvasDTO:
    """DTO for creating a new canvas.

    Attributes:
        name: Display name for the canvas.
        width: Canvas width in pixels.
        height: Canvas height in pixels.
        background_color: Background color in hex format.
    """

    name: str
    width: int = 1920
    height: int = 1080
    background_color: str = "#ffffff"


@dataclass
class UpdateCanvasDTO:
    """DTO for updating canvas properties.

    All fields are optional. Only provided fields will be updated.

    Attributes:
        name: New display name for the canvas.
        width: New canvas width in pixels.
        height: New canvas height in pixels.
        background_color: New background color in hex format.
    """

    name: str | None = None
    width: int | None = None
    height: int | None = None
    background_color: str | None = None


@dataclass
class CanvasResponseDTO:
    """DTO for canvas list/summary responses.

    Attributes:
        id: Unique identifier for the canvas.
        name: Display name for the canvas.
        width: Canvas width in pixels.
        height: Canvas height in pixels.
        background_color: Background color in hex format.
        element_count: Number of elements on the canvas.
        created_at: Timestamp when the canvas was created.
        updated_at: Timestamp when the canvas was last updated.
    """

    id: UUID
    name: str
    width: int
    height: int
    background_color: str
    element_count: int
    created_at: datetime
    updated_at: datetime


@dataclass
class CanvasDetailDTO:
    """DTO for detailed canvas responses including elements.

    Attributes:
        id: Unique identifier for the canvas.
        name: Display name for the canvas.
        width: Canvas width in pixels.
        height: Canvas height in pixels.
        background_color: Background color in hex format.
        elements: List of elements on the canvas.
        created_at: Timestamp when the canvas was created.
        updated_at: Timestamp when the canvas was last updated.
    """

    id: UUID
    name: str
    width: int
    height: int
    background_color: str
    elements: list[ElementResponseDTO]
    created_at: datetime
    updated_at: datetime


# Element DTOs


@dataclass
class PointDTO:
    """DTO for representing a point in 2D space.

    Attributes:
        x: X-coordinate position.
        y: Y-coordinate position.
        pressure: Pressure value for stylus input (0.0 to 1.0).
    """

    x: float
    y: float
    pressure: float = 1.0


@dataclass
class StyleDTO:
    """DTO for element styling configuration.

    Attributes:
        stroke_color: The color of the element's stroke/outline in hex format.
        fill_color: Optional fill color for the element in hex format.
        stroke_width: Width of the stroke in pixels.
        opacity: Opacity level from 0.0 (transparent) to 1.0 (opaque).
    """

    stroke_color: str = "#000000"
    fill_color: str | None = None
    stroke_width: float = 2.0
    opacity: float = 1.0


@dataclass
class CreateStrokeDTO:
    """DTO for creating a stroke element.

    Attributes:
        points: List of points that make up the stroke path.
        style: Optional styling configuration for the stroke.
        smoothing: Smoothing factor applied to the stroke (0.0 to 1.0).
    """

    points: list[PointDTO]
    style: StyleDTO | None = None
    smoothing: float = 0.5


@dataclass
class CreateShapeDTO:
    """DTO for creating a shape element.

    Attributes:
        shape_type: Type of shape (rectangle, ellipse, etc.).
        x: X-coordinate position.
        y: Y-coordinate position.
        width: Width of the shape in pixels.
        height: Height of the shape in pixels.
        style: Optional styling configuration for the shape.
        rotation: Rotation angle in degrees.
    """

    shape_type: ShapeType
    x: float
    y: float
    width: float
    height: float
    style: StyleDTO | None = None
    rotation: float = 0.0


@dataclass
class CreateTextDTO:
    """DTO for creating a text element.

    Attributes:
        content: The text content to display.
        x: X-coordinate position.
        y: Y-coordinate position.
        style: Optional styling configuration for the text.
        font_size: Font size in pixels.
        font_family: Font family name.
    """

    content: str
    x: float
    y: float
    style: StyleDTO | None = None
    font_size: int = 16
    font_family: str = "sans-serif"


@dataclass
class StrokeDataDTO:
    """DTO for stroke-specific data in element responses.

    Attributes:
        points: List of points that make up the stroke path.
        smoothing: Smoothing factor applied to the stroke (0.0 to 1.0).
    """

    points: list[PointDTO]
    smoothing: float


@dataclass
class ShapeDataDTO:
    """DTO for shape-specific data in element responses.

    Attributes:
        shape_type: Type of shape (rectangle, ellipse, etc.).
        width: Width of the shape in pixels.
        height: Height of the shape in pixels.
        rotation: Rotation angle in degrees.
    """

    shape_type: ShapeType
    width: float
    height: float
    rotation: float


@dataclass
class TextDataDTO:
    """DTO for text-specific data in element responses.

    Attributes:
        content: The text content.
        font_size: Font size in pixels.
        font_family: Font family name.
    """

    content: str
    font_size: int
    font_family: str


@dataclass
class ElementResponseDTO:
    """DTO for element responses.

    This DTO includes common element fields and type-specific data.

    Attributes:
        id: Unique identifier for the element.
        element_type: Type of the element (stroke, shape, or text).
        position: Position of the element on the canvas.
        style: Visual styling configuration for the element.
        created_at: Timestamp when the element was created.
        stroke_data: Stroke-specific data (only for stroke elements).
        shape_data: Shape-specific data (only for shape elements).
        text_data: Text-specific data (only for text elements).
    """

    id: UUID
    element_type: ElementType
    position: PointDTO
    style: StyleDTO
    created_at: datetime
    stroke_data: StrokeDataDTO | None = None
    shape_data: ShapeDataDTO | None = None
    text_data: TextDataDTO | None = None


# Conversion helper functions


def style_to_dto(style: ElementStyle) -> StyleDTO:
    """Convert a domain ElementStyle to a StyleDTO.

    Args:
        style: The domain style object to convert.

    Returns:
        The corresponding StyleDTO.
    """
    return StyleDTO(
        stroke_color=style.stroke_color,
        fill_color=style.fill_color,
        stroke_width=style.stroke_width,
        opacity=style.opacity,
    )


def style_from_dto(dto: StyleDTO) -> ElementStyle:
    """Convert a StyleDTO to a domain ElementStyle.

    Args:
        dto: The DTO to convert.

    Returns:
        The corresponding domain ElementStyle.
    """
    return ElementStyle(
        stroke_color=dto.stroke_color,
        fill_color=dto.fill_color,
        stroke_width=dto.stroke_width,
        opacity=dto.opacity,
    )


def point_to_dto(point: DomainPoint) -> PointDTO:
    """Convert a domain Point to a PointDTO.

    Args:
        point: The domain point to convert.

    Returns:
        The corresponding PointDTO.
    """
    return PointDTO(
        x=point.x,
        y=point.y,
        pressure=point.pressure,
    )


def point_from_dto(dto: PointDTO) -> DomainPoint:
    """Convert a PointDTO to a domain Point.

    Args:
        dto: The DTO to convert.

    Returns:
        The corresponding domain Point.
    """
    return DomainPoint(
        x=dto.x,
        y=dto.y,
        pressure=dto.pressure,
    )


def canvas_to_response(canvas: Canvas) -> CanvasResponseDTO:
    """Convert a Canvas domain model to a CanvasResponseDTO.

    Args:
        canvas: The canvas to convert.

    Returns:
        The corresponding CanvasResponseDTO.
    """
    return CanvasResponseDTO(
        id=canvas.id,
        name=canvas.name,
        width=canvas.width,
        height=canvas.height,
        background_color=canvas.background_color,
        element_count=len(canvas.elements),
        created_at=canvas.created_at,
        updated_at=canvas.updated_at,
    )


def canvas_to_detail(canvas: Canvas) -> CanvasDetailDTO:
    """Convert a Canvas domain model to a CanvasDetailDTO.

    Args:
        canvas: The canvas to convert.

    Returns:
        The corresponding CanvasDetailDTO.
    """
    return CanvasDetailDTO(
        id=canvas.id,
        name=canvas.name,
        width=canvas.width,
        height=canvas.height,
        background_color=canvas.background_color,
        elements=[element_to_response(elem) for elem in canvas.elements],
        created_at=canvas.created_at,
        updated_at=canvas.updated_at,
    )


def element_to_response(element: Element) -> ElementResponseDTO:
    """Convert an Element domain model to an ElementResponseDTO.

    Args:
        element: The element to convert.

    Returns:
        The corresponding ElementResponseDTO.
    """
    base_dto = ElementResponseDTO(
        id=element.id,
        element_type=element.element_type,
        position=point_to_dto(element.position),
        style=style_to_dto(element.style),
        created_at=element.created_at,
    )

    if isinstance(element, Stroke):
        base_dto.stroke_data = StrokeDataDTO(
            points=[point_to_dto(p) for p in element.points],
            smoothing=element.smoothing,
        )
    elif isinstance(element, Shape):
        base_dto.shape_data = ShapeDataDTO(
            shape_type=element.shape_type,
            width=element.width,
            height=element.height,
            rotation=element.rotation,
        )
    elif isinstance(element, Text):
        base_dto.text_data = TextDataDTO(
            content=element.content,
            font_size=element.font_size,
            font_family=element.font_family,
        )

    return base_dto
