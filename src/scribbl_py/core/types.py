"""Core type definitions for scribbl-py."""

from __future__ import annotations

from enum import StrEnum


class ElementType(StrEnum):
    """Enumeration of element types in the canvas."""

    STROKE = "stroke"
    SHAPE = "shape"
    TEXT = "text"
    GROUP = "group"


class ShapeType(StrEnum):
    """Enumeration of shape types available for drawing."""

    RECTANGLE = "rectangle"
    ELLIPSE = "ellipse"
    LINE = "line"
    ARROW = "arrow"
    TRIANGLE = "triangle"
