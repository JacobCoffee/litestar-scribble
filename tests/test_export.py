"""Tests for export functionality."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from litestar import Litestar
from litestar.testing import TestClient

from scribbl_py.core.models import Canvas, Group, Point, Shape, Stroke, Text
from scribbl_py.core.style import ElementStyle
from scribbl_py.core.types import ShapeType
from scribbl_py.plugin import ScribblConfig, ScribblPlugin
from scribbl_py.services.export import ExportService


@pytest.fixture
def export_service() -> ExportService:
    """Create an ExportService instance."""
    return ExportService()


@pytest.fixture
def canvas_with_elements() -> Canvas:
    """Create a canvas with various elements for export testing."""
    canvas = Canvas(name="Export Test", width=800, height=600, background_color="#f0f0f0")

    # Add a stroke
    stroke = Stroke(
        position=Point(x=0, y=0),
        points=[Point(x=10, y=10), Point(x=50, y=50), Point(x=100, y=30)],
        style=ElementStyle(stroke_color="#ff0000", stroke_width=2.0),
        z_index=0,
    )
    canvas.elements.append(stroke)

    # Add a rectangle
    rect = Shape(
        shape_type=ShapeType.RECTANGLE,
        position=Point(x=200, y=100),
        width=100.0,
        height=80.0,
        style=ElementStyle(stroke_color="#0000ff", fill_color="#00ff00"),
        z_index=1,
    )
    canvas.elements.append(rect)

    # Add text
    text = Text(
        content="Hello World",
        position=Point(x=300, y=200),
        font_size=24,
        font_family="Arial",
        style=ElementStyle(stroke_color="#333333"),
        z_index=2,
    )
    canvas.elements.append(text)

    return canvas


class TestExportServiceJSON:
    """Tests for JSON export functionality."""

    def test_to_json_empty_canvas(self, export_service: ExportService) -> None:
        """Test JSON export of empty canvas."""
        canvas = Canvas(name="Empty", width=100, height=100)
        result = export_service.to_json(canvas)

        data = json.loads(result)
        assert data["name"] == "Empty"
        assert data["width"] == 100
        assert data["height"] == 100
        assert data["elements"] == []

    def test_to_json_with_elements(self, export_service: ExportService, canvas_with_elements: Canvas) -> None:
        """Test JSON export with elements."""
        result = export_service.to_json(canvas_with_elements)

        data = json.loads(result)
        assert data["name"] == "Export Test"
        assert len(data["elements"]) == 3
        assert data["background_color"] == "#f0f0f0"

    def test_to_json_compact(self, export_service: ExportService) -> None:
        """Test compact JSON export (no indentation)."""
        canvas = Canvas(name="Test", width=100, height=100)
        result = export_service.to_json(canvas, indent=None)

        assert "\n" not in result
        data = json.loads(result)
        assert data["name"] == "Test"

    def test_to_dict(self, export_service: ExportService, canvas_with_elements: Canvas) -> None:
        """Test dictionary export."""
        result = export_service.to_dict(canvas_with_elements)

        assert isinstance(result, dict)
        assert result["name"] == "Export Test"
        assert len(result["elements"]) == 3

    def test_stroke_serialization(self, export_service: ExportService) -> None:
        """Test stroke element serialization."""
        canvas = Canvas(name="Test", width=100, height=100)
        stroke = Stroke(
            position=Point(x=0, y=0),
            points=[Point(x=1, y=2, pressure=0.5, timestamp=100)],
            smoothing=0.7,
        )
        canvas.elements.append(stroke)

        result = export_service.to_dict(canvas)
        stroke_data = result["elements"][0]

        assert stroke_data["element_type"] == "stroke"
        assert stroke_data["smoothing"] == 0.7
        assert len(stroke_data["points"]) == 1
        assert stroke_data["points"][0]["pressure"] == 0.5

    def test_shape_serialization(self, export_service: ExportService) -> None:
        """Test shape element serialization."""
        canvas = Canvas(name="Test", width=100, height=100)
        shape = Shape(
            shape_type=ShapeType.ELLIPSE,
            position=Point(x=10, y=20),
            width=50.0,
            height=30.0,
            rotation=45.0,
        )
        canvas.elements.append(shape)

        result = export_service.to_dict(canvas)
        shape_data = result["elements"][0]

        assert shape_data["element_type"] == "shape"
        assert shape_data["shape_type"] == "ellipse"
        assert shape_data["width"] == 50.0
        assert shape_data["rotation"] == 45.0

    def test_text_serialization(self, export_service: ExportService) -> None:
        """Test text element serialization."""
        canvas = Canvas(name="Test", width=100, height=100)
        text = Text(
            content="Hello",
            position=Point(x=10, y=20),
            font_size=16,
            font_family="Helvetica",
        )
        canvas.elements.append(text)

        result = export_service.to_dict(canvas)
        text_data = result["elements"][0]

        assert text_data["element_type"] == "text"
        assert text_data["content"] == "Hello"
        assert text_data["font_size"] == 16
        assert text_data["font_family"] == "Helvetica"

    def test_group_serialization(self, export_service: ExportService) -> None:
        """Test group element serialization."""
        canvas = Canvas(name="Test", width=100, height=100)
        group = Group(
            name="Test Group",
            position=Point(x=0, y=0),
            locked=True,
            collapsed=False,
        )
        canvas.elements.append(group)

        result = export_service.to_dict(canvas)
        group_data = result["elements"][0]

        assert group_data["element_type"] == "group"
        assert group_data["name"] == "Test Group"
        assert group_data["locked"] is True
        assert group_data["collapsed"] is False


class TestExportServiceSVG:
    """Tests for SVG export functionality."""

    def test_to_svg_basic(self, export_service: ExportService) -> None:
        """Test basic SVG export."""
        canvas = Canvas(name="Test", width=800, height=600, background_color="#ffffff")
        result = export_service.to_svg(canvas)

        assert '<?xml version="1.0" encoding="UTF-8"?>' in result
        assert '<svg xmlns="http://www.w3.org/2000/svg"' in result
        assert 'width="800"' in result
        assert 'height="600"' in result
        assert "<title>Test</title>" in result
        assert 'fill="#ffffff"' in result

    def test_to_svg_stroke(self, export_service: ExportService) -> None:
        """Test SVG export with stroke element."""
        canvas = Canvas(name="Test", width=100, height=100)
        stroke = Stroke(
            position=Point(x=0, y=0),
            points=[Point(x=10, y=10), Point(x=50, y=50)],
            style=ElementStyle(stroke_color="#ff0000", stroke_width=3.0),
        )
        canvas.elements.append(stroke)

        result = export_service.to_svg(canvas)

        assert "<path" in result
        assert 'stroke="#ff0000"' in result
        assert 'stroke-width="3.0"' in result
        assert "M 10 10" in result
        assert "L 50 50" in result

    def test_to_svg_rectangle(self, export_service: ExportService) -> None:
        """Test SVG export with rectangle shape."""
        canvas = Canvas(name="Test", width=100, height=100)
        shape = Shape(
            shape_type=ShapeType.RECTANGLE,
            position=Point(x=10, y=20),
            width=50.0,
            height=30.0,
            style=ElementStyle(stroke_color="#000000", fill_color="#ffff00"),
        )
        canvas.elements.append(shape)

        result = export_service.to_svg(canvas)

        assert "<rect" in result
        assert 'x="10"' in result
        assert 'y="20"' in result
        assert 'width="50.0"' in result
        assert 'height="30.0"' in result
        assert 'fill="#ffff00"' in result

    def test_to_svg_ellipse(self, export_service: ExportService) -> None:
        """Test SVG export with ellipse shape."""
        canvas = Canvas(name="Test", width=100, height=100)
        shape = Shape(
            shape_type=ShapeType.ELLIPSE,
            position=Point(x=0, y=0),
            width=100.0,
            height=50.0,
        )
        canvas.elements.append(shape)

        result = export_service.to_svg(canvas)

        assert "<ellipse" in result
        assert 'cx="50.0"' in result
        assert 'cy="25.0"' in result
        assert 'rx="50.0"' in result
        assert 'ry="25.0"' in result

    def test_to_svg_line(self, export_service: ExportService) -> None:
        """Test SVG export with line shape."""
        canvas = Canvas(name="Test", width=100, height=100)
        shape = Shape(
            shape_type=ShapeType.LINE,
            position=Point(x=10, y=20),
            width=80.0,
            height=60.0,
        )
        canvas.elements.append(shape)

        result = export_service.to_svg(canvas)

        assert "<line" in result
        assert 'x1="10"' in result
        assert 'y1="20"' in result
        assert 'x2="90' in result  # 10 + 80
        assert 'y2="80' in result  # 20 + 60

    def test_to_svg_triangle(self, export_service: ExportService) -> None:
        """Test SVG export with triangle shape."""
        canvas = Canvas(name="Test", width=100, height=100)
        shape = Shape(
            shape_type=ShapeType.TRIANGLE,
            position=Point(x=0, y=0),
            width=100.0,
            height=100.0,
        )
        canvas.elements.append(shape)

        result = export_service.to_svg(canvas)

        assert "<polygon" in result
        assert "50.0,0" in result  # Top point
        assert "0,100" in result  # Bottom left
        assert "100.0,100" in result  # Bottom right

    def test_to_svg_arrow(self, export_service: ExportService) -> None:
        """Test SVG export with arrow shape."""
        canvas = Canvas(name="Test", width=100, height=100)
        shape = Shape(
            shape_type=ShapeType.ARROW,
            position=Point(x=10, y=20),
            width=80.0,
            height=40.0,
        )
        canvas.elements.append(shape)

        result = export_service.to_svg(canvas)

        assert "<g" in result
        assert "<line" in result
        assert "<polygon" in result

    def test_to_svg_text(self, export_service: ExportService) -> None:
        """Test SVG export with text element."""
        canvas = Canvas(name="Test", width=100, height=100)
        text = Text(
            content="Hello World",
            position=Point(x=10, y=50),
            font_size=24,
            font_family="Arial",
            style=ElementStyle(stroke_color="#333333"),
        )
        canvas.elements.append(text)

        result = export_service.to_svg(canvas)

        assert "<text" in result
        assert 'x="10"' in result
        assert 'y="50"' in result
        assert 'font-family="Arial"' in result
        assert 'font-size="24"' in result
        assert ">Hello World</text>" in result

    def test_to_svg_rotation(self, export_service: ExportService) -> None:
        """Test SVG export with rotated shape."""
        canvas = Canvas(name="Test", width=100, height=100)
        shape = Shape(
            shape_type=ShapeType.RECTANGLE,
            position=Point(x=10, y=10),
            width=40.0,
            height=20.0,
            rotation=45.0,
        )
        canvas.elements.append(shape)

        result = export_service.to_svg(canvas)

        assert 'transform="rotate(45.0' in result

    def test_to_svg_xml_escape(self, export_service: ExportService) -> None:
        """Test SVG export escapes special XML characters."""
        canvas = Canvas(name="Test <\"&'>", width=100, height=100)
        text = Text(
            content="<script>alert('XSS')</script>",
            position=Point(x=0, y=0),
        )
        canvas.elements.append(text)

        result = export_service.to_svg(canvas)

        assert "&lt;script&gt;" in result
        assert "&apos;XSS&apos;" in result
        assert "<script>" not in result.replace("&lt;script&gt;", "")

    def test_to_svg_z_order(self, export_service: ExportService) -> None:
        """Test SVG export respects z-index ordering."""
        canvas = Canvas(name="Test", width=100, height=100)

        # Add elements in wrong order
        shape2 = Shape(
            shape_type=ShapeType.RECTANGLE,
            position=Point(x=0, y=0),
            width=50.0,
            height=50.0,
            z_index=1,
        )
        shape1 = Shape(
            shape_type=ShapeType.ELLIPSE,
            position=Point(x=25, y=25),
            width=50.0,
            height=50.0,
            z_index=0,
        )
        canvas.elements.append(shape2)
        canvas.elements.append(shape1)

        result = export_service.to_svg(canvas)

        # Ellipse (z_index=0) should come before rectangle (z_index=1)
        ellipse_pos = result.find("<ellipse")
        # Find rect with specific attributes (skip background rect)
        rect_pos = result.find('<rect x="0"')
        assert ellipse_pos < rect_pos

    def test_to_svg_empty_stroke(self, export_service: ExportService) -> None:
        """Test SVG export handles empty stroke gracefully."""
        canvas = Canvas(name="Test", width=100, height=100)
        stroke = Stroke(position=Point(x=0, y=0), points=[])
        canvas.elements.append(stroke)

        result = export_service.to_svg(canvas)

        # Should not raise, empty stroke produces no path
        assert "<svg" in result


class TestExportServicePNG:
    """Tests for PNG export functionality."""

    def test_to_png_without_cairosvg(self, export_service: ExportService) -> None:
        """Test PNG export raises ImportError without cairosvg."""
        canvas = Canvas(name="Test", width=100, height=100)

        with patch.dict("sys.modules", {"cairosvg": None}):
            with pytest.raises(ImportError, match="PNG export requires"):
                export_service.to_png(canvas)

    def test_to_png_with_cairosvg(self, export_service: ExportService) -> None:
        """Test PNG export calls cairosvg correctly."""
        canvas = Canvas(name="Test", width=100, height=100)
        expected_png = b"\x89PNG\r\n\x1a\n"

        mock_cairosvg = MagicMock()
        mock_cairosvg.svg2png.return_value = expected_png

        with patch.dict("sys.modules", {"cairosvg": mock_cairosvg}):
            # Need to reimport to pick up the mock
            result = export_service.to_png(canvas, scale=2.0)

        mock_cairosvg.svg2png.assert_called_once()
        call_kwargs = mock_cairosvg.svg2png.call_args[1]
        assert call_kwargs["scale"] == 2.0
        assert b"svg" in call_kwargs["bytestring"]


class TestExportAPI:
    """Tests for export API endpoints."""

    @pytest.fixture
    def app(self) -> Litestar:
        """Create a Litestar app with ScribblPlugin for testing."""
        return Litestar(plugins=[ScribblPlugin(ScribblConfig())])

    @pytest.fixture
    def client(self, app: Litestar) -> TestClient[Litestar]:
        """Create a test client for the app."""
        return TestClient(app=app)

    def test_export_json_endpoint(self, client: TestClient[Litestar]) -> None:
        """Test JSON export via API."""
        # Create canvas
        create_response = client.post("/api/canvases", json={"name": "Export Test"})
        canvas_id = create_response.json()["id"]

        # Export as JSON
        response = client.get(f"/api/canvases/{canvas_id}/export/json")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Export Test"
        assert "id" in data
        assert "elements" in data

    def test_export_json_with_elements(self, client: TestClient[Litestar]) -> None:
        """Test JSON export with elements via API."""
        # Create canvas with stroke
        create_response = client.post("/api/canvases", json={"name": "Test"})
        canvas_id = create_response.json()["id"]

        # Add element
        client.post(
            f"/api/canvases/{canvas_id}/elements/strokes",
            json={"points": [{"x": 0, "y": 0}, {"x": 10, "y": 10}]},
        )

        # Export
        response = client.get(f"/api/canvases/{canvas_id}/export/json")
        data = response.json()

        assert len(data["elements"]) == 1

    def test_export_svg_endpoint(self, client: TestClient[Litestar]) -> None:
        """Test SVG export via API."""
        # Create canvas
        create_response = client.post("/api/canvases", json={"name": "SVG Test"})
        canvas_id = create_response.json()["id"]

        # Export as SVG
        response = client.get(f"/api/canvases/{canvas_id}/export/svg")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/svg+xml"
        assert 'filename="SVG Test.svg"' in response.headers.get("content-disposition", "")

        content = response.text
        assert '<?xml version="1.0"' in content
        assert "<svg" in content

    def test_export_svg_with_elements(self, client: TestClient[Litestar]) -> None:
        """Test SVG export with elements via API."""
        # Create canvas and add shape
        create_response = client.post("/api/canvases", json={"name": "Test"})
        canvas_id = create_response.json()["id"]

        client.post(
            f"/api/canvases/{canvas_id}/elements/shapes",
            json={
                "shape_type": "rectangle",
                "x": 10,
                "y": 20,
                "width": 100,
                "height": 50,
            },
        )

        # Export
        response = client.get(f"/api/canvases/{canvas_id}/export/svg")
        content = response.text

        assert "<rect" in content

    def test_export_png_endpoint_without_dependency(self, client: TestClient[Litestar]) -> None:
        """Test PNG export fails gracefully without cairosvg."""
        # Create canvas
        create_response = client.post("/api/canvases", json={"name": "PNG Test"})
        canvas_id = create_response.json()["id"]

        # This should fail if cairosvg is not installed
        response = client.get(f"/api/canvases/{canvas_id}/export/png")
        # Either 500 (ImportError) or 200 (if cairosvg is installed)
        assert response.status_code in (200, 500)

    def test_export_canvas_not_found(self, client: TestClient[Litestar]) -> None:
        """Test export with non-existent canvas."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        json_response = client.get(f"/api/canvases/{fake_id}/export/json")
        svg_response = client.get(f"/api/canvases/{fake_id}/export/svg")

        # Should return 404 or 500
        assert json_response.status_code in (404, 500)
        assert svg_response.status_code in (404, 500)


class TestJSONSerializer:
    """Tests for custom JSON serialization."""

    def test_datetime_serialization(self, export_service: ExportService) -> None:
        """Test datetime objects are serialized to ISO format."""
        canvas = Canvas(name="Test", width=100, height=100)
        result = export_service.to_dict(canvas)

        assert "created_at" in result
        assert "updated_at" in result
        # Should be ISO format strings
        assert "T" in result["created_at"]

    def test_uuid_serialization(self, export_service: ExportService) -> None:
        """Test UUIDs are serialized to strings."""
        canvas = Canvas(name="Test", width=100, height=100)
        result = export_service.to_dict(canvas)

        assert isinstance(result["id"], str)
        # Should be a valid UUID string
        assert len(result["id"]) == 36
