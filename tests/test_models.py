"""Tests for core domain models."""

from __future__ import annotations

from uuid import UUID

from scribbl_py.core.models import Canvas, Point, Shape, Stroke, Text
from scribbl_py.core.style import ElementStyle
from scribbl_py.core.types import ElementType, ShapeType


class TestPoint:
    """Tests for the Point model."""

    def test_create_point(self) -> None:
        """Test creating a basic point."""
        point = Point(x=10.0, y=20.0)
        assert point.x == 10.0
        assert point.y == 20.0
        assert point.pressure == 1.0  # default

    def test_point_with_pressure(self) -> None:
        """Test creating a point with custom pressure."""
        point = Point(x=0, y=0, pressure=0.5)
        assert point.pressure == 0.5

    def test_point_with_timestamp(self) -> None:
        """Test creating a point with timestamp."""
        timestamp = 1234567890.0
        point = Point(x=5.0, y=10.0, pressure=0.8, timestamp=timestamp)
        assert point.timestamp == timestamp

    def test_point_with_negative_coords(self) -> None:
        """Test creating a point with negative coordinates."""
        point = Point(x=-10.5, y=-20.3)
        assert point.x == -10.5
        assert point.y == -20.3

    def test_point_zero_pressure(self) -> None:
        """Test creating a point with zero pressure."""
        point = Point(x=0, y=0, pressure=0.0)
        assert point.pressure == 0.0


class TestElementStyle:
    """Tests for the ElementStyle model."""

    def test_default_style(self) -> None:
        """Test default style values."""
        style = ElementStyle()
        assert style.stroke_color == "#000000"
        assert style.fill_color is None
        assert style.stroke_width == 2.0
        assert style.opacity == 1.0

    def test_custom_style(self) -> None:
        """Test creating a custom style."""
        style = ElementStyle(
            stroke_color="#ff0000",
            fill_color="#00ff00",
            stroke_width=5.0,
            opacity=0.5,
        )
        assert style.stroke_color == "#ff0000"
        assert style.fill_color == "#00ff00"
        assert style.stroke_width == 5.0
        assert style.opacity == 0.5

    def test_style_with_only_stroke(self) -> None:
        """Test creating a style with only stroke color."""
        style = ElementStyle(stroke_color="#0000ff")
        assert style.stroke_color == "#0000ff"
        assert style.fill_color is None

    def test_style_with_partial_opacity(self) -> None:
        """Test creating a style with partial opacity."""
        style = ElementStyle(opacity=0.75)
        assert style.opacity == 0.75


class TestStroke:
    """Tests for the Stroke element model."""

    def test_create_stroke(self) -> None:
        """Test creating a basic stroke."""
        points = [Point(x=0, y=0), Point(x=10, y=10)]
        stroke = Stroke(position=Point(x=0, y=0), points=points)
        assert stroke.element_type == ElementType.STROKE
        assert len(stroke.points) == 2
        assert isinstance(stroke.id, UUID)

    def test_stroke_default_smoothing(self) -> None:
        """Test stroke with default smoothing value."""
        stroke = Stroke(position=Point(x=0, y=0), points=[])
        assert stroke.smoothing == 0.5

    def test_stroke_custom_smoothing(self) -> None:
        """Test stroke with custom smoothing value."""
        stroke = Stroke(
            position=Point(x=0, y=0),
            points=[Point(x=1, y=1)],
            smoothing=0.8,
        )
        assert stroke.smoothing == 0.8

    def test_stroke_with_style(self) -> None:
        """Test creating a stroke with custom style."""
        style = ElementStyle(stroke_color="#ff0000", stroke_width=3.0)
        stroke = Stroke(
            position=Point(x=5, y=5),
            points=[Point(x=5, y=5), Point(x=15, y=15)],
            style=style,
        )
        assert stroke.style.stroke_color == "#ff0000"
        assert stroke.style.stroke_width == 3.0

    def test_stroke_empty_points(self) -> None:
        """Test creating a stroke with no points."""
        stroke = Stroke(position=Point(x=0, y=0), points=[])
        assert len(stroke.points) == 0

    def test_stroke_many_points(self) -> None:
        """Test creating a stroke with many points."""
        points = [Point(x=i, y=i) for i in range(100)]
        stroke = Stroke(position=Point(x=0, y=0), points=points)
        assert len(stroke.points) == 100

    def test_stroke_created_at(self) -> None:
        """Test that stroke has created_at timestamp."""
        stroke = Stroke(position=Point(x=0, y=0), points=[])
        assert stroke.created_at is not None


class TestShape:
    """Tests for the Shape element model."""

    def test_create_rectangle(self) -> None:
        """Test creating a rectangle shape."""
        shape = Shape(
            shape_type=ShapeType.RECTANGLE,
            position=Point(x=0, y=0),
            width=100.0,
            height=50.0,
        )
        assert shape.element_type == ElementType.SHAPE
        assert shape.shape_type == ShapeType.RECTANGLE
        assert shape.width == 100.0
        assert shape.height == 50.0

    def test_create_ellipse(self) -> None:
        """Test creating an ellipse shape."""
        shape = Shape(
            shape_type=ShapeType.ELLIPSE,
            position=Point(x=50, y=50),
            width=80.0,
            height=80.0,
        )
        assert shape.shape_type == ShapeType.ELLIPSE

    def test_create_line(self) -> None:
        """Test creating a line shape."""
        shape = Shape(
            shape_type=ShapeType.LINE,
            position=Point(x=0, y=0),
            width=100.0,
            height=0.0,
        )
        assert shape.shape_type == ShapeType.LINE

    def test_create_arrow(self) -> None:
        """Test creating an arrow shape."""
        shape = Shape(
            shape_type=ShapeType.ARROW,
            position=Point(x=10, y=10),
            width=50.0,
            height=20.0,
        )
        assert shape.shape_type == ShapeType.ARROW

    def test_create_triangle(self) -> None:
        """Test creating a triangle shape."""
        shape = Shape(
            shape_type=ShapeType.TRIANGLE,
            position=Point(x=25, y=25),
            width=40.0,
            height=60.0,
        )
        assert shape.shape_type == ShapeType.TRIANGLE

    def test_shape_default_rotation(self) -> None:
        """Test shape with default rotation value."""
        shape = Shape(
            shape_type=ShapeType.RECTANGLE,
            position=Point(x=0, y=0),
            width=10.0,
            height=10.0,
        )
        assert shape.rotation == 0.0

    def test_shape_custom_rotation(self) -> None:
        """Test shape with custom rotation."""
        shape = Shape(
            shape_type=ShapeType.RECTANGLE,
            position=Point(x=0, y=0),
            width=10.0,
            height=10.0,
            rotation=45.0,
        )
        assert shape.rotation == 45.0

    def test_shape_with_style(self) -> None:
        """Test creating a shape with custom style."""
        style = ElementStyle(
            stroke_color="#0000ff",
            fill_color="#ffff00",
            stroke_width=2.5,
        )
        shape = Shape(
            shape_type=ShapeType.ELLIPSE,
            position=Point(x=20, y=20),
            width=60.0,
            height=40.0,
            style=style,
        )
        assert shape.style.stroke_color == "#0000ff"
        assert shape.style.fill_color == "#ffff00"

    def test_shape_unique_id(self) -> None:
        """Test that each shape gets a unique ID."""
        shape1 = Shape(
            shape_type=ShapeType.RECTANGLE,
            position=Point(x=0, y=0),
            width=10.0,
            height=10.0,
        )
        shape2 = Shape(
            shape_type=ShapeType.RECTANGLE,
            position=Point(x=0, y=0),
            width=10.0,
            height=10.0,
        )
        assert shape1.id != shape2.id


class TestText:
    """Tests for the Text element model."""

    def test_create_text(self) -> None:
        """Test creating a text element."""
        text = Text(
            content="Hello",
            position=Point(x=10, y=20),
        )
        assert text.element_type == ElementType.TEXT
        assert text.content == "Hello"
        assert text.position.x == 10
        assert text.position.y == 20

    def test_text_default_font_size(self) -> None:
        """Test text with default font size."""
        text = Text(content="Test", position=Point(x=0, y=0))
        assert text.font_size == 16

    def test_text_custom_font_size(self) -> None:
        """Test text with custom font size."""
        text = Text(
            content="Large Text",
            position=Point(x=0, y=0),
            font_size=32,
        )
        assert text.font_size == 32

    def test_text_default_font_family(self) -> None:
        """Test text with default font family."""
        text = Text(content="Test", position=Point(x=0, y=0))
        assert text.font_family == "sans-serif"

    def test_text_custom_font_family(self) -> None:
        """Test text with custom font family."""
        text = Text(
            content="Fancy Text",
            position=Point(x=0, y=0),
            font_family="Arial",
        )
        assert text.font_family == "Arial"

    def test_text_empty_content(self) -> None:
        """Test creating text with empty content."""
        text = Text(content="", position=Point(x=0, y=0))
        assert text.content == ""

    def test_text_multiline_content(self) -> None:
        """Test creating text with multiline content."""
        content = "Line 1\nLine 2\nLine 3"
        text = Text(content=content, position=Point(x=0, y=0))
        assert text.content == content

    def test_text_with_style(self) -> None:
        """Test creating text with custom style."""
        style = ElementStyle(stroke_color="#00ff00")
        text = Text(
            content="Styled Text",
            position=Point(x=5, y=10),
            style=style,
        )
        assert text.style.stroke_color == "#00ff00"

    def test_text_unique_id(self) -> None:
        """Test that each text element gets a unique ID."""
        text1 = Text(content="Text 1", position=Point(x=0, y=0))
        text2 = Text(content="Text 2", position=Point(x=0, y=0))
        assert text1.id != text2.id


class TestCanvas:
    """Tests for the Canvas model."""

    def test_create_canvas(self) -> None:
        """Test creating a basic canvas."""
        canvas = Canvas(name="Test Canvas")
        assert canvas.name == "Test Canvas"
        assert canvas.width == 1920
        assert canvas.height == 1080
        assert len(canvas.elements) == 0

    def test_canvas_default_name(self) -> None:
        """Test canvas with default name."""
        canvas = Canvas()
        assert canvas.name == "Untitled Canvas"

    def test_canvas_default_dimensions(self) -> None:
        """Test canvas with default dimensions."""
        canvas = Canvas(name="Test")
        assert canvas.width == 1920
        assert canvas.height == 1080

    def test_canvas_custom_dimensions(self) -> None:
        """Test canvas with custom dimensions."""
        canvas = Canvas(name="Custom", width=800, height=600)
        assert canvas.width == 800
        assert canvas.height == 600

    def test_canvas_default_background(self) -> None:
        """Test canvas with default background color."""
        canvas = Canvas(name="Test")
        assert canvas.background_color == "#ffffff"

    def test_canvas_custom_background(self) -> None:
        """Test canvas with custom background color."""
        canvas = Canvas(name="Dark", background_color="#000000")
        assert canvas.background_color == "#000000"

    def test_canvas_unique_id(self) -> None:
        """Test that each canvas gets a unique ID."""
        canvas1 = Canvas(name="Canvas 1")
        canvas2 = Canvas(name="Canvas 2")
        assert canvas1.id != canvas2.id
        assert isinstance(canvas1.id, UUID)
        assert isinstance(canvas2.id, UUID)

    def test_canvas_timestamps(self) -> None:
        """Test that canvas has created_at and updated_at timestamps."""
        canvas = Canvas(name="Test")
        assert canvas.created_at is not None
        assert canvas.updated_at is not None

    def test_canvas_with_elements(self) -> None:
        """Test creating a canvas with elements."""
        stroke = Stroke(position=Point(x=0, y=0), points=[Point(x=0, y=0)])
        shape = Shape(
            shape_type=ShapeType.RECTANGLE,
            position=Point(x=10, y=10),
            width=50.0,
            height=30.0,
        )
        text = Text(content="Hello", position=Point(x=20, y=20))

        canvas = Canvas(name="Test", elements=[stroke, shape, text])
        assert len(canvas.elements) == 3
        assert isinstance(canvas.elements[0], Stroke)
        assert isinstance(canvas.elements[1], Shape)
        assert isinstance(canvas.elements[2], Text)

    def test_canvas_empty_elements_list(self) -> None:
        """Test that canvas starts with empty elements list."""
        canvas = Canvas(name="Empty")
        assert canvas.elements == []
        assert len(canvas.elements) == 0


class TestElementInheritance:
    """Tests for element inheritance and polymorphism."""

    def test_stroke_is_element(self) -> None:
        """Test that Stroke is an Element."""
        stroke = Stroke(position=Point(x=0, y=0), points=[])
        assert hasattr(stroke, "id")
        assert hasattr(stroke, "element_type")
        assert hasattr(stroke, "position")
        assert hasattr(stroke, "style")
        assert hasattr(stroke, "created_at")

    def test_shape_is_element(self) -> None:
        """Test that Shape is an Element."""
        shape = Shape(
            shape_type=ShapeType.RECTANGLE,
            position=Point(x=0, y=0),
            width=10.0,
            height=10.0,
        )
        assert hasattr(shape, "id")
        assert hasattr(shape, "element_type")
        assert hasattr(shape, "position")
        assert hasattr(shape, "style")
        assert hasattr(shape, "created_at")

    def test_text_is_element(self) -> None:
        """Test that Text is an Element."""
        text = Text(content="Test", position=Point(x=0, y=0))
        assert hasattr(text, "id")
        assert hasattr(text, "element_type")
        assert hasattr(text, "position")
        assert hasattr(text, "style")
        assert hasattr(text, "created_at")

    def test_element_types_are_distinct(self) -> None:
        """Test that different element types have correct type identifiers."""
        stroke = Stroke(position=Point(x=0, y=0), points=[])
        shape = Shape(
            shape_type=ShapeType.RECTANGLE,
            position=Point(x=0, y=0),
            width=10.0,
            height=10.0,
        )
        text = Text(content="Test", position=Point(x=0, y=0))

        assert stroke.element_type == ElementType.STROKE
        assert shape.element_type == ElementType.SHAPE
        assert text.element_type == ElementType.TEXT
        assert stroke.element_type != shape.element_type
        assert shape.element_type != text.element_type
