"""Canvas service providing business logic for canvas operations."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from scribbl_py.core.commands import (
    AddElementCommand,
    CommandHistoryManager,
    DeleteElementCommand,
    GroupElementsCommand,
    MoveElementCommand,
    ReorderElementCommand,
    UngroupElementsCommand,
    UpdateElementCommand,
)
from scribbl_py.core.models import Canvas, Element, Group, Point, Shape, Stroke, Text
from scribbl_py.core.style import ElementStyle
from scribbl_py.exceptions import CanvasNotFoundError, ElementNotFoundError

if TYPE_CHECKING:
    from uuid import UUID

    from scribbl_py.core.types import ShapeType
    from scribbl_py.storage.base import StorageProtocol


class CanvasService:
    """Service for managing canvases and their elements.

    This service provides business logic for canvas operations,
    wrapping the storage layer with validation and convenience methods.

    Attributes:
        command_history: Manager for undo/redo command histories.
        clipboard: In-memory clipboard for copy/paste operations.
    """

    def __init__(self, storage: StorageProtocol, max_history: int = 100) -> None:
        """Initialize the canvas service.

        Args:
            storage: Storage backend implementing StorageProtocol.
            max_history: Maximum undo history size per canvas.
        """
        self._storage = storage
        self.command_history = CommandHistoryManager(max_history)
        self._clipboard: dict[str, list[Element]] = {}  # user_id -> copied elements
        self._z_index_counter: dict[UUID, int] = {}  # canvas_id -> next z_index

    # Canvas operations
    async def create_canvas(
        self,
        name: str,
        width: int = 1920,
        height: int = 1080,
        background_color: str = "#ffffff",
    ) -> Canvas:
        """Create a new canvas.

        Args:
            name: Display name for the canvas.
            width: Canvas width in pixels.
            height: Canvas height in pixels.
            background_color: Background color in hex format.

        Returns:
            The newly created canvas.

        Raises:
            StorageError: If the canvas cannot be created.
        """
        canvas = Canvas(
            name=name,
            width=width,
            height=height,
            background_color=background_color,
        )
        return await self._storage.create_canvas(canvas)

    async def get_canvas(self, canvas_id: UUID) -> Canvas:
        """Get a canvas by ID.

        Args:
            canvas_id: The unique identifier of the canvas.

        Returns:
            The requested canvas.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
        """
        canvas = await self._storage.get_canvas(canvas_id)
        if canvas is None:
            raise CanvasNotFoundError(canvas_id)
        return canvas

    async def list_canvases(self) -> list[Canvas]:
        """List all canvases.

        Returns:
            A list of all canvases, ordered by creation date (newest first).

        Raises:
            StorageError: If the list operation fails.
        """
        return await self._storage.list_canvases()

    async def update_canvas(
        self,
        canvas_id: UUID,
        *,
        name: str | None = None,
        width: int | None = None,
        height: int | None = None,
        background_color: str | None = None,
    ) -> Canvas:
        """Update canvas properties.

        Only provided fields are updated. Fields with None values are ignored.

        Args:
            canvas_id: The unique identifier of the canvas.
            name: New display name for the canvas.
            width: New canvas width in pixels.
            height: New canvas height in pixels.
            background_color: New background color in hex format.

        Returns:
            The updated canvas.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            StorageError: If the update operation fails.
        """
        canvas = await self.get_canvas(canvas_id)
        updates = {}
        if name is not None:
            updates["name"] = name
        if width is not None:
            updates["width"] = width
        if height is not None:
            updates["height"] = height
        if background_color is not None:
            updates["background_color"] = background_color
        if updates:
            updates["updated_at"] = datetime.now(UTC)
            canvas = replace(canvas, **updates)
            return await self._storage.update_canvas(canvas)
        return canvas

    async def delete_canvas(self, canvas_id: UUID) -> bool:
        """Delete a canvas.

        Args:
            canvas_id: The unique identifier of the canvas to delete.

        Returns:
            True if the canvas was deleted, False if it did not exist.

        Raises:
            StorageError: If the delete operation fails.
        """
        return await self._storage.delete_canvas(canvas_id)

    # Element operations
    async def add_stroke(
        self,
        canvas_id: UUID,
        points: list[Point],
        *,
        style: ElementStyle | None = None,
        smoothing: float = 0.5,
        user_id: str = "system",
    ) -> Stroke:
        """Add a stroke to a canvas.

        Args:
            canvas_id: The unique identifier of the canvas.
            points: List of points that make up the stroke path.
            style: Visual styling configuration for the stroke.
            smoothing: Smoothing factor applied to the stroke (0.0 to 1.0).
            user_id: ID of the user performing the action.

        Returns:
            The created stroke element.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            StorageError: If the add operation fails.
        """
        position = points[0] if points else Point(x=0, y=0)
        stroke = Stroke(
            position=position,
            points=points,
            style=style or ElementStyle(),
            smoothing=smoothing,
            z_index=await self._get_next_z_index(canvas_id),
        )
        created = await self._storage.add_element(canvas_id, stroke)

        # Record command for undo
        cmd = AddElementCommand(canvas_id=canvas_id, user_id=user_id, element=created)
        cmd.execute()
        self.command_history.push(canvas_id, cmd)

        return created

    async def add_shape(
        self,
        canvas_id: UUID,
        shape_type: ShapeType,
        position: Point,
        width: float,
        height: float,
        *,
        style: ElementStyle | None = None,
        rotation: float = 0.0,
        user_id: str = "system",
    ) -> Shape:
        """Add a shape to a canvas.

        Args:
            canvas_id: The unique identifier of the canvas.
            shape_type: Type of shape (rectangle, ellipse, etc.).
            position: Position of the shape on the canvas.
            width: Width of the shape in pixels.
            height: Height of the shape in pixels.
            style: Visual styling configuration for the shape.
            rotation: Rotation angle in degrees.
            user_id: ID of the user performing the action.

        Returns:
            The created shape element.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            StorageError: If the add operation fails.
        """
        shape = Shape(
            shape_type=shape_type,
            position=position,
            width=width,
            height=height,
            style=style or ElementStyle(),
            rotation=rotation,
            z_index=await self._get_next_z_index(canvas_id),
        )
        created = await self._storage.add_element(canvas_id, shape)

        # Record command for undo
        cmd = AddElementCommand(canvas_id=canvas_id, user_id=user_id, element=created)
        cmd.execute()
        self.command_history.push(canvas_id, cmd)

        return created

    async def add_text(
        self,
        canvas_id: UUID,
        content: str,
        position: Point,
        *,
        style: ElementStyle | None = None,
        font_size: int = 16,
        font_family: str = "sans-serif",
        user_id: str = "system",
    ) -> Text:
        """Add text to a canvas.

        Args:
            canvas_id: The unique identifier of the canvas.
            content: The text content to display.
            position: Position of the text on the canvas.
            style: Visual styling configuration for the text.
            font_size: Font size in pixels.
            font_family: Font family name.
            user_id: ID of the user performing the action.

        Returns:
            The created text element.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            StorageError: If the add operation fails.
        """
        text = Text(
            content=content,
            position=position,
            style=style or ElementStyle(),
            font_size=font_size,
            font_family=font_family,
            z_index=await self._get_next_z_index(canvas_id),
        )
        created = await self._storage.add_element(canvas_id, text)

        # Record command for undo
        cmd = AddElementCommand(canvas_id=canvas_id, user_id=user_id, element=created)
        cmd.execute()
        self.command_history.push(canvas_id, cmd)

        return created

    async def get_element(self, canvas_id: UUID, element_id: UUID) -> Element:
        """Get an element from a canvas.

        Args:
            canvas_id: The unique identifier of the canvas.
            element_id: The unique identifier of the element.

        Returns:
            The requested element.

        Raises:
            ElementNotFoundError: If the element does not exist.
            CanvasNotFoundError: If the canvas does not exist.
            StorageError: If the retrieval operation fails.
        """
        element = await self._storage.get_element(canvas_id, element_id)
        if element is None:
            raise ElementNotFoundError(element_id)
        return element

    async def list_elements(self, canvas_id: UUID) -> list[Element]:
        """List all elements on a canvas.

        Args:
            canvas_id: The unique identifier of the canvas.

        Returns:
            A list of all elements on the canvas, ordered by creation date.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            StorageError: If the list operation fails.
        """
        return await self._storage.list_elements(canvas_id)

    async def delete_element(self, canvas_id: UUID, element_id: UUID, user_id: str = "system") -> bool:
        """Delete an element from a canvas.

        Args:
            canvas_id: The unique identifier of the canvas.
            element_id: The unique identifier of the element to delete.
            user_id: ID of the user performing the action.

        Returns:
            True if the element was deleted, False if it did not exist.

        Raises:
            CanvasNotFoundError: If the canvas does not exist.
            StorageError: If the delete operation fails.
        """
        # Get the element before deleting for undo capability
        element = await self._storage.get_element(canvas_id, element_id)

        # Record command for undo
        cmd = DeleteElementCommand(canvas_id=canvas_id, user_id=user_id, element_id=element_id)
        if element:
            cmd.set_deleted_element(element)
        self.command_history.push(canvas_id, cmd)

        return await self._storage.delete_element(canvas_id, element_id)

    # Z-ordering operations

    async def _get_next_z_index(self, canvas_id: UUID) -> int:
        """Get the next available z-index for a canvas.

        Args:
            canvas_id: The canvas ID.

        Returns:
            The next z-index value.
        """
        if canvas_id not in self._z_index_counter:
            elements = await self._storage.list_elements(canvas_id)
            max_z = max((e.z_index for e in elements), default=-1)
            self._z_index_counter[canvas_id] = max_z + 1
        result = self._z_index_counter[canvas_id]
        self._z_index_counter[canvas_id] += 1
        return result

    async def bring_to_front(
        self,
        canvas_id: UUID,
        element_id: UUID,
        user_id: str = "system",
    ) -> Element:
        """Bring an element to the front (highest z-index).

        Args:
            canvas_id: The canvas ID.
            element_id: The element ID.
            user_id: ID of the user performing the action.

        Returns:
            The updated element.

        Raises:
            ElementNotFoundError: If the element does not exist.
        """
        element = await self.get_element(canvas_id, element_id)
        old_z = element.z_index
        new_z = await self._get_next_z_index(canvas_id)

        # Create command for undo
        cmd = ReorderElementCommand(
            canvas_id=canvas_id,
            user_id=user_id,
            element_id=element_id,
            new_z_index=new_z,
        )
        cmd.set_old_z_index(old_z)
        self.command_history.push(canvas_id, cmd)

        updated = replace(element, z_index=new_z)
        return await self._storage.update_element(canvas_id, updated)

    async def send_to_back(
        self,
        canvas_id: UUID,
        element_id: UUID,
        user_id: str = "system",
    ) -> Element:
        """Send an element to the back (lowest z-index).

        Args:
            canvas_id: The canvas ID.
            element_id: The element ID.
            user_id: ID of the user performing the action.

        Returns:
            The updated element.

        Raises:
            ElementNotFoundError: If the element does not exist.
        """
        element = await self.get_element(canvas_id, element_id)
        old_z = element.z_index
        elements = await self._storage.list_elements(canvas_id)
        min_z = min((e.z_index for e in elements), default=0)
        new_z = min_z - 1

        cmd = ReorderElementCommand(
            canvas_id=canvas_id,
            user_id=user_id,
            element_id=element_id,
            new_z_index=new_z,
        )
        cmd.set_old_z_index(old_z)
        self.command_history.push(canvas_id, cmd)

        updated = replace(element, z_index=new_z)
        return await self._storage.update_element(canvas_id, updated)

    async def move_forward(
        self,
        canvas_id: UUID,
        element_id: UUID,
        user_id: str = "system",
    ) -> Element:
        """Move an element one layer forward.

        Args:
            canvas_id: The canvas ID.
            element_id: The element ID.
            user_id: ID of the user performing the action.

        Returns:
            The updated element.
        """
        element = await self.get_element(canvas_id, element_id)
        old_z = element.z_index
        new_z = old_z + 1

        cmd = ReorderElementCommand(
            canvas_id=canvas_id,
            user_id=user_id,
            element_id=element_id,
            new_z_index=new_z,
        )
        cmd.set_old_z_index(old_z)
        self.command_history.push(canvas_id, cmd)

        updated = replace(element, z_index=new_z)
        return await self._storage.update_element(canvas_id, updated)

    async def move_backward(
        self,
        canvas_id: UUID,
        element_id: UUID,
        user_id: str = "system",
    ) -> Element:
        """Move an element one layer backward.

        Args:
            canvas_id: The canvas ID.
            element_id: The element ID.
            user_id: ID of the user performing the action.

        Returns:
            The updated element.
        """
        element = await self.get_element(canvas_id, element_id)
        old_z = element.z_index
        new_z = old_z - 1

        cmd = ReorderElementCommand(
            canvas_id=canvas_id,
            user_id=user_id,
            element_id=element_id,
            new_z_index=new_z,
        )
        cmd.set_old_z_index(old_z)
        self.command_history.push(canvas_id, cmd)

        updated = replace(element, z_index=new_z)
        return await self._storage.update_element(canvas_id, updated)

    # Layer state operations (visibility/lock)

    async def toggle_visibility(
        self,
        canvas_id: UUID,
        element_id: UUID,
        user_id: str = "system",
    ) -> Element:
        """Toggle element visibility.

        Args:
            canvas_id: The canvas ID.
            element_id: The element ID.
            user_id: ID of the user performing the action.

        Returns:
            The updated element.

        Raises:
            ElementNotFoundError: If the element does not exist.
        """
        element = await self.get_element(canvas_id, element_id)
        new_visible = not element.visible

        # Record for undo
        cmd = UpdateElementCommand(
            canvas_id=canvas_id,
            user_id=user_id,
            element_id=element_id,
            updates={"visible": new_visible},
        )
        cmd.set_previous_state({"visible": element.visible})
        self.command_history.push(canvas_id, cmd)

        updated = replace(element, visible=new_visible)
        return await self._storage.update_element(canvas_id, updated)

    async def set_visibility(
        self,
        canvas_id: UUID,
        element_id: UUID,
        visible: bool,
        user_id: str = "system",
    ) -> Element:
        """Set element visibility explicitly.

        Args:
            canvas_id: The canvas ID.
            element_id: The element ID.
            visible: New visibility state.
            user_id: ID of the user performing the action.

        Returns:
            The updated element.

        Raises:
            ElementNotFoundError: If the element does not exist.
        """
        element = await self.get_element(canvas_id, element_id)
        if element.visible == visible:
            return element

        cmd = UpdateElementCommand(
            canvas_id=canvas_id,
            user_id=user_id,
            element_id=element_id,
            updates={"visible": visible},
        )
        cmd.set_previous_state({"visible": element.visible})
        self.command_history.push(canvas_id, cmd)

        updated = replace(element, visible=visible)
        return await self._storage.update_element(canvas_id, updated)

    async def toggle_lock(
        self,
        canvas_id: UUID,
        element_id: UUID,
        user_id: str = "system",
    ) -> Element:
        """Toggle element lock state.

        Args:
            canvas_id: The canvas ID.
            element_id: The element ID.
            user_id: ID of the user performing the action.

        Returns:
            The updated element.

        Raises:
            ElementNotFoundError: If the element does not exist.
        """
        element = await self.get_element(canvas_id, element_id)
        new_locked = not element.locked

        cmd = UpdateElementCommand(
            canvas_id=canvas_id,
            user_id=user_id,
            element_id=element_id,
            updates={"locked": new_locked},
        )
        cmd.set_previous_state({"locked": element.locked})
        self.command_history.push(canvas_id, cmd)

        updated = replace(element, locked=new_locked)
        return await self._storage.update_element(canvas_id, updated)

    async def set_lock(
        self,
        canvas_id: UUID,
        element_id: UUID,
        locked: bool,
        user_id: str = "system",
    ) -> Element:
        """Set element lock state explicitly.

        Args:
            canvas_id: The canvas ID.
            element_id: The element ID.
            locked: New lock state.
            user_id: ID of the user performing the action.

        Returns:
            The updated element.

        Raises:
            ElementNotFoundError: If the element does not exist.
        """
        element = await self.get_element(canvas_id, element_id)
        if element.locked == locked:
            return element

        cmd = UpdateElementCommand(
            canvas_id=canvas_id,
            user_id=user_id,
            element_id=element_id,
            updates={"locked": locked},
        )
        cmd.set_previous_state({"locked": element.locked})
        self.command_history.push(canvas_id, cmd)

        updated = replace(element, locked=locked)
        return await self._storage.update_element(canvas_id, updated)

    # Grouping operations

    async def group_elements(
        self,
        canvas_id: UUID,
        element_ids: list[UUID],
        user_id: str = "system",
        group_name: str = "",
    ) -> Group:
        """Group multiple elements together.

        Args:
            canvas_id: The canvas ID.
            element_ids: IDs of elements to group.
            user_id: ID of the user performing the action.
            group_name: Optional name for the group.

        Returns:
            The created group element.

        Raises:
            ValueError: If fewer than 2 elements are provided.
            ElementNotFoundError: If any element does not exist.
        """
        if len(element_ids) < 2:
            msg = "At least 2 elements are required to create a group"
            raise ValueError(msg)

        # Verify all elements exist and store previous group assignments
        previous_groups: dict[UUID, UUID | None] = {}
        for eid in element_ids:
            element = await self.get_element(canvas_id, eid)
            previous_groups[eid] = element.group_id

        # Create the group
        group = Group(
            name=group_name,
            children=list(element_ids),
            z_index=await self._get_next_z_index(canvas_id),
        )
        created_group = await self._storage.add_element(canvas_id, group)

        # Update elements with group_id
        for eid in element_ids:
            element = await self._storage.get_element(canvas_id, eid)
            if element:
                updated = replace(element, group_id=created_group.id)
                await self._storage.update_element(canvas_id, updated)

        # Record command for undo
        cmd = GroupElementsCommand(
            canvas_id=canvas_id,
            user_id=user_id,
            element_ids=list(element_ids),
        )
        cmd.set_group_id(created_group.id)
        cmd.set_previous_group_ids(previous_groups)
        self.command_history.push(canvas_id, cmd)

        return created_group

    async def ungroup_elements(
        self,
        canvas_id: UUID,
        group_id: UUID,
        user_id: str = "system",
    ) -> list[Element]:
        """Ungroup elements from a group.

        Args:
            canvas_id: The canvas ID.
            group_id: ID of the group to ungroup.
            user_id: ID of the user performing the action.

        Returns:
            List of elements that were in the group.

        Raises:
            ElementNotFoundError: If the group does not exist.
            ValueError: If the element is not a group.
        """
        group = await self.get_element(canvas_id, group_id)
        if not isinstance(group, Group):
            msg = f"Element {group_id} is not a group"
            raise ValueError(msg)

        child_ids = list(group.children)
        ungrouped_elements: list[Element] = []

        # Remove group_id from all children
        for child_id in child_ids:
            element = await self._storage.get_element(canvas_id, child_id)
            if element:
                updated = replace(element, group_id=None)
                await self._storage.update_element(canvas_id, updated)
                ungrouped_elements.append(updated)

        # Record command before deleting group
        cmd = UngroupElementsCommand(
            canvas_id=canvas_id,
            user_id=user_id,
            group_id=group_id,
        )
        cmd.set_deleted_group(group, child_ids)
        self.command_history.push(canvas_id, cmd)

        # Delete the group element
        await self._storage.delete_element(canvas_id, group_id)

        return ungrouped_elements

    # Copy/paste operations

    async def copy_elements(
        self,
        canvas_id: UUID,
        element_ids: list[UUID],
        user_id: str,
    ) -> int:
        """Copy elements to the clipboard.

        Args:
            canvas_id: The canvas ID.
            element_ids: IDs of elements to copy.
            user_id: ID of the user copying.

        Returns:
            Number of elements copied.
        """
        copied: list[Element] = []
        for eid in element_ids:
            element = await self._storage.get_element(canvas_id, eid)
            if element:
                copied.append(deepcopy(element))

        self._clipboard[user_id] = copied
        return len(copied)

    async def paste_elements(
        self,
        canvas_id: UUID,
        user_id: str,
        offset_x: float = 10.0,
        offset_y: float = 10.0,
    ) -> list[Element]:
        """Paste elements from the clipboard.

        Args:
            canvas_id: The canvas ID to paste into.
            user_id: ID of the user pasting.
            offset_x: X offset for pasted elements.
            offset_y: Y offset for pasted elements.

        Returns:
            List of newly created elements.
        """
        if user_id not in self._clipboard or not self._clipboard[user_id]:
            return []

        pasted: list[Element] = []
        id_mapping: dict[UUID, UUID] = {}  # old_id -> new_id

        for element in self._clipboard[user_id]:
            # Create new element with new ID and offset position
            new_id = uuid4()
            id_mapping[element.id] = new_id

            new_position = Point(
                x=element.position.x + offset_x,
                y=element.position.y + offset_y,
                pressure=element.position.pressure,
            )

            # Create a copy with new ID and position
            new_element = replace(
                element,
                id=new_id,
                position=new_position,
                z_index=await self._get_next_z_index(canvas_id),
                group_id=None,  # Don't preserve group membership
            )

            created = await self._storage.add_element(canvas_id, new_element)
            pasted.append(created)

            # Record command
            cmd = AddElementCommand(
                canvas_id=canvas_id,
                user_id=user_id,
                element=created,
            )
            self.command_history.push(canvas_id, cmd)

        return pasted

    def clear_clipboard(self, user_id: str) -> None:
        """Clear a user's clipboard.

        Args:
            user_id: ID of the user.
        """
        self._clipboard.pop(user_id, None)

    def get_clipboard_count(self, user_id: str) -> int:
        """Get number of items in a user's clipboard.

        Args:
            user_id: ID of the user.

        Returns:
            Number of elements in clipboard.
        """
        return len(self._clipboard.get(user_id, []))

    # Undo/redo operations

    async def undo(  # noqa: C901, PLR0912
        self, canvas_id: UUID, user_id: str = "system"
    ) -> bool:
        """Undo the last operation on a canvas.

        Args:
            canvas_id: The canvas ID.
            user_id: ID of the user (for filtering, not yet implemented).

        Returns:
            True if an operation was undone, False if nothing to undo.
        """
        command = self.command_history.undo(canvas_id)
        if command is None:
            return False

        # Execute the undo based on command type
        if isinstance(command, AddElementCommand):
            # Undo add = delete
            await self._storage.delete_element(canvas_id, command.element.id)

        elif isinstance(command, DeleteElementCommand):
            # Undo delete = restore element
            if command.deleted_element:
                await self._storage.add_element(canvas_id, command.deleted_element)

        elif isinstance(command, UpdateElementCommand):
            # Undo update = restore previous state
            element = await self._storage.get_element(canvas_id, command.element_id)
            if element and command.previous_state:
                restored = replace(element, **command.previous_state)
                await self._storage.update_element(canvas_id, restored)

        elif isinstance(command, MoveElementCommand):
            # Undo move = restore old position
            element = await self._storage.get_element(canvas_id, command.element_id)
            if element:
                old_pos = Point(x=command.old_x, y=command.old_y)
                restored = replace(element, position=old_pos)
                await self._storage.update_element(canvas_id, restored)

        elif isinstance(command, ReorderElementCommand):
            # Undo reorder = restore old z-index
            element = await self._storage.get_element(canvas_id, command.element_id)
            if element:
                restored = replace(element, z_index=command.old_z_index)
                await self._storage.update_element(canvas_id, restored)

        elif isinstance(command, GroupElementsCommand):
            # Undo group = ungroup and restore previous group assignments
            if command.group_id:
                # Remove group_id from children and restore previous
                for eid, prev_gid in command.previous_group_ids.items():
                    element = await self._storage.get_element(canvas_id, eid)
                    if element:
                        restored = replace(element, group_id=prev_gid)
                        await self._storage.update_element(canvas_id, restored)
                # Delete the group
                await self._storage.delete_element(canvas_id, command.group_id)

        elif isinstance(command, UngroupElementsCommand) and command.deleted_group:
            # Undo ungroup = recreate group and reassign children
            await self._storage.add_element(canvas_id, command.deleted_group)
            for child_id in command.child_ids:
                element = await self._storage.get_element(canvas_id, child_id)
                if element:
                    restored = replace(element, group_id=command.group_id)
                    await self._storage.update_element(canvas_id, restored)

        return True

    async def redo(  # noqa: C901, PLR0912
        self, canvas_id: UUID, user_id: str = "system"
    ) -> bool:
        """Redo the last undone operation on a canvas.

        Args:
            canvas_id: The canvas ID.
            user_id: ID of the user (for filtering, not yet implemented).

        Returns:
            True if an operation was redone, False if nothing to redo.
        """
        command = self.command_history.redo(canvas_id)
        if command is None:
            return False

        # Execute the redo based on command type
        if isinstance(command, AddElementCommand):
            # Redo add = add again
            await self._storage.add_element(canvas_id, command.element)

        elif isinstance(command, DeleteElementCommand):
            # Redo delete = delete again
            await self._storage.delete_element(canvas_id, command.element_id)

        elif isinstance(command, UpdateElementCommand):
            # Redo update = apply updates again
            element = await self._storage.get_element(canvas_id, command.element_id)
            if element:
                updated = replace(element, **command.updates)
                await self._storage.update_element(canvas_id, updated)

        elif isinstance(command, MoveElementCommand):
            # Redo move = apply new position
            element = await self._storage.get_element(canvas_id, command.element_id)
            if element:
                new_pos = Point(x=command.new_x, y=command.new_y)
                updated = replace(element, position=new_pos)
                await self._storage.update_element(canvas_id, updated)

        elif isinstance(command, ReorderElementCommand):
            # Redo reorder = apply new z-index
            element = await self._storage.get_element(canvas_id, command.element_id)
            if element:
                updated = replace(element, z_index=command.new_z_index)
                await self._storage.update_element(canvas_id, updated)

        elif isinstance(command, GroupElementsCommand):
            # Redo group = recreate group
            if command.group_id:
                group = Group(
                    id=command.group_id,
                    children=command.element_ids,
                )
                await self._storage.add_element(canvas_id, group)
                for eid in command.element_ids:
                    element = await self._storage.get_element(canvas_id, eid)
                    if element:
                        updated = replace(element, group_id=command.group_id)
                        await self._storage.update_element(canvas_id, updated)

        elif isinstance(command, UngroupElementsCommand):
            # Redo ungroup = ungroup again
            for child_id in command.child_ids:
                element = await self._storage.get_element(canvas_id, child_id)
                if element:
                    updated = replace(element, group_id=None)
                    await self._storage.update_element(canvas_id, updated)
            await self._storage.delete_element(canvas_id, command.group_id)

        return True

    def can_undo(self, canvas_id: UUID) -> bool:
        """Check if undo is available for a canvas.

        Args:
            canvas_id: The canvas ID.

        Returns:
            True if undo is available.
        """
        return self.command_history.get_history(canvas_id).can_undo()

    def can_redo(self, canvas_id: UUID) -> bool:
        """Check if redo is available for a canvas.

        Args:
            canvas_id: The canvas ID.

        Returns:
            True if redo is available.
        """
        return self.command_history.get_history(canvas_id).can_redo()
