"""Export service for canvas rendering to various formats."""

from __future__ import annotations

import io
import json
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from PIL import Image, ImageDraw

from scribbl_py.core.models import Canvas, Group, Shape, Stroke, Text
from scribbl_py.core.types import ShapeType

if TYPE_CHECKING:
    from scribbl_py.core.models import Element


class ExportService:
    """Service for exporting canvases to various formats.

    Supports exporting to:
    - JSON: Full canvas data with all elements
    - SVG: Vector graphics representation
    - PNG: Raster image
    """

    def to_json(self, canvas: Canvas, *, indent: int | None = 2) -> str:
        """Export canvas to JSON format.

        Args:
            canvas: The canvas to export.
            indent: JSON indentation level (None for compact).

        Returns:
            JSON string representation of the canvas.
        """
        return json.dumps(
            self._canvas_to_dict(canvas),
            indent=indent,
            default=self._json_serializer,
        )

    def to_dict(self, canvas: Canvas) -> dict[str, Any]:
        """Export canvas to a dictionary.

        Args:
            canvas: The canvas to export.

        Returns:
            Dictionary representation of the canvas.
        """
        return self._canvas_to_dict(canvas)

    def to_svg(self, canvas: Canvas) -> str:
        """Export canvas to SVG format.

        Args:
            canvas: The canvas to export.

        Returns:
            SVG string representation of the canvas.
        """
        # Sort elements by z_index for proper layering
        sorted_elements = sorted(canvas.elements, key=lambda e: e.z_index)

        svg_elements = []
        for element in sorted_elements:
            svg_element = self._element_to_svg(element)
            if svg_element:
                svg_elements.append(svg_element)

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="{canvas.width}"
     height="{canvas.height}"
     viewBox="0 0 {canvas.width} {canvas.height}">
  <title>{self._escape_xml(canvas.name)}</title>
  <rect width="100%" height="100%" fill="{canvas.background_color}"/>
  {chr(10).join(svg_elements)}
</svg>"""

    def to_png(self, canvas: Canvas, *, scale: float = 1.0) -> bytes:
        """Export canvas to PNG format using Pillow.

        Args:
            canvas: The canvas to export.
            scale: Scale factor for the output image.

        Returns:
            PNG image as bytes.
        """
        width = int(canvas.width * scale)
        height = int(canvas.height * scale)

        # Create image with background color
        bg_color = self._parse_color(canvas.background_color)
        image = Image.new("RGBA", (width, height), bg_color)
        draw = ImageDraw.Draw(image)

        # Sort elements by z_index for proper layering
        sorted_elements = sorted(canvas.elements, key=lambda e: e.z_index)

        for element in sorted_elements:
            self._draw_element(draw, element, scale)

        # Convert to bytes
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def _parse_color(self, color: str | None) -> tuple[int, int, int, int]:
        """Parse hex color string to RGBA tuple."""
        if not color:
            return (0, 0, 0, 255)
        color = color.lstrip("#")
        if len(color) == 6:
            r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
            return (r, g, b, 255)
        if len(color) == 8:
            r, g, b, a = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16), int(color[6:8], 16)
            return (r, g, b, a)
        return (0, 0, 0, 255)

    def _draw_element(self, draw: ImageDraw.ImageDraw, element: Element, scale: float) -> None:
        """Draw an element onto the image."""
        if isinstance(element, Stroke):
            self._draw_stroke(draw, element, scale)
        elif isinstance(element, Shape):
            self._draw_shape(draw, element, scale)
        elif isinstance(element, Text):
            self._draw_text(draw, element, scale)

    def _draw_stroke(self, draw: ImageDraw.ImageDraw, stroke: Stroke, scale: float) -> None:
        """Draw a stroke onto the image."""
        if not stroke.points or len(stroke.points) < 2:
            return

        color = self._parse_color(stroke.style.stroke_color)
        width = max(1, int(stroke.style.stroke_width * scale))

        # Draw lines between consecutive points
        for i in range(len(stroke.points) - 1):
            p1 = stroke.points[i]
            p2 = stroke.points[i + 1]
            draw.line(
                [(p1.x * scale, p1.y * scale), (p2.x * scale, p2.y * scale)],
                fill=color,
                width=width,
            )

    def _draw_shape(self, draw: ImageDraw.ImageDraw, shape: Shape, scale: float) -> None:
        """Draw a shape onto the image."""
        x = shape.position.x * scale
        y = shape.position.y * scale
        w = shape.width * scale
        h = shape.height * scale

        fill = self._parse_color(shape.style.fill_color) if shape.style.fill_color else None
        outline = self._parse_color(shape.style.stroke_color)
        width = max(1, int(shape.style.stroke_width * scale))

        if shape.shape_type == ShapeType.RECTANGLE:
            draw.rectangle([x, y, x + w, y + h], fill=fill, outline=outline, width=width)
        elif shape.shape_type == ShapeType.ELLIPSE:
            draw.ellipse([x, y, x + w, y + h], fill=fill, outline=outline, width=width)
        elif shape.shape_type == ShapeType.LINE:
            draw.line([(x, y), (x + w, y + h)], fill=outline, width=width)
        elif shape.shape_type == ShapeType.TRIANGLE:
            points = [(x + w / 2, y), (x, y + h), (x + w, y + h)]
            draw.polygon(points, fill=fill, outline=outline, width=width)

    def _draw_text(self, draw: ImageDraw.ImageDraw, text: Text, scale: float) -> None:
        """Draw text onto the image."""
        x = text.position.x * scale
        y = text.position.y * scale
        color = self._parse_color(text.style.stroke_color or text.style.fill_color)
        # Note: Custom fonts would require loading font files
        draw.text((x, y), text.content, fill=color)

    def _canvas_to_dict(self, canvas: Canvas) -> dict[str, Any]:
        """Convert canvas to dictionary with proper serialization."""
        return {
            "id": str(canvas.id),
            "name": canvas.name,
            "width": canvas.width,
            "height": canvas.height,
            "background_color": canvas.background_color,
            "elements": [self._element_to_dict(e) for e in canvas.elements],
            "created_at": canvas.created_at.isoformat(),
            "updated_at": canvas.updated_at.isoformat(),
        }

    def _element_to_dict(self, element: Element) -> dict[str, Any]:
        """Convert element to dictionary with proper serialization."""
        base = {
            "id": str(element.id),
            "element_type": element.element_type.value,
            "position": {"x": element.position.x, "y": element.position.y},
            "style": {
                "stroke_color": element.style.stroke_color,
                "fill_color": element.style.fill_color,
                "stroke_width": element.style.stroke_width,
                "opacity": element.style.opacity,
            },
            "z_index": element.z_index,
            "group_id": str(element.group_id) if element.group_id else None,
            "created_at": element.created_at.isoformat(),
        }

        if isinstance(element, Stroke):
            base["points"] = [
                {
                    "x": p.x,
                    "y": p.y,
                    "pressure": p.pressure,
                    "timestamp": p.timestamp,
                }
                for p in element.points
            ]
            base["smoothing"] = element.smoothing

        elif isinstance(element, Shape):
            base["shape_type"] = element.shape_type.value
            base["width"] = element.width
            base["height"] = element.height
            base["rotation"] = element.rotation

        elif isinstance(element, Text):
            base["content"] = element.content
            base["font_size"] = element.font_size
            base["font_family"] = element.font_family

        elif isinstance(element, Group):
            base["name"] = element.name
            base["children"] = [str(child_id) for child_id in element.children]
            base["locked"] = element.locked
            base["collapsed"] = element.collapsed

        return base

    def _element_to_svg(self, element: Element) -> str | None:
        """Convert an element to SVG markup."""
        if isinstance(element, Stroke):
            return self._stroke_to_svg(element)
        if isinstance(element, Shape):
            return self._shape_to_svg(element)
        if isinstance(element, Text):
            return self._text_to_svg(element)
        if isinstance(element, Group):
            # Groups don't have visual representation themselves
            return None
        return None

    def _stroke_to_svg(self, stroke: Stroke) -> str:
        """Convert a stroke to SVG path."""
        if not stroke.points:
            return ""

        # Build path data
        path_parts = []
        for i, point in enumerate(stroke.points):
            if i == 0:
                path_parts.append(f"M {point.x} {point.y}")
            else:
                path_parts.append(f"L {point.x} {point.y}")

        path_data = " ".join(path_parts)

        style = stroke.style
        stroke_color = style.stroke_color or "#000000"
        stroke_width = style.stroke_width

        return (
            f'  <path d="{path_data}" '
            f'stroke="{stroke_color}" '
            f'stroke-width="{stroke_width}" '
            f'fill="none" '
            f'stroke-linecap="round" '
            f'stroke-linejoin="round" '
            f'opacity="{style.opacity}"/>'
        )

    def _shape_to_svg(self, shape: Shape) -> str:
        """Convert a shape to SVG element."""
        style = shape.style
        fill = style.fill_color or "none"
        stroke = style.stroke_color or "#000000"
        stroke_width = style.stroke_width
        opacity = style.opacity

        x = shape.position.x
        y = shape.position.y
        width = shape.width
        height = shape.height

        # Build transform if rotated
        transform = ""
        if shape.rotation != 0:
            cx = x + width / 2
            cy = y + height / 2
            transform = f' transform="rotate({shape.rotation} {cx} {cy})"'

        common_attrs = f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" opacity="{opacity}"{transform}'

        if shape.shape_type == ShapeType.RECTANGLE:
            return f'  <rect x="{x}" y="{y}" width="{width}" height="{height}" {common_attrs}/>'

        if shape.shape_type == ShapeType.ELLIPSE:
            cx = x + width / 2
            cy = y + height / 2
            rx = width / 2
            ry = height / 2
            return f'  <ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" {common_attrs}/>'

        if shape.shape_type == ShapeType.LINE:
            x2 = x + width
            y2 = y + height
            return f'  <line x1="{x}" y1="{y}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{stroke_width}" opacity="{opacity}"{transform}/>'

        if shape.shape_type == ShapeType.TRIANGLE:
            # Equilateral-ish triangle
            p1 = f"{x + width / 2},{y}"
            p2 = f"{x},{y + height}"
            p3 = f"{x + width},{y + height}"
            return f'  <polygon points="{p1} {p2} {p3}" {common_attrs}/>'

        if shape.shape_type == ShapeType.ARROW:
            # Arrow pointing right
            mid_y = y + height / 2
            arrow_head = width * 0.3
            return (
                f"  <g {common_attrs}>"
                f'<line x1="{x}" y1="{mid_y}" x2="{x + width - arrow_head}" y2="{mid_y}" '
                f'stroke="{stroke}" stroke-width="{stroke_width}"/>'
                f'<polygon points="{x + width},{mid_y} {x + width - arrow_head},{y} {x + width - arrow_head},{y + height}" '
                f'fill="{stroke}"/>'
                f"</g>"
            )

        # Fallback to rectangle
        return f'  <rect x="{x}" y="{y}" width="{width}" height="{height}" {common_attrs}/>'

    def _text_to_svg(self, text: Text) -> str:
        """Convert a text element to SVG."""
        style = text.style
        fill = style.stroke_color or "#000000"
        opacity = style.opacity

        # Escape special XML characters
        content = self._escape_xml(text.content)

        return (
            f'  <text x="{text.position.x}" y="{text.position.y}" '
            f'font-family="{text.font_family}" '
            f'font-size="{text.font_size}" '
            f'fill="{fill}" '
            f'opacity="{opacity}">'
            f"{content}</text>"
        )

    def _escape_xml(self, text: str) -> str:
        """Escape special XML characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for special types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        if hasattr(obj, "value"):  # Enum
            return obj.value
        msg = f"Object of type {type(obj)} is not JSON serializable"
        raise TypeError(msg)
