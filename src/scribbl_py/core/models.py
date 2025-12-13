"""Core domain models for scribbl-py canvas system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from scribbl_py.core.style import ElementStyle
from scribbl_py.core.types import ElementType, ShapeType


@dataclass
class Point:
    """Represents a point in 2D space with optional pressure and timestamp.

    Attributes:
        x: X-coordinate position.
        y: Y-coordinate position.
        pressure: Pressure value for stylus input (0.0 to 1.0).
        timestamp: Optional timestamp when the point was created.
    """

    x: float
    y: float
    pressure: float = 1.0
    timestamp: float | None = None


@dataclass
class Element:
    """Base class for all canvas elements.

    Attributes:
        id: Unique identifier for the element.
        element_type: Type of the element (stroke, shape, text, or group).
        position: Position of the element on the canvas.
        style: Visual styling configuration for the element.
        z_index: Layer ordering (higher values are rendered on top).
        group_id: ID of parent group if this element is grouped.
        created_at: Timestamp when the element was created.
    """

    id: UUID = field(default_factory=uuid4)
    element_type: ElementType = field(init=False)
    position: Point = field(default_factory=lambda: Point(0.0, 0.0))
    style: ElementStyle = field(default_factory=ElementStyle)
    z_index: int = 0
    group_id: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Stroke(Element):
    """Represents a freehand stroke drawn on the canvas.

    Attributes:
        points: List of points that make up the stroke path.
        smoothing: Smoothing factor applied to the stroke (0.0 to 1.0).
    """

    points: list[Point] = field(default_factory=list)
    smoothing: float = 0.5

    def __post_init__(self) -> None:
        """Set the element type to STROKE after initialization."""
        self.element_type = ElementType.STROKE


@dataclass
class Shape(Element):
    """Represents a geometric shape on the canvas.

    Attributes:
        shape_type: Type of shape (rectangle, ellipse, etc.).
        width: Width of the shape in pixels.
        height: Height of the shape in pixels.
        rotation: Rotation angle in degrees.
    """

    shape_type: ShapeType = ShapeType.RECTANGLE
    width: float = 0.0
    height: float = 0.0
    rotation: float = 0.0

    def __post_init__(self) -> None:
        """Set the element type to SHAPE after initialization."""
        self.element_type = ElementType.SHAPE


@dataclass
class Text(Element):
    """Represents a text element on the canvas.

    Attributes:
        content: The text content to display.
        font_size: Font size in pixels.
        font_family: Font family name.
    """

    content: str = ""
    font_size: int = 16
    font_family: str = "sans-serif"

    def __post_init__(self) -> None:
        """Set the element type to TEXT after initialization."""
        self.element_type = ElementType.TEXT


@dataclass
class Group(Element):
    """Represents a group of elements on the canvas.

    Groups allow multiple elements to be treated as a single unit for
    selection, transformation, and organization purposes.

    Attributes:
        name: Optional name for the group.
        children: List of element IDs that belong to this group.
        locked: Whether the group is locked from editing.
        collapsed: Whether the group is collapsed in the layer panel.
    """

    name: str = ""
    children: list[UUID] = field(default_factory=list)
    locked: bool = False
    collapsed: bool = False

    def __post_init__(self) -> None:
        """Set the element type to GROUP after initialization."""
        self.element_type = ElementType.GROUP


@dataclass
class Canvas:
    """Represents a drawing canvas containing elements.

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

    id: UUID = field(default_factory=uuid4)
    name: str = "Untitled Canvas"
    width: int = 1920
    height: int = 1080
    background_color: str = "#ffffff"
    elements: list[Element] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
