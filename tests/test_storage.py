"""Tests for the storage layer."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from scribbl_py.core.exceptions import CanvasNotFoundError, ElementNotFoundError
from scribbl_py.core.models import Canvas, Point, Shape, Stroke, Text
from scribbl_py.core.style import ElementStyle
from scribbl_py.core.types import ShapeType
from scribbl_py.storage.memory import InMemoryStorage


@pytest.fixture
def storage() -> InMemoryStorage:
    """Create a fresh InMemoryStorage instance for each test."""
    return InMemoryStorage()


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


class TestInMemoryStorageCanvas:
    """Tests for canvas operations in InMemoryStorage."""

    @pytest.mark.asyncio
    async def test_create_and_get_canvas(self, storage: InMemoryStorage, sample_canvas: Canvas) -> None:
        """Test creating and retrieving a canvas."""
        created = await storage.create_canvas(sample_canvas)
        assert created.name == "Test Canvas"
        assert created.id == sample_canvas.id

        retrieved = await storage.get_canvas(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name

    @pytest.mark.asyncio
    async def test_get_nonexistent_canvas(self, storage: InMemoryStorage) -> None:
        """Test retrieving a canvas that doesn't exist."""
        nonexistent_id = uuid4()
        result = await storage.get_canvas(nonexistent_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_list_canvases(self, storage: InMemoryStorage) -> None:
        """Test listing all canvases."""
        canvas1 = Canvas(name="Canvas 1")
        canvas2 = Canvas(name="Canvas 2")
        canvas3 = Canvas(name="Canvas 3")

        await storage.create_canvas(canvas1)
        await storage.create_canvas(canvas2)
        await storage.create_canvas(canvas3)

        canvases = await storage.list_canvases()
        assert len(canvases) == 3
        names = {c.name for c in canvases}
        assert names == {"Canvas 1", "Canvas 2", "Canvas 3"}

    @pytest.mark.asyncio
    async def test_list_canvases_empty(self, storage: InMemoryStorage) -> None:
        """Test listing canvases when none exist."""
        canvases = await storage.list_canvases()
        assert canvases == []

    @pytest.mark.asyncio
    async def test_list_canvases_ordered_by_creation(self, storage: InMemoryStorage) -> None:
        """Test that list_canvases returns canvases ordered by creation date (newest first)."""

        canvas1 = Canvas(name="First")
        await storage.create_canvas(canvas1)
        await asyncio.sleep(0.01)  # Small delay to ensure different timestamps

        canvas2 = Canvas(name="Second")
        await storage.create_canvas(canvas2)
        await asyncio.sleep(0.01)

        canvas3 = Canvas(name="Third")
        await storage.create_canvas(canvas3)

        canvases = await storage.list_canvases()
        assert len(canvases) == 3
        # Newest first
        assert canvases[0].name == "Third"
        assert canvases[1].name == "Second"
        assert canvases[2].name == "First"

    @pytest.mark.asyncio
    async def test_update_canvas(self, storage: InMemoryStorage, sample_canvas: Canvas) -> None:
        """Test updating an existing canvas."""
        created = await storage.create_canvas(sample_canvas)
        original_created_at = created.created_at

        # Modify the canvas
        created.name = "Updated Name"
        created.background_color = "#ff0000"

        updated = await storage.update_canvas(created)
        assert updated.name == "Updated Name"
        assert updated.background_color == "#ff0000"
        assert updated.created_at == original_created_at
        assert updated.updated_at > original_created_at

    @pytest.mark.asyncio
    async def test_update_nonexistent_canvas(self, storage: InMemoryStorage) -> None:
        """Test updating a canvas that doesn't exist."""
        canvas = Canvas(name="Nonexistent")
        canvas.id = uuid4()  # Ensure it doesn't exist

        with pytest.raises(CanvasNotFoundError) as exc_info:
            await storage.update_canvas(canvas)

        assert str(canvas.id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_canvas(self, storage: InMemoryStorage, sample_canvas: Canvas) -> None:
        """Test deleting a canvas."""
        created = await storage.create_canvas(sample_canvas)
        deleted = await storage.delete_canvas(created.id)
        assert deleted is True

        retrieved = await storage.get_canvas(created.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_canvas(self, storage: InMemoryStorage) -> None:
        """Test deleting a canvas that doesn't exist."""
        nonexistent_id = uuid4()
        deleted = await storage.delete_canvas(nonexistent_id)
        assert deleted is False

    @pytest.mark.asyncio
    async def test_canvas_isolation(self, storage: InMemoryStorage) -> None:
        """Test that returned canvases are isolated from internal storage."""
        canvas = Canvas(name="Original")
        created = await storage.create_canvas(canvas)

        # Modify the returned object
        created.name = "Modified"

        # Retrieve again and verify it wasn't affected
        retrieved = await storage.get_canvas(created.id)
        assert retrieved is not None
        assert retrieved.name == "Original"


class TestInMemoryStorageElements:
    """Tests for element operations in InMemoryStorage."""

    @pytest.mark.asyncio
    async def test_add_element(
        self,
        storage: InMemoryStorage,
        sample_canvas: Canvas,
        sample_stroke: Stroke,
    ) -> None:
        """Test adding an element to a canvas."""
        canvas = await storage.create_canvas(sample_canvas)
        added = await storage.add_element(canvas.id, sample_stroke)

        assert added.id == sample_stroke.id
        assert isinstance(added, Stroke)

        elements = await storage.list_elements(canvas.id)
        assert len(elements) == 1
        assert elements[0].id == sample_stroke.id

    @pytest.mark.asyncio
    async def test_add_element_to_nonexistent_canvas(self, storage: InMemoryStorage, sample_stroke: Stroke) -> None:
        """Test adding an element to a canvas that doesn't exist."""
        nonexistent_id = uuid4()

        with pytest.raises(CanvasNotFoundError) as exc_info:
            await storage.add_element(nonexistent_id, sample_stroke)

        assert str(nonexistent_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_multiple_elements(
        self,
        storage: InMemoryStorage,
        sample_canvas: Canvas,
        sample_stroke: Stroke,
        sample_shape: Shape,
    ) -> None:
        """Test adding multiple elements to a canvas."""
        canvas = await storage.create_canvas(sample_canvas)

        await storage.add_element(canvas.id, sample_stroke)
        await storage.add_element(canvas.id, sample_shape)

        text = Text(content="Test Text", position=Point(x=100, y=100))
        await storage.add_element(canvas.id, text)

        elements = await storage.list_elements(canvas.id)
        assert len(elements) == 3

    @pytest.mark.asyncio
    async def test_get_element(
        self,
        storage: InMemoryStorage,
        sample_canvas: Canvas,
        sample_stroke: Stroke,
    ) -> None:
        """Test retrieving a specific element from a canvas."""
        canvas = await storage.create_canvas(sample_canvas)
        added = await storage.add_element(canvas.id, sample_stroke)

        retrieved = await storage.get_element(canvas.id, added.id)
        assert retrieved is not None
        assert retrieved.id == added.id
        assert isinstance(retrieved, Stroke)

    @pytest.mark.asyncio
    async def test_get_nonexistent_element(self, storage: InMemoryStorage, sample_canvas: Canvas) -> None:
        """Test retrieving an element that doesn't exist."""
        canvas = await storage.create_canvas(sample_canvas)
        nonexistent_id = uuid4()

        result = await storage.get_element(canvas.id, nonexistent_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_element_from_nonexistent_canvas(self, storage: InMemoryStorage) -> None:
        """Test retrieving an element from a canvas that doesn't exist."""
        nonexistent_canvas_id = uuid4()
        element_id = uuid4()

        with pytest.raises(CanvasNotFoundError):
            await storage.get_element(nonexistent_canvas_id, element_id)

    @pytest.mark.asyncio
    async def test_update_element(
        self,
        storage: InMemoryStorage,
        sample_canvas: Canvas,
        sample_stroke: Stroke,
    ) -> None:
        """Test updating an element on a canvas."""
        canvas = await storage.create_canvas(sample_canvas)
        added = await storage.add_element(canvas.id, sample_stroke)

        # Modify the element
        new_style = ElementStyle(stroke_color="#ff0000", stroke_width=5.0)
        added.style = new_style

        updated = await storage.update_element(canvas.id, added)
        assert updated.style.stroke_color == "#ff0000"
        assert updated.style.stroke_width == 5.0

        # Verify the update persisted
        retrieved = await storage.get_element(canvas.id, added.id)
        assert retrieved is not None
        assert retrieved.style.stroke_color == "#ff0000"

    @pytest.mark.asyncio
    async def test_update_nonexistent_element(self, storage: InMemoryStorage, sample_canvas: Canvas) -> None:
        """Test updating an element that doesn't exist."""
        canvas = await storage.create_canvas(sample_canvas)
        stroke = Stroke(position=Point(x=0, y=0), points=[])

        with pytest.raises(ElementNotFoundError) as exc_info:
            await storage.update_element(canvas.id, stroke)

        assert str(stroke.id) in str(exc_info.value)
        assert str(canvas.id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_element_on_nonexistent_canvas(self, storage: InMemoryStorage, sample_stroke: Stroke) -> None:
        """Test updating an element on a canvas that doesn't exist."""
        nonexistent_canvas_id = uuid4()

        with pytest.raises(CanvasNotFoundError):
            await storage.update_element(nonexistent_canvas_id, sample_stroke)

    @pytest.mark.asyncio
    async def test_delete_element(
        self,
        storage: InMemoryStorage,
        sample_canvas: Canvas,
        sample_stroke: Stroke,
    ) -> None:
        """Test deleting an element from a canvas."""
        canvas = await storage.create_canvas(sample_canvas)
        added = await storage.add_element(canvas.id, sample_stroke)

        deleted = await storage.delete_element(canvas.id, added.id)
        assert deleted is True

        elements = await storage.list_elements(canvas.id)
        assert len(elements) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_element(self, storage: InMemoryStorage, sample_canvas: Canvas) -> None:
        """Test deleting an element that doesn't exist."""
        canvas = await storage.create_canvas(sample_canvas)
        nonexistent_id = uuid4()

        deleted = await storage.delete_element(canvas.id, nonexistent_id)
        assert deleted is False

    @pytest.mark.asyncio
    async def test_delete_element_from_nonexistent_canvas(self, storage: InMemoryStorage) -> None:
        """Test deleting an element from a canvas that doesn't exist."""
        nonexistent_canvas_id = uuid4()
        element_id = uuid4()

        with pytest.raises(CanvasNotFoundError):
            await storage.delete_element(nonexistent_canvas_id, element_id)

    @pytest.mark.asyncio
    async def test_list_elements(self, storage: InMemoryStorage, sample_canvas: Canvas) -> None:
        """Test listing all elements on a canvas."""
        canvas = await storage.create_canvas(sample_canvas)

        stroke = Stroke(position=Point(x=0, y=0), points=[Point(x=0, y=0)])
        shape = Shape(
            shape_type=ShapeType.ELLIPSE,
            position=Point(x=10, y=10),
            width=50.0,
            height=50.0,
        )
        text = Text(content="Test", position=Point(x=20, y=20))

        await storage.add_element(canvas.id, stroke)
        await storage.add_element(canvas.id, shape)
        await storage.add_element(canvas.id, text)

        elements = await storage.list_elements(canvas.id)
        assert len(elements) == 3

    @pytest.mark.asyncio
    async def test_list_elements_empty_canvas(self, storage: InMemoryStorage, sample_canvas: Canvas) -> None:
        """Test listing elements on a canvas with no elements."""
        canvas = await storage.create_canvas(sample_canvas)
        elements = await storage.list_elements(canvas.id)
        assert elements == []

    @pytest.mark.asyncio
    async def test_list_elements_from_nonexistent_canvas(self, storage: InMemoryStorage) -> None:
        """Test listing elements from a canvas that doesn't exist."""
        nonexistent_id = uuid4()

        with pytest.raises(CanvasNotFoundError):
            await storage.list_elements(nonexistent_id)

    @pytest.mark.asyncio
    async def test_element_isolation(
        self,
        storage: InMemoryStorage,
        sample_canvas: Canvas,
        sample_stroke: Stroke,
    ) -> None:
        """Test that returned elements are isolated from internal storage."""
        canvas = await storage.create_canvas(sample_canvas)
        added = await storage.add_element(canvas.id, sample_stroke)

        # Modify the returned element
        added.smoothing = 0.9

        # Retrieve again and verify it wasn't affected
        retrieved = await storage.get_element(canvas.id, added.id)
        assert retrieved is not None
        assert retrieved.smoothing == 0.5  # Original value


class TestInMemoryStorageUpdates:
    """Tests for canvas update tracking in InMemoryStorage."""

    @pytest.mark.asyncio
    async def test_canvas_updated_on_element_add(
        self,
        storage: InMemoryStorage,
        sample_canvas: Canvas,
        sample_stroke: Stroke,
    ) -> None:
        """Test that canvas updated_at changes when element is added."""
        canvas = await storage.create_canvas(sample_canvas)
        original_updated_at = canvas.updated_at

        await asyncio.sleep(0.01)  # Small delay

        await storage.add_element(canvas.id, sample_stroke)

        updated_canvas = await storage.get_canvas(canvas.id)
        assert updated_canvas is not None
        assert updated_canvas.updated_at > original_updated_at

    @pytest.mark.asyncio
    async def test_canvas_updated_on_element_delete(
        self,
        storage: InMemoryStorage,
        sample_canvas: Canvas,
        sample_stroke: Stroke,
    ) -> None:
        """Test that canvas updated_at changes when element is deleted."""
        canvas = await storage.create_canvas(sample_canvas)
        added = await storage.add_element(canvas.id, sample_stroke)

        updated_canvas = await storage.get_canvas(canvas.id)
        assert updated_canvas is not None
        original_updated_at = updated_canvas.updated_at

        await asyncio.sleep(0.01)  # Small delay

        await storage.delete_element(canvas.id, added.id)

        final_canvas = await storage.get_canvas(canvas.id)
        assert final_canvas is not None
        assert final_canvas.updated_at > original_updated_at

    @pytest.mark.asyncio
    async def test_canvas_updated_on_element_update(
        self,
        storage: InMemoryStorage,
        sample_canvas: Canvas,
        sample_stroke: Stroke,
    ) -> None:
        """Test that canvas updated_at changes when element is updated."""
        canvas = await storage.create_canvas(sample_canvas)
        added = await storage.add_element(canvas.id, sample_stroke)

        updated_canvas = await storage.get_canvas(canvas.id)
        assert updated_canvas is not None
        original_updated_at = updated_canvas.updated_at

        await asyncio.sleep(0.01)  # Small delay

        added.smoothing = 0.8
        await storage.update_element(canvas.id, added)

        final_canvas = await storage.get_canvas(canvas.id)
        assert final_canvas is not None
        assert final_canvas.updated_at > original_updated_at


class TestInMemoryStorageThreadSafety:
    """Tests for thread safety in InMemoryStorage."""

    @pytest.mark.asyncio
    async def test_concurrent_canvas_creation(self, storage: InMemoryStorage) -> None:
        """Test creating multiple canvases concurrently."""

        async def create_canvas(name: str) -> Canvas:
            canvas = Canvas(name=name)
            return await storage.create_canvas(canvas)

        tasks = [create_canvas(f"Canvas {i}") for i in range(10)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        canvases = await storage.list_canvases()
        assert len(canvases) == 10

    @pytest.mark.asyncio
    async def test_concurrent_element_addition(self, storage: InMemoryStorage, sample_canvas: Canvas) -> None:
        """Test adding elements to a canvas concurrently."""

        canvas = await storage.create_canvas(sample_canvas)

        async def add_stroke(index: int) -> Stroke:
            stroke = Stroke(
                position=Point(x=index, y=index),
                points=[Point(x=index, y=index)],
            )
            return await storage.add_element(canvas.id, stroke)

        tasks = [add_stroke(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 20
        elements = await storage.list_elements(canvas.id)
        assert len(elements) == 20
