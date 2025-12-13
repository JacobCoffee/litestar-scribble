"""Pytest configuration and fixtures for scribbl-py tests."""

from __future__ import annotations

import pytest
from litestar import Litestar
from litestar.testing import TestClient

from scribbl_py.core.models import Canvas, Point, Shape, Stroke, Text
from scribbl_py.core.style import ElementStyle
from scribbl_py.core.types import ShapeType
from scribbl_py.plugin import ScribblConfig, ScribblPlugin
from scribbl_py.storage.memory import InMemoryStorage


@pytest.fixture
def anyio_backend() -> str:
    """Use asyncio as the async backend."""
    return "asyncio"


# Storage fixtures


@pytest.fixture
def storage() -> InMemoryStorage:
    """Create a fresh InMemoryStorage instance for each test."""
    return InMemoryStorage()


# Model fixtures


@pytest.fixture
def sample_canvas() -> Canvas:
    """Create a sample canvas for testing."""
    return Canvas(name="Test Canvas", width=800, height=600)


@pytest.fixture
def sample_point() -> Point:
    """Create a sample point for testing."""
    return Point(x=10.0, y=20.0, pressure=1.0)


@pytest.fixture
def sample_stroke() -> Stroke:
    """Create a sample stroke for testing."""
    return Stroke(
        position=Point(x=0, y=0),
        points=[Point(x=0, y=0), Point(x=10, y=10), Point(x=20, y=5)],
        smoothing=0.5,
    )


@pytest.fixture
def sample_shape() -> Shape:
    """Create a sample shape for testing."""
    return Shape(
        shape_type=ShapeType.RECTANGLE,
        position=Point(x=50, y=50),
        width=100.0,
        height=75.0,
    )


@pytest.fixture
def sample_text() -> Text:
    """Create a sample text element for testing."""
    return Text(
        content="Test Text",
        position=Point(x=100, y=100),
        font_size=16,
        font_family="sans-serif",
    )


@pytest.fixture
def sample_style() -> ElementStyle:
    """Create a sample element style for testing."""
    return ElementStyle(
        stroke_color="#ff0000",
        fill_color="#00ff00",
        stroke_width=3.0,
        opacity=0.8,
    )


# App and client fixtures


@pytest.fixture
def app() -> Litestar:
    """Create a Litestar app with ScribblPlugin for testing."""
    return Litestar(plugins=[ScribblPlugin(ScribblConfig())])


@pytest.fixture
def client(app: Litestar) -> TestClient[Litestar]:
    """Create a test client for the app."""
    return TestClient(app=app)
