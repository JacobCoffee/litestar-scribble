"""Tests for the database storage layer.

These tests use an in-memory SQLite database for fast test execution.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from scribbl_py.core.exceptions import CanvasNotFoundError, ElementNotFoundError
from scribbl_py.core.models import Canvas, Point, Shape, Stroke, Text
from scribbl_py.core.style import ElementStyle
from scribbl_py.core.types import ShapeType

# Skip all tests in this module if db dependencies are not installed
pytest.importorskip("advanced_alchemy")
pytest.importorskip("sqlalchemy.ext.asyncio")

from scribbl_py.storage.db.models import CanvasModel, ElementModel
from scribbl_py.storage.db.storage import DatabaseStorage


@pytest.fixture
async def db_session() -> AsyncSession:
    """Create a test database session with in-memory SQLite."""
    # aiosqlite is needed for async SQLite
    pytest.importorskip("aiosqlite")

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Enable foreign key support for SQLite
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(CanvasModel.metadata.create_all)

    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def db_storage(db_session: AsyncSession) -> DatabaseStorage:
    """Create a DatabaseStorage instance with the test session."""
    return DatabaseStorage(session=db_session)


@pytest.fixture
def sample_canvas() -> Canvas:
    """Create a sample canvas for testing."""
    return Canvas(name="Test Canvas", width=800, height=600)


@pytest.fixture
def sample_stroke() -> Stroke:
    """Create a sample stroke for testing."""
    return Stroke(
        position=Point(x=0, y=0),
        points=[Point(x=0, y=0), Point(x=10, y=10), Point(x=20, y=5)],
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


@pytest.mark.db
class TestDatabaseStorageCanvas:
    """Tests for canvas operations in DatabaseStorage."""

    @pytest.mark.asyncio
    async def test_create_and_get_canvas(self, db_storage: DatabaseStorage, sample_canvas: Canvas) -> None:
        """Test creating and retrieving a canvas."""
        created = await db_storage.create_canvas(sample_canvas)
        assert created.name == "Test Canvas"
        assert created.id == sample_canvas.id

        retrieved = await db_storage.get_canvas(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name

    @pytest.mark.asyncio
    async def test_get_nonexistent_canvas(self, db_storage: DatabaseStorage) -> None:
        """Test retrieving a canvas that doesn't exist."""
        nonexistent_id = uuid4()
        result = await db_storage.get_canvas(nonexistent_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_list_canvases(self, db_storage: DatabaseStorage) -> None:
        """Test listing all canvases."""
        canvas1 = Canvas(name="Canvas 1")
        canvas2 = Canvas(name="Canvas 2")
        canvas3 = Canvas(name="Canvas 3")

        await db_storage.create_canvas(canvas1)
        await db_storage.create_canvas(canvas2)
        await db_storage.create_canvas(canvas3)

        canvases = await db_storage.list_canvases()
        assert len(canvases) == 3
        names = {c.name for c in canvases}
        assert names == {"Canvas 1", "Canvas 2", "Canvas 3"}

    @pytest.mark.asyncio
    async def test_list_canvases_empty(self, db_storage: DatabaseStorage) -> None:
        """Test listing canvases when none exist."""
        canvases = await db_storage.list_canvases()
        assert canvases == []

    @pytest.mark.asyncio
    async def test_update_canvas(self, db_storage: DatabaseStorage, sample_canvas: Canvas) -> None:
        """Test updating an existing canvas."""
        created = await db_storage.create_canvas(sample_canvas)
        original_created_at = created.created_at

        # Modify the canvas
        created.name = "Updated Name"
        created.background_color = "#ff0000"

        updated = await db_storage.update_canvas(created)
        assert updated.name == "Updated Name"
        assert updated.background_color == "#ff0000"
        assert updated.created_at == original_created_at

    @pytest.mark.asyncio
    async def test_update_nonexistent_canvas(self, db_storage: DatabaseStorage) -> None:
        """Test updating a canvas that doesn't exist."""
        canvas = Canvas(name="Nonexistent")
        canvas.id = uuid4()

        with pytest.raises(CanvasNotFoundError) as exc_info:
            await db_storage.update_canvas(canvas)

        assert str(canvas.id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_canvas(self, db_storage: DatabaseStorage, sample_canvas: Canvas) -> None:
        """Test deleting a canvas."""
        created = await db_storage.create_canvas(sample_canvas)
        deleted = await db_storage.delete_canvas(created.id)
        assert deleted is True

        retrieved = await db_storage.get_canvas(created.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_canvas(self, db_storage: DatabaseStorage) -> None:
        """Test deleting a canvas that doesn't exist."""
        nonexistent_id = uuid4()
        deleted = await db_storage.delete_canvas(nonexistent_id)
        assert deleted is False


@pytest.mark.db
class TestDatabaseStorageElements:
    """Tests for element operations in DatabaseStorage."""

    @pytest.mark.asyncio
    async def test_add_element(
        self,
        db_storage: DatabaseStorage,
        sample_canvas: Canvas,
        sample_stroke: Stroke,
    ) -> None:
        """Test adding an element to a canvas."""
        canvas = await db_storage.create_canvas(sample_canvas)
        added = await db_storage.add_element(canvas.id, sample_stroke)

        assert added.id == sample_stroke.id
        assert isinstance(added, Stroke)

        elements = await db_storage.list_elements(canvas.id)
        assert len(elements) == 1
        assert elements[0].id == sample_stroke.id

    @pytest.mark.asyncio
    async def test_add_element_to_nonexistent_canvas(self, db_storage: DatabaseStorage, sample_stroke: Stroke) -> None:
        """Test adding an element to a canvas that doesn't exist."""
        nonexistent_id = uuid4()

        with pytest.raises(CanvasNotFoundError) as exc_info:
            await db_storage.add_element(nonexistent_id, sample_stroke)

        assert str(nonexistent_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_multiple_element_types(
        self,
        db_storage: DatabaseStorage,
        sample_canvas: Canvas,
    ) -> None:
        """Test adding multiple element types to a canvas."""
        canvas = await db_storage.create_canvas(sample_canvas)

        stroke = Stroke(
            position=Point(x=0, y=0),
            points=[Point(x=0, y=0), Point(x=10, y=10)],
        )
        shape = Shape(
            shape_type=ShapeType.RECTANGLE,
            position=Point(x=50, y=50),
            width=100.0,
            height=75.0,
        )
        text = Text(content="Test Text", position=Point(x=100, y=100))

        await db_storage.add_element(canvas.id, stroke)
        await db_storage.add_element(canvas.id, shape)
        await db_storage.add_element(canvas.id, text)

        elements = await db_storage.list_elements(canvas.id)
        assert len(elements) == 3

        # Verify element types
        types = {type(e).__name__ for e in elements}
        assert types == {"Stroke", "Shape", "Text"}

    @pytest.mark.asyncio
    async def test_get_element(
        self,
        db_storage: DatabaseStorage,
        sample_canvas: Canvas,
        sample_stroke: Stroke,
    ) -> None:
        """Test retrieving a specific element from a canvas."""
        canvas = await db_storage.create_canvas(sample_canvas)
        added = await db_storage.add_element(canvas.id, sample_stroke)

        retrieved = await db_storage.get_element(canvas.id, added.id)
        assert retrieved is not None
        assert retrieved.id == added.id
        assert isinstance(retrieved, Stroke)

    @pytest.mark.asyncio
    async def test_get_nonexistent_element(self, db_storage: DatabaseStorage, sample_canvas: Canvas) -> None:
        """Test retrieving an element that doesn't exist."""
        canvas = await db_storage.create_canvas(sample_canvas)
        nonexistent_id = uuid4()

        result = await db_storage.get_element(canvas.id, nonexistent_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_element_from_nonexistent_canvas(self, db_storage: DatabaseStorage) -> None:
        """Test retrieving an element from a canvas that doesn't exist."""
        nonexistent_canvas_id = uuid4()
        element_id = uuid4()

        with pytest.raises(CanvasNotFoundError):
            await db_storage.get_element(nonexistent_canvas_id, element_id)

    @pytest.mark.asyncio
    async def test_update_element(
        self,
        db_storage: DatabaseStorage,
        sample_canvas: Canvas,
        sample_stroke: Stroke,
    ) -> None:
        """Test updating an element on a canvas."""
        canvas = await db_storage.create_canvas(sample_canvas)
        added = await db_storage.add_element(canvas.id, sample_stroke)

        # Modify the element
        new_style = ElementStyle(stroke_color="#ff0000", stroke_width=5.0)
        added.style = new_style

        updated = await db_storage.update_element(canvas.id, added)
        assert updated.style.stroke_color == "#ff0000"
        assert updated.style.stroke_width == 5.0

        # Verify the update persisted
        retrieved = await db_storage.get_element(canvas.id, added.id)
        assert retrieved is not None
        assert retrieved.style.stroke_color == "#ff0000"

    @pytest.mark.asyncio
    async def test_update_nonexistent_element(self, db_storage: DatabaseStorage, sample_canvas: Canvas) -> None:
        """Test updating an element that doesn't exist."""
        canvas = await db_storage.create_canvas(sample_canvas)
        stroke = Stroke(position=Point(x=0, y=0), points=[])

        with pytest.raises(ElementNotFoundError) as exc_info:
            await db_storage.update_element(canvas.id, stroke)

        assert str(stroke.id) in str(exc_info.value)
        assert str(canvas.id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_element_on_nonexistent_canvas(
        self, db_storage: DatabaseStorage, sample_stroke: Stroke
    ) -> None:
        """Test updating an element on a canvas that doesn't exist."""
        nonexistent_canvas_id = uuid4()

        with pytest.raises(CanvasNotFoundError):
            await db_storage.update_element(nonexistent_canvas_id, sample_stroke)

    @pytest.mark.asyncio
    async def test_delete_element(
        self,
        db_storage: DatabaseStorage,
        sample_canvas: Canvas,
        sample_stroke: Stroke,
    ) -> None:
        """Test deleting an element from a canvas."""
        canvas = await db_storage.create_canvas(sample_canvas)
        added = await db_storage.add_element(canvas.id, sample_stroke)

        deleted = await db_storage.delete_element(canvas.id, added.id)
        assert deleted is True

        elements = await db_storage.list_elements(canvas.id)
        assert len(elements) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_element(self, db_storage: DatabaseStorage, sample_canvas: Canvas) -> None:
        """Test deleting an element that doesn't exist."""
        canvas = await db_storage.create_canvas(sample_canvas)
        nonexistent_id = uuid4()

        deleted = await db_storage.delete_element(canvas.id, nonexistent_id)
        assert deleted is False

    @pytest.mark.asyncio
    async def test_delete_element_from_nonexistent_canvas(self, db_storage: DatabaseStorage) -> None:
        """Test deleting an element from a canvas that doesn't exist."""
        nonexistent_canvas_id = uuid4()
        element_id = uuid4()

        with pytest.raises(CanvasNotFoundError):
            await db_storage.delete_element(nonexistent_canvas_id, element_id)

    @pytest.mark.asyncio
    async def test_list_elements(self, db_storage: DatabaseStorage, sample_canvas: Canvas) -> None:
        """Test listing all elements on a canvas."""
        canvas = await db_storage.create_canvas(sample_canvas)

        stroke = Stroke(position=Point(x=0, y=0), points=[Point(x=0, y=0)])
        shape = Shape(
            shape_type=ShapeType.ELLIPSE,
            position=Point(x=10, y=10),
            width=50.0,
            height=50.0,
        )
        text = Text(content="Test", position=Point(x=20, y=20))

        await db_storage.add_element(canvas.id, stroke)
        await db_storage.add_element(canvas.id, shape)
        await db_storage.add_element(canvas.id, text)

        elements = await db_storage.list_elements(canvas.id)
        assert len(elements) == 3

    @pytest.mark.asyncio
    async def test_list_elements_empty_canvas(self, db_storage: DatabaseStorage, sample_canvas: Canvas) -> None:
        """Test listing elements on a canvas with no elements."""
        canvas = await db_storage.create_canvas(sample_canvas)
        elements = await db_storage.list_elements(canvas.id)
        assert elements == []

    @pytest.mark.asyncio
    async def test_list_elements_from_nonexistent_canvas(self, db_storage: DatabaseStorage) -> None:
        """Test listing elements from a canvas that doesn't exist."""
        nonexistent_id = uuid4()

        with pytest.raises(CanvasNotFoundError):
            await db_storage.list_elements(nonexistent_id)


@pytest.mark.db
class TestDatabaseStorageCascade:
    """Tests for cascade delete behavior."""

    @pytest.mark.asyncio
    async def test_delete_canvas_cascades_to_elements(
        self,
        db_storage: DatabaseStorage,
        db_session: AsyncSession,
        sample_canvas: Canvas,
        sample_stroke: Stroke,
    ) -> None:
        """Test that deleting a canvas also deletes its elements."""
        canvas = await db_storage.create_canvas(sample_canvas)
        await db_storage.add_element(canvas.id, sample_stroke)

        # Delete the canvas
        await db_storage.delete_canvas(canvas.id)
        await db_session.commit()

        # Verify elements are also deleted (query directly to bypass canvas check)
        from sqlalchemy import select

        stmt = select(ElementModel).where(ElementModel.canvas_id == canvas.id)
        result = await db_session.execute(stmt)
        assert result.scalars().first() is None


@pytest.mark.db
class TestDatabaseStorageModelConversion:
    """Tests for model conversion functions."""

    @pytest.mark.asyncio
    async def test_stroke_round_trip(
        self,
        db_storage: DatabaseStorage,
        sample_canvas: Canvas,
    ) -> None:
        """Test that a Stroke survives a round trip to/from the database."""
        canvas = await db_storage.create_canvas(sample_canvas)

        original = Stroke(
            position=Point(x=10, y=20, pressure=0.8),
            points=[
                Point(x=0, y=0, pressure=1.0, timestamp=1000.0),
                Point(x=10, y=10, pressure=0.9),
            ],
            smoothing=0.7,
            style=ElementStyle(
                stroke_color="#ff0000",
                fill_color="#00ff00",
                stroke_width=3.0,
                opacity=0.8,
            ),
        )

        await db_storage.add_element(canvas.id, original)
        retrieved = await db_storage.get_element(canvas.id, original.id)

        assert retrieved is not None
        assert isinstance(retrieved, Stroke)
        assert retrieved.position.x == 10
        assert retrieved.position.y == 20
        assert retrieved.position.pressure == 0.8
        assert len(retrieved.points) == 2
        assert retrieved.points[0].timestamp == 1000.0
        assert retrieved.smoothing == 0.7
        assert retrieved.style.stroke_color == "#ff0000"
        assert retrieved.style.fill_color == "#00ff00"

    @pytest.mark.asyncio
    async def test_shape_round_trip(
        self,
        db_storage: DatabaseStorage,
        sample_canvas: Canvas,
    ) -> None:
        """Test that a Shape survives a round trip to/from the database."""
        canvas = await db_storage.create_canvas(sample_canvas)

        original = Shape(
            position=Point(x=100, y=200),
            shape_type=ShapeType.ELLIPSE,
            width=150.0,
            height=75.0,
            rotation=45.0,
            style=ElementStyle(stroke_color="#0000ff", stroke_width=2.0),
        )

        await db_storage.add_element(canvas.id, original)
        retrieved = await db_storage.get_element(canvas.id, original.id)

        assert retrieved is not None
        assert isinstance(retrieved, Shape)
        assert retrieved.shape_type == ShapeType.ELLIPSE
        assert retrieved.width == 150.0
        assert retrieved.height == 75.0
        assert retrieved.rotation == 45.0

    @pytest.mark.asyncio
    async def test_text_round_trip(
        self,
        db_storage: DatabaseStorage,
        sample_canvas: Canvas,
    ) -> None:
        """Test that a Text element survives a round trip to/from the database."""
        canvas = await db_storage.create_canvas(sample_canvas)

        original = Text(
            position=Point(x=50, y=50),
            content="Hello, World!",
            font_size=24,
            font_family="monospace",
        )

        await db_storage.add_element(canvas.id, original)
        retrieved = await db_storage.get_element(canvas.id, original.id)

        assert retrieved is not None
        assert isinstance(retrieved, Text)
        assert retrieved.content == "Hello, World!"
        assert retrieved.font_size == 24
        assert retrieved.font_family == "monospace"
