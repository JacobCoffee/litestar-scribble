"""Style definitions for canvas elements."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ElementStyle:
    """Styling configuration for canvas elements.

    Attributes:
        stroke_color: The color of the element's stroke/outline in hex format.
        fill_color: Optional fill color for the element in hex format.
        stroke_width: Width of the stroke in pixels.
        opacity: Opacity level from 0.0 (transparent) to 1.0 (opaque).
    """

    stroke_color: str = "#000000"
    fill_color: str | None = None
    stroke_width: float = 2.0
    opacity: float = 1.0
