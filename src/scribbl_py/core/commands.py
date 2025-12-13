"""Command pattern implementation for undo/redo functionality."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from uuid import UUID

    from scribbl_py.core.models import Element


@dataclass
class Command(ABC):
    """Abstract base class for all commands.

    Commands encapsulate operations that can be executed and undone,
    enabling undo/redo functionality.
    """

    canvas_id: UUID
    user_id: str

    @abstractmethod
    def execute(self) -> Any:
        """Execute the command and return the result."""
        ...

    @abstractmethod
    def undo(self) -> Any:
        """Undo the command and return the result."""
        ...

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Convert command to dictionary for serialization."""
        ...


@dataclass
class AddElementCommand(Command):
    """Command for adding an element to a canvas."""

    element: Element
    _executed: bool = field(default=False, init=False)

    def execute(self) -> Element:
        """Execute returns the element to be added."""
        self._executed = True
        return self.element

    def undo(self) -> UUID:
        """Undo returns the element ID to be deleted."""
        return self.element.id

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": "add_element",
            "canvas_id": str(self.canvas_id),
            "user_id": self.user_id,
            "element_id": str(self.element.id),
            "element_type": self.element.element_type.value,
        }


@dataclass
class DeleteElementCommand(Command):
    """Command for deleting an element from a canvas."""

    element_id: UUID
    deleted_element: Element | None = None

    def execute(self) -> UUID:
        """Execute returns the element ID to be deleted."""
        return self.element_id

    def undo(self) -> Element | None:
        """Undo returns the element to be restored."""
        return self.deleted_element

    def set_deleted_element(self, element: Element) -> None:
        """Store the deleted element for undo capability."""
        self.deleted_element = element

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": "delete_element",
            "canvas_id": str(self.canvas_id),
            "user_id": self.user_id,
            "element_id": str(self.element_id),
        }


@dataclass
class UpdateElementCommand(Command):
    """Command for updating an element on a canvas."""

    element_id: UUID
    updates: dict[str, Any]
    previous_state: dict[str, Any] = field(default_factory=dict)

    def execute(self) -> dict[str, Any]:
        """Execute returns the updates to be applied."""
        return self.updates

    def undo(self) -> dict[str, Any]:
        """Undo returns the previous state to restore."""
        return self.previous_state

    def set_previous_state(self, state: dict[str, Any]) -> None:
        """Store the previous state for undo capability."""
        self.previous_state = state

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": "update_element",
            "canvas_id": str(self.canvas_id),
            "user_id": self.user_id,
            "element_id": str(self.element_id),
            "updates": self.updates,
        }


@dataclass
class MoveElementCommand(Command):
    """Command for moving an element to a new position."""

    element_id: UUID
    new_x: float
    new_y: float
    old_x: float = 0.0
    old_y: float = 0.0

    def execute(self) -> tuple[float, float]:
        """Execute returns the new position."""
        return (self.new_x, self.new_y)

    def undo(self) -> tuple[float, float]:
        """Undo returns the old position."""
        return (self.old_x, self.old_y)

    def set_old_position(self, x: float, y: float) -> None:
        """Store the old position for undo capability."""
        self.old_x = x
        self.old_y = y

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": "move_element",
            "canvas_id": str(self.canvas_id),
            "user_id": self.user_id,
            "element_id": str(self.element_id),
            "new_x": self.new_x,
            "new_y": self.new_y,
            "old_x": self.old_x,
            "old_y": self.old_y,
        }


@dataclass
class ReorderElementCommand(Command):
    """Command for changing an element's z-index."""

    element_id: UUID
    new_z_index: int
    old_z_index: int = 0

    def execute(self) -> int:
        """Execute returns the new z-index."""
        return self.new_z_index

    def undo(self) -> int:
        """Undo returns the old z-index."""
        return self.old_z_index

    def set_old_z_index(self, z_index: int) -> None:
        """Store the old z-index for undo capability."""
        self.old_z_index = z_index

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": "reorder_element",
            "canvas_id": str(self.canvas_id),
            "user_id": self.user_id,
            "element_id": str(self.element_id),
            "new_z_index": self.new_z_index,
            "old_z_index": self.old_z_index,
        }


@dataclass
class GroupElementsCommand(Command):
    """Command for grouping multiple elements."""

    element_ids: list[UUID]
    group_id: UUID | None = None
    previous_group_ids: dict[UUID, UUID | None] = field(default_factory=dict)

    def execute(self) -> list[UUID]:
        """Execute returns the element IDs to be grouped."""
        return self.element_ids

    def undo(self) -> dict[UUID, UUID | None]:
        """Undo returns the previous group assignments."""
        return self.previous_group_ids

    def set_group_id(self, group_id: UUID) -> None:
        """Set the group ID after group creation."""
        self.group_id = group_id

    def set_previous_group_ids(self, group_ids: dict[UUID, UUID | None]) -> None:
        """Store previous group IDs for undo capability."""
        self.previous_group_ids = group_ids

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": "group_elements",
            "canvas_id": str(self.canvas_id),
            "user_id": self.user_id,
            "element_ids": [str(eid) for eid in self.element_ids],
            "group_id": str(self.group_id) if self.group_id else None,
        }


@dataclass
class UngroupElementsCommand(Command):
    """Command for ungrouping elements."""

    group_id: UUID
    child_ids: list[UUID] = field(default_factory=list)
    deleted_group: Element | None = None

    def execute(self) -> UUID:
        """Execute returns the group ID to be ungrouped."""
        return self.group_id

    def undo(self) -> tuple[Element | None, list[UUID]]:
        """Undo returns the group to restore and its children."""
        return (self.deleted_group, self.child_ids)

    def set_deleted_group(self, group: Element, child_ids: list[UUID]) -> None:
        """Store the deleted group for undo capability."""
        self.deleted_group = group
        self.child_ids = child_ids

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": "ungroup_elements",
            "canvas_id": str(self.canvas_id),
            "user_id": self.user_id,
            "group_id": str(self.group_id),
            "child_ids": [str(cid) for cid in self.child_ids],
        }


class CommandHistory:
    """Manages command history for undo/redo functionality.

    Each canvas has its own command history. Commands are stored in two stacks:
    - undo_stack: Commands that can be undone
    - redo_stack: Commands that were undone and can be redone

    Attributes:
        max_history: Maximum number of commands to keep in history.
    """

    def __init__(self, max_history: int = 100) -> None:
        """Initialize command history.

        Args:
            max_history: Maximum number of commands to keep.
        """
        self.max_history = max_history
        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []

    def push(self, command: Command) -> None:
        """Add a command to the history.

        This clears the redo stack since new actions invalidate
        any previously undone commands.

        Args:
            command: The command to add.
        """
        self._undo_stack.append(command)
        self._redo_stack.clear()

        # Limit history size
        if len(self._undo_stack) > self.max_history:
            self._undo_stack.pop(0)

    def undo(self) -> Command | None:
        """Get the command to undo.

        Returns:
            The command to undo, or None if no commands to undo.
        """
        if not self._undo_stack:
            return None
        command = self._undo_stack.pop()
        self._redo_stack.append(command)
        return command

    def redo(self) -> Command | None:
        """Get the command to redo.

        Returns:
            The command to redo, or None if no commands to redo.
        """
        if not self._redo_stack:
            return None
        command = self._redo_stack.pop()
        self._undo_stack.append(command)
        return command

    def can_undo(self) -> bool:
        """Check if there are commands to undo."""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if there are commands to redo."""
        return len(self._redo_stack) > 0

    def clear(self) -> None:
        """Clear all command history."""
        self._undo_stack.clear()
        self._redo_stack.clear()

    @property
    def undo_count(self) -> int:
        """Number of commands that can be undone."""
        return len(self._undo_stack)

    @property
    def redo_count(self) -> int:
        """Number of commands that can be redone."""
        return len(self._redo_stack)


class CommandHistoryManager:
    """Manages command histories for multiple canvases.

    This class maintains a separate CommandHistory for each canvas,
    enabling per-canvas undo/redo functionality.
    """

    def __init__(self, max_history: int = 100) -> None:
        """Initialize the command history manager.

        Args:
            max_history: Maximum history size for each canvas.
        """
        self.max_history = max_history
        self._histories: dict[UUID, CommandHistory] = {}

    def get_history(self, canvas_id: UUID) -> CommandHistory:
        """Get or create command history for a canvas.

        Args:
            canvas_id: The canvas ID.

        Returns:
            The command history for the canvas.
        """
        if canvas_id not in self._histories:
            self._histories[canvas_id] = CommandHistory(self.max_history)
        return self._histories[canvas_id]

    def push(self, canvas_id: UUID, command: Command) -> None:
        """Add a command to a canvas's history.

        Args:
            canvas_id: The canvas ID.
            command: The command to add.
        """
        self.get_history(canvas_id).push(command)

    def undo(self, canvas_id: UUID) -> Command | None:
        """Undo the last command for a canvas.

        Args:
            canvas_id: The canvas ID.

        Returns:
            The command to undo, or None if nothing to undo.
        """
        return self.get_history(canvas_id).undo()

    def redo(self, canvas_id: UUID) -> Command | None:
        """Redo the last undone command for a canvas.

        Args:
            canvas_id: The canvas ID.

        Returns:
            The command to redo, or None if nothing to redo.
        """
        return self.get_history(canvas_id).redo()

    def clear(self, canvas_id: UUID) -> None:
        """Clear command history for a canvas.

        Args:
            canvas_id: The canvas ID.
        """
        if canvas_id in self._histories:
            self._histories[canvas_id].clear()

    def remove(self, canvas_id: UUID) -> None:
        """Remove command history for a canvas.

        Args:
            canvas_id: The canvas ID.
        """
        self._histories.pop(canvas_id, None)
