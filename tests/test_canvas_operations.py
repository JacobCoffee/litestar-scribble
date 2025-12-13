"""Tests for Phase 5 canvas operations: undo/redo, z-ordering, grouping, copy/paste."""

from __future__ import annotations

from uuid import uuid4

import pytest

from scribbl_py.core.commands import (
    AddElementCommand,
    CommandHistory,
    CommandHistoryManager,
    DeleteElementCommand,
    GroupElementsCommand,
    MoveElementCommand,
    ReorderElementCommand,
    UngroupElementsCommand,
    UpdateElementCommand,
)
from scribbl_py.core.models import Canvas, Group, Point, Shape, Stroke
from scribbl_py.core.types import ElementType, ShapeType
from scribbl_py.exceptions import ElementNotFoundError
from scribbl_py.services.canvas import CanvasService
from scribbl_py.storage.memory import InMemoryStorage

# Fixtures


@pytest.fixture
def storage() -> InMemoryStorage:
    """Create a fresh InMemoryStorage instance for each test."""
    return InMemoryStorage()


@pytest.fixture
def service(storage: InMemoryStorage) -> CanvasService:
    """Create a canvas service with in-memory storage."""
    return CanvasService(storage)


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


# Command History Tests


class TestCommandHistory:
    """Tests for CommandHistory class."""

    def test_push_and_undo(self) -> None:
        """Test pushing a command and undoing it."""
        history = CommandHistory()
        canvas_id = uuid4()
        stroke = Stroke(position=Point(x=0, y=0), points=[])

        command = AddElementCommand(canvas_id=canvas_id, user_id="test", element=stroke)
        history.push(command)

        assert history.can_undo()
        assert not history.can_redo()
        assert history.undo_count == 1

        undone = history.undo()
        assert undone is command
        assert not history.can_undo()
        assert history.can_redo()
        assert history.redo_count == 1

    def test_redo(self) -> None:
        """Test redoing an undone command."""
        history = CommandHistory()
        canvas_id = uuid4()
        stroke = Stroke(position=Point(x=0, y=0), points=[])

        command = AddElementCommand(canvas_id=canvas_id, user_id="test", element=stroke)
        history.push(command)
        history.undo()

        redone = history.redo()
        assert redone is command
        assert history.can_undo()
        assert not history.can_redo()

    def test_push_clears_redo_stack(self) -> None:
        """Test that pushing a new command clears the redo stack."""
        history = CommandHistory()
        canvas_id = uuid4()

        cmd1 = AddElementCommand(
            canvas_id=canvas_id,
            user_id="test",
            element=Stroke(position=Point(x=0, y=0), points=[]),
        )
        cmd2 = AddElementCommand(
            canvas_id=canvas_id,
            user_id="test",
            element=Stroke(position=Point(x=1, y=1), points=[]),
        )

        history.push(cmd1)
        history.undo()
        assert history.can_redo()

        history.push(cmd2)
        assert not history.can_redo()

    def test_max_history_limit(self) -> None:
        """Test that history respects max_history limit."""
        history = CommandHistory(max_history=5)
        canvas_id = uuid4()

        for i in range(10):
            cmd = AddElementCommand(
                canvas_id=canvas_id,
                user_id="test",
                element=Stroke(position=Point(x=float(i), y=0), points=[]),
            )
            history.push(cmd)

        assert history.undo_count == 5

    def test_undo_empty_stack(self) -> None:
        """Test undoing with empty stack returns None."""
        history = CommandHistory()
        assert history.undo() is None

    def test_redo_empty_stack(self) -> None:
        """Test redoing with empty stack returns None."""
        history = CommandHistory()
        assert history.redo() is None

    def test_clear(self) -> None:
        """Test clearing command history."""
        history = CommandHistory()
        canvas_id = uuid4()

        cmd = AddElementCommand(
            canvas_id=canvas_id,
            user_id="test",
            element=Stroke(position=Point(x=0, y=0), points=[]),
        )
        history.push(cmd)
        history.undo()

        history.clear()
        assert not history.can_undo()
        assert not history.can_redo()


class TestCommandHistoryManager:
    """Tests for CommandHistoryManager class."""

    def test_separate_histories_per_canvas(self) -> None:
        """Test that each canvas has its own history."""
        manager = CommandHistoryManager()
        canvas1 = uuid4()
        canvas2 = uuid4()

        cmd1 = AddElementCommand(
            canvas_id=canvas1,
            user_id="test",
            element=Stroke(position=Point(x=0, y=0), points=[]),
        )
        cmd2 = AddElementCommand(
            canvas_id=canvas2,
            user_id="test",
            element=Stroke(position=Point(x=1, y=1), points=[]),
        )

        manager.push(canvas1, cmd1)
        manager.push(canvas2, cmd2)

        history1 = manager.get_history(canvas1)
        history2 = manager.get_history(canvas2)

        assert history1.undo_count == 1
        assert history2.undo_count == 1

        manager.undo(canvas1)
        assert history1.undo_count == 0
        assert history2.undo_count == 1

    def test_remove_canvas_history(self) -> None:
        """Test removing a canvas's history."""
        manager = CommandHistoryManager()
        canvas_id = uuid4()

        cmd = AddElementCommand(
            canvas_id=canvas_id,
            user_id="test",
            element=Stroke(position=Point(x=0, y=0), points=[]),
        )
        manager.push(canvas_id, cmd)

        manager.remove(canvas_id)
        assert manager.get_history(canvas_id).undo_count == 0


# Command Tests


class TestCommands:
    """Tests for individual command classes."""

    def test_add_element_command(self) -> None:
        """Test AddElementCommand."""
        canvas_id = uuid4()
        stroke = Stroke(position=Point(x=0, y=0), points=[])

        cmd = AddElementCommand(canvas_id=canvas_id, user_id="test", element=stroke)

        assert cmd.execute() is stroke
        assert cmd.undo() == stroke.id

        data = cmd.to_dict()
        assert data["type"] == "add_element"
        assert data["canvas_id"] == str(canvas_id)
        assert data["element_id"] == str(stroke.id)

    def test_delete_element_command(self) -> None:
        """Test DeleteElementCommand."""
        canvas_id = uuid4()
        element_id = uuid4()
        stroke = Stroke(id=element_id, position=Point(x=0, y=0), points=[])

        cmd = DeleteElementCommand(canvas_id=canvas_id, user_id="test", element_id=element_id)
        cmd.set_deleted_element(stroke)

        assert cmd.execute() == element_id
        assert cmd.undo() is stroke

    def test_update_element_command(self) -> None:
        """Test UpdateElementCommand."""
        canvas_id = uuid4()
        element_id = uuid4()

        cmd = UpdateElementCommand(
            canvas_id=canvas_id,
            user_id="test",
            element_id=element_id,
            updates={"z_index": 10},
        )
        cmd.set_previous_state({"z_index": 0})

        assert cmd.execute() == {"z_index": 10}
        assert cmd.undo() == {"z_index": 0}

    def test_move_element_command(self) -> None:
        """Test MoveElementCommand."""
        canvas_id = uuid4()
        element_id = uuid4()

        cmd = MoveElementCommand(
            canvas_id=canvas_id,
            user_id="test",
            element_id=element_id,
            new_x=100.0,
            new_y=200.0,
        )
        cmd.set_old_position(0.0, 0.0)

        assert cmd.execute() == (100.0, 200.0)
        assert cmd.undo() == (0.0, 0.0)

    def test_reorder_element_command(self) -> None:
        """Test ReorderElementCommand."""
        canvas_id = uuid4()
        element_id = uuid4()

        cmd = ReorderElementCommand(
            canvas_id=canvas_id,
            user_id="test",
            element_id=element_id,
            new_z_index=10,
        )
        cmd.set_old_z_index(0)

        assert cmd.execute() == 10
        assert cmd.undo() == 0

    def test_group_elements_command(self) -> None:
        """Test GroupElementsCommand."""
        canvas_id = uuid4()
        element_ids = [uuid4(), uuid4(), uuid4()]

        cmd = GroupElementsCommand(canvas_id=canvas_id, user_id="test", element_ids=element_ids)
        cmd.set_group_id(uuid4())

        assert cmd.execute() == element_ids

    def test_ungroup_elements_command(self) -> None:
        """Test UngroupElementsCommand."""
        canvas_id = uuid4()
        group_id = uuid4()
        child_ids = [uuid4(), uuid4()]
        group = Group(id=group_id, children=child_ids)

        cmd = UngroupElementsCommand(canvas_id=canvas_id, user_id="test", group_id=group_id)
        cmd.set_deleted_group(group, child_ids)

        assert cmd.execute() == group_id
        deleted, children = cmd.undo()
        assert deleted is group
        assert children == child_ids


# Z-Index Ordering Tests


class TestZIndexOrdering:
    """Tests for z-index layer ordering operations."""

    @pytest.mark.asyncio
    async def test_elements_have_z_index(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test that elements have z_index field."""
        canvas = await service.create_canvas(sample_canvas)
        stroke = await service.add_stroke(canvas.id, [Point(x=0, y=0), Point(x=10, y=10), Point(x=20, y=5)])
        assert hasattr(stroke, "z_index")
        assert stroke.z_index >= 0

    @pytest.mark.asyncio
    async def test_bring_to_front(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test bringing an element to the front."""
        canvas = await service.create_canvas(sample_canvas)
        stroke = await service.add_stroke(canvas.id, [Point(x=0, y=0), Point(x=10, y=10)])
        shape = await service.add_shape(canvas.id, ShapeType.RECTANGLE, Point(x=50, y=50), 100.0, 75.0)

        # Bring stroke to front
        brought = await service.bring_to_front(canvas.id, stroke.id)
        assert brought is not None
        assert brought.z_index > shape.z_index

    @pytest.mark.asyncio
    async def test_send_to_back(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test sending an element to the back."""
        canvas = await service.create_canvas(sample_canvas)
        stroke = await service.add_stroke(canvas.id, [Point(x=0, y=0), Point(x=10, y=10)])
        shape = await service.add_shape(canvas.id, ShapeType.RECTANGLE, Point(x=50, y=50), 100.0, 75.0)

        # Send shape to back
        sent = await service.send_to_back(canvas.id, shape.id)
        assert sent is not None

        # Refetch both elements
        updated_stroke = await service.get_element(canvas.id, stroke.id)
        updated_shape = await service.get_element(canvas.id, shape.id)

        assert updated_shape is not None
        assert updated_stroke is not None
        assert updated_shape.z_index < updated_stroke.z_index

    @pytest.mark.asyncio
    async def test_move_forward(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test moving an element one layer forward."""
        canvas = await service.create_canvas(sample_canvas)
        stroke = await service.add_stroke(canvas.id, [Point(x=0, y=0), Point(x=10, y=10)])
        await service.add_shape(canvas.id, ShapeType.RECTANGLE, Point(x=50, y=50), 100.0, 75.0)

        old_z = stroke.z_index
        moved = await service.move_forward(canvas.id, stroke.id)
        assert moved is not None
        assert moved.z_index > old_z

    @pytest.mark.asyncio
    async def test_move_backward(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test moving an element one layer backward."""
        canvas = await service.create_canvas(sample_canvas)
        await service.add_stroke(canvas.id, [Point(x=0, y=0), Point(x=10, y=10)])
        shape = await service.add_shape(canvas.id, ShapeType.RECTANGLE, Point(x=50, y=50), 100.0, 75.0)

        old_z = shape.z_index
        moved = await service.move_backward(canvas.id, shape.id)
        assert moved is not None
        assert moved.z_index < old_z


# Grouping Tests


class TestElementGrouping:
    """Tests for element grouping operations."""

    @pytest.mark.asyncio
    async def test_group_elements(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test grouping multiple elements."""
        canvas = await service.create_canvas(sample_canvas)
        stroke = await service.add_stroke(canvas.id, [Point(x=0, y=0), Point(x=10, y=10)])
        shape = await service.add_shape(canvas.id, ShapeType.RECTANGLE, Point(x=50, y=50), 100.0, 75.0)

        group = await service.group_elements(canvas.id, [stroke.id, shape.id])

        assert group is not None
        assert group.element_type == ElementType.GROUP
        assert len(group.children) == 2
        assert stroke.id in group.children
        assert shape.id in group.children

    @pytest.mark.asyncio
    async def test_grouped_elements_have_group_id(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test that grouped elements have their group_id set."""
        canvas = await service.create_canvas(sample_canvas)
        stroke = await service.add_stroke(canvas.id, [Point(x=0, y=0), Point(x=10, y=10)])
        shape = await service.add_shape(canvas.id, ShapeType.RECTANGLE, Point(x=50, y=50), 100.0, 75.0)

        group = await service.group_elements(canvas.id, [stroke.id, shape.id])
        assert group is not None

        # Refetch elements
        updated_stroke = await service.get_element(canvas.id, stroke.id)
        updated_shape = await service.get_element(canvas.id, shape.id)

        assert updated_stroke is not None
        assert updated_shape is not None
        assert updated_stroke.group_id == group.id
        assert updated_shape.group_id == group.id

    @pytest.mark.asyncio
    async def test_ungroup_elements(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test ungrouping elements."""
        canvas = await service.create_canvas(sample_canvas)
        stroke = await service.add_stroke(canvas.id, [Point(x=0, y=0), Point(x=10, y=10)])
        shape = await service.add_shape(canvas.id, ShapeType.RECTANGLE, Point(x=50, y=50), 100.0, 75.0)

        group = await service.group_elements(canvas.id, [stroke.id, shape.id])
        assert group is not None

        ungrouped = await service.ungroup_elements(canvas.id, group.id)
        assert len(ungrouped) == 2

        # The ungrouped elements should have group_id=None
        for element in ungrouped:
            assert element.group_id is None

        # Group should be deleted
        with pytest.raises(ElementNotFoundError):
            await service.get_element(canvas.id, group.id)

    @pytest.mark.asyncio
    async def test_group_not_enough_elements(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test that grouping fewer than 2 elements raises ValueError."""
        canvas = await service.create_canvas(sample_canvas)
        stroke = await service.add_stroke(canvas.id, [Point(x=0, y=0)])

        with pytest.raises(ValueError, match="At least 2 elements"):
            await service.group_elements(canvas.id, [stroke.id])

    @pytest.mark.asyncio
    async def test_ungroup_nonexistent_group(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test ungrouping a nonexistent group raises error."""
        canvas = await service.create_canvas(sample_canvas)

        with pytest.raises(ElementNotFoundError):
            await service.ungroup_elements(canvas.id, uuid4())


# Copy/Paste Tests


class TestCopyPaste:
    """Tests for copy/paste operations."""

    @pytest.mark.asyncio
    async def test_copy_elements(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test copying elements to clipboard."""
        canvas = await service.create_canvas(sample_canvas)
        stroke = await service.add_stroke(canvas.id, [Point(x=0, y=0), Point(x=10, y=10)])
        shape = await service.add_shape(canvas.id, ShapeType.RECTANGLE, Point(x=50, y=50), 100.0, 75.0)

        count = await service.copy_elements(canvas.id, [stroke.id, shape.id], user_id="user1")
        assert count == 2
        assert service.get_clipboard_count("user1") == 2

    @pytest.mark.asyncio
    async def test_paste_elements(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test pasting elements from clipboard."""
        canvas = await service.create_canvas(sample_canvas)
        stroke = await service.add_stroke(canvas.id, [Point(x=0, y=0), Point(x=10, y=10)])

        await service.copy_elements(canvas.id, [stroke.id], user_id="user1")
        pasted = await service.paste_elements(canvas.id, user_id="user1")

        assert len(pasted) == 1
        assert pasted[0].id != stroke.id  # New ID
        assert pasted[0].position.x == stroke.position.x + 10  # Offset

    @pytest.mark.asyncio
    async def test_paste_with_offset(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test pasting elements with custom offset."""
        canvas = await service.create_canvas(sample_canvas)
        stroke = await service.add_stroke(canvas.id, [Point(x=0, y=0), Point(x=10, y=10)])

        await service.copy_elements(canvas.id, [stroke.id], user_id="user1")
        pasted = await service.paste_elements(canvas.id, user_id="user1", offset_x=50.0, offset_y=50.0)

        assert len(pasted) == 1
        assert pasted[0].position.x == stroke.position.x + 50.0
        assert pasted[0].position.y == stroke.position.y + 50.0

    @pytest.mark.asyncio
    async def test_paste_empty_clipboard(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test pasting with empty clipboard."""
        canvas = await service.create_canvas(sample_canvas)

        pasted = await service.paste_elements(canvas.id, user_id="user1")
        assert pasted == []

    @pytest.mark.asyncio
    async def test_clear_clipboard(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test clearing the clipboard."""
        canvas = await service.create_canvas(sample_canvas)
        stroke = await service.add_stroke(canvas.id, [Point(x=0, y=0), Point(x=10, y=10)])

        await service.copy_elements(canvas.id, [stroke.id], user_id="user1")
        assert service.get_clipboard_count("user1") == 1

        service.clear_clipboard("user1")
        assert service.get_clipboard_count("user1") == 0

    @pytest.mark.asyncio
    async def test_separate_clipboards_per_user(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test that each user has their own clipboard."""
        canvas = await service.create_canvas(sample_canvas)
        stroke = await service.add_stroke(canvas.id, [Point(x=0, y=0), Point(x=10, y=10)])
        shape = await service.add_shape(canvas.id, ShapeType.RECTANGLE, Point(x=50, y=50), 100.0, 75.0)

        await service.copy_elements(canvas.id, [stroke.id], user_id="user1")
        await service.copy_elements(canvas.id, [shape.id], user_id="user2")

        assert service.get_clipboard_count("user1") == 1
        assert service.get_clipboard_count("user2") == 1


# Undo/Redo Tests


class TestUndoRedo:
    """Tests for undo/redo operations."""

    @pytest.mark.asyncio
    async def test_undo_add_element(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test undoing an add element operation."""
        canvas = await service.create_canvas(sample_canvas)
        stroke = await service.add_stroke(canvas.id, [Point(x=0, y=0), Point(x=10, y=10)])

        assert service.can_undo(canvas.id)

        success = await service.undo(canvas.id)
        assert success

        # Element should be gone
        with pytest.raises(ElementNotFoundError):
            await service.get_element(canvas.id, stroke.id)

    @pytest.mark.asyncio
    async def test_redo_add_element(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test redoing an add element operation."""
        canvas = await service.create_canvas(sample_canvas)
        stroke = await service.add_stroke(canvas.id, [Point(x=0, y=0), Point(x=10, y=10)])

        await service.undo(canvas.id)
        assert service.can_redo(canvas.id)

        success = await service.redo(canvas.id)
        assert success

        # Element should be back
        element = await service.get_element(canvas.id, stroke.id)
        assert element is not None

    @pytest.mark.asyncio
    async def test_undo_delete_element(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test undoing a delete element operation."""
        canvas = await service.create_canvas(sample_canvas)
        stroke = await service.add_stroke(canvas.id, [Point(x=0, y=0), Point(x=10, y=10)])

        await service.delete_element(canvas.id, stroke.id)

        # Verify element is deleted
        with pytest.raises(ElementNotFoundError):
            await service.get_element(canvas.id, stroke.id)

        # Undo the delete
        await service.undo(canvas.id)

        # Element should be restored
        element = await service.get_element(canvas.id, stroke.id)
        assert element is not None

    @pytest.mark.asyncio
    async def test_undo_reorder_element(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test undoing a reorder operation."""
        canvas = await service.create_canvas(sample_canvas)
        stroke = await service.add_stroke(canvas.id, [Point(x=0, y=0), Point(x=10, y=10)])
        original_z = stroke.z_index

        # Bring to front
        await service.bring_to_front(canvas.id, stroke.id)

        # Verify it moved
        moved = await service.get_element(canvas.id, stroke.id)
        assert moved is not None
        assert moved.z_index > original_z

        # Undo
        await service.undo(canvas.id)

        # Should be back to original z-index
        restored = await service.get_element(canvas.id, stroke.id)
        assert restored is not None
        assert restored.z_index == original_z

    @pytest.mark.asyncio
    async def test_undo_nothing_to_undo(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test undoing when there's nothing to undo."""
        canvas = await service.create_canvas(sample_canvas)

        success = await service.undo(canvas.id)
        assert not success

    @pytest.mark.asyncio
    async def test_redo_nothing_to_redo(self, service: CanvasService, sample_canvas: Canvas) -> None:
        """Test redoing when there's nothing to redo."""
        canvas = await service.create_canvas(sample_canvas)

        success = await service.redo(canvas.id)
        assert not success


# Group Element Tests


class TestGroupElement:
    """Tests for the Group element type."""

    def test_group_element_type(self) -> None:
        """Test that Group has correct element type."""
        group = Group(name="Test Group")
        assert group.element_type == ElementType.GROUP

    def test_group_children(self) -> None:
        """Test Group children list."""
        child_ids = [uuid4(), uuid4()]
        group = Group(name="Test Group", children=child_ids)

        assert len(group.children) == 2
        assert child_ids[0] in group.children
        assert child_ids[1] in group.children

    def test_group_locked(self) -> None:
        """Test Group locked property."""
        group = Group(name="Locked Group", locked=True)
        assert group.locked

    def test_group_collapsed(self) -> None:
        """Test Group collapsed property."""
        group = Group(name="Collapsed Group", collapsed=True)
        assert group.collapsed

    def test_group_default_values(self) -> None:
        """Test Group default values."""
        group = Group()
        assert group.name == ""
        assert group.children == []
        assert not group.locked
        assert not group.collapsed
