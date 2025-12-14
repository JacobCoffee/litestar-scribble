"""SQLAlchemy models for scribbl-py database storage."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class CanvasModel(UUIDAuditBase):
    """SQLAlchemy model for Canvas entities.

    Attributes:
        id: UUID primary key (from UUIDAuditBase).
        name: Display name for the canvas.
        width: Canvas width in pixels.
        height: Canvas height in pixels.
        background_color: Background color in hex format.
        elements: Related element records.
        created_at: Creation timestamp (from UUIDAuditBase).
        updated_at: Last update timestamp (from UUIDAuditBase).
    """

    __tablename__ = "canvases"

    name: Mapped[str] = mapped_column(String(255), default="Untitled Canvas")
    width: Mapped[int] = mapped_column(Integer, default=1920)
    height: Mapped[int] = mapped_column(Integer, default=1080)
    background_color: Mapped[str] = mapped_column(String(7), default="#ffffff")

    elements: Mapped[list[ElementModel]] = relationship(
        "ElementModel",
        back_populates="canvas",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ElementModel.created_at",
    )


class ElementModel(UUIDAuditBase):
    """SQLAlchemy model for Element entities.

    This model stores all element types (Stroke, Shape, Text, Group) in a single table
    using a discriminator column (element_type) and JSON columns for type-specific data.

    Attributes:
        id: UUID primary key (from UUIDAuditBase).
        canvas_id: Foreign key to parent canvas.
        element_type: Discriminator for element type (stroke, shape, text, group).
        position_x: X-coordinate position.
        position_y: Y-coordinate position.
        position_pressure: Pressure value for position point.
        z_index: Layer ordering (higher values rendered on top).
        group_id: Parent group ID if this element is grouped.
        style_data: JSON blob for ElementStyle fields.
        element_data: JSON blob for type-specific data (points, shape_type, content, etc.).
        created_at: Creation timestamp (from UUIDAuditBase).
        updated_at: Last update timestamp (from UUIDAuditBase).
    """

    __tablename__ = "elements"

    canvas_id: Mapped[UUID] = mapped_column(ForeignKey("canvases.id", ondelete="CASCADE"), index=True)
    element_type: Mapped[str] = mapped_column(String(20), index=True)

    # Position fields
    position_x: Mapped[float] = mapped_column(Float, default=0.0)
    position_y: Mapped[float] = mapped_column(Float, default=0.0)
    position_pressure: Mapped[float] = mapped_column(Float, default=1.0)

    # Layer ordering and state
    z_index: Mapped[int] = mapped_column(Integer, default=0, index=True)
    group_id: Mapped[UUID | None] = mapped_column(ForeignKey("elements.id", ondelete="SET NULL"), nullable=True)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Style stored as JSON for flexibility
    style_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Type-specific data stored as JSON
    # For Stroke: {"points": [...], "smoothing": 0.5}
    # For Shape: {"shape_type": "rectangle", "width": 100, "height": 75, "rotation": 0}
    # For Text: {"content": "...", "font_size": 16, "font_family": "sans-serif"}
    # For Group: {"name": "...", "children": [...], "locked": false, "collapsed": false}
    element_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    canvas: Mapped[CanvasModel] = relationship("CanvasModel", back_populates="elements")


def canvas_to_model(canvas: Any) -> CanvasModel:
    """Convert a domain Canvas to a CanvasModel.

    Args:
        canvas: Domain Canvas dataclass instance.

    Returns:
        CanvasModel instance ready for database insertion.
    """
    return CanvasModel(
        id=canvas.id,
        name=canvas.name,
        width=canvas.width,
        height=canvas.height,
        background_color=canvas.background_color,
        created_at=canvas.created_at,
        updated_at=canvas.updated_at,
    )


def canvas_from_model(model: CanvasModel, include_elements: bool = True) -> Any:
    """Convert a CanvasModel to a domain Canvas.

    Args:
        model: SQLAlchemy CanvasModel instance.
        include_elements: Whether to include elements in the conversion.

    Returns:
        Domain Canvas dataclass instance.
    """
    from scribbl_py.core.models import Canvas

    elements = []
    if include_elements and model.elements:
        elements = [element_from_model(e) for e in model.elements]

    return Canvas(
        id=model.id,
        name=model.name,
        width=model.width,
        height=model.height,
        background_color=model.background_color,
        elements=elements,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def element_to_model(element: Any, canvas_id: UUID) -> ElementModel:
    """Convert a domain Element to an ElementModel.

    Args:
        element: Domain Element (Stroke, Shape, Text, or Group) dataclass instance.
        canvas_id: UUID of the parent canvas.

    Returns:
        ElementModel instance ready for database insertion.
    """
    from scribbl_py.core.types import ElementType

    # Build style data
    style_data = {
        "stroke_color": element.style.stroke_color,
        "fill_color": element.style.fill_color,
        "stroke_width": element.style.stroke_width,
        "opacity": element.style.opacity,
    }

    # Build type-specific data
    element_data: dict[str, Any] = {}
    if element.element_type == ElementType.STROKE:
        element_data = {
            "points": [{"x": p.x, "y": p.y, "pressure": p.pressure, "timestamp": p.timestamp} for p in element.points],
            "smoothing": element.smoothing,
        }
    elif element.element_type == ElementType.SHAPE:
        element_data = {
            "shape_type": element.shape_type.value,
            "width": element.width,
            "height": element.height,
            "rotation": element.rotation,
        }
    elif element.element_type == ElementType.TEXT:
        element_data = {
            "content": element.content,
            "font_size": element.font_size,
            "font_family": element.font_family,
        }
    elif element.element_type == ElementType.GROUP:
        element_data = {
            "name": element.name,
            "children": [str(child_id) for child_id in element.children],
            "locked": element.locked,
            "collapsed": element.collapsed,
        }

    return ElementModel(
        id=element.id,
        canvas_id=canvas_id,
        element_type=element.element_type.value,
        position_x=element.position.x,
        position_y=element.position.y,
        position_pressure=element.position.pressure,
        z_index=element.z_index,
        group_id=element.group_id,
        visible=element.visible,
        locked=element.locked,
        style_data=style_data,
        element_data=element_data,
        created_at=element.created_at,
    )


def element_from_model(model: ElementModel) -> Any:
    """Convert an ElementModel to a domain Element.

    Args:
        model: SQLAlchemy ElementModel instance.

    Returns:
        Domain Element (Stroke, Shape, Text, or Group) dataclass instance.
    """
    from scribbl_py.core.models import Group, Point, Shape, Stroke
    from scribbl_py.core.models import Text as TextElement
    from scribbl_py.core.style import ElementStyle
    from scribbl_py.core.types import ElementType, ShapeType

    # Reconstruct position
    position = Point(
        x=model.position_x,
        y=model.position_y,
        pressure=model.position_pressure,
    )

    # Reconstruct style
    style = ElementStyle(
        stroke_color=model.style_data.get("stroke_color", "#000000"),
        fill_color=model.style_data.get("fill_color"),
        stroke_width=model.style_data.get("stroke_width", 2.0),
        opacity=model.style_data.get("opacity", 1.0),
    )

    element_type = ElementType(model.element_type)
    data = model.element_data

    if element_type == ElementType.STROKE:
        points = [
            Point(
                x=p["x"],
                y=p["y"],
                pressure=p.get("pressure", 1.0),
                timestamp=p.get("timestamp"),
            )
            for p in data.get("points", [])
        ]
        element = Stroke(
            id=model.id,
            position=position,
            style=style,
            z_index=model.z_index,
            group_id=model.group_id,
            visible=model.visible,
            locked=model.locked,
            points=points,
            smoothing=data.get("smoothing", 0.5),
        )
        element.created_at = model.created_at
        return element

    if element_type == ElementType.SHAPE:
        element = Shape(
            id=model.id,
            position=position,
            style=style,
            z_index=model.z_index,
            group_id=model.group_id,
            visible=model.visible,
            locked=model.locked,
            shape_type=ShapeType(data.get("shape_type", "rectangle")),
            width=data.get("width", 0.0),
            height=data.get("height", 0.0),
            rotation=data.get("rotation", 0.0),
        )
        element.created_at = model.created_at
        return element

    if element_type == ElementType.TEXT:
        element = TextElement(
            id=model.id,
            position=position,
            style=style,
            z_index=model.z_index,
            group_id=model.group_id,
            visible=model.visible,
            locked=model.locked,
            content=data.get("content", ""),
            font_size=data.get("font_size", 16),
            font_family=data.get("font_family", "sans-serif"),
        )
        element.created_at = model.created_at
        return element

    # ElementType.GROUP
    children = [UUID(child_id) for child_id in data.get("children", [])]
    element = Group(
        id=model.id,
        position=position,
        style=style,
        z_index=model.z_index,
        group_id=model.group_id,
        visible=model.visible,
        locked=model.locked,
        name=data.get("name", ""),
        children=children,
        collapsed=data.get("collapsed", False),
    )
    element.created_at = model.created_at
    return element
