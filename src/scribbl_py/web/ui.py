"""UI Controller for scribbl-py frontend views."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, ClassVar
from uuid import UUID, uuid4

from litestar import Controller, get, post
from litestar.connection import Request  # noqa: TC002
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Redirect, Template
from litestar.status_codes import HTTP_201_CREATED

from scribbl_py.services.canvas import CanvasService


@dataclass
class CreateCanvasForm:
    """Form data for creating a new canvas."""

    name: str
    width: int = 1920
    height: int = 1080
    background_color: str = "#ffffff"


@dataclass
class Pagination:
    """Pagination metadata."""

    page: int
    per_page: int
    total: int

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        return max(1, (self.total + self.per_page - 1) // self.per_page)

    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1

    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.total_pages


class UIController(Controller):
    """Controller for UI views.

    This controller handles all the HTML page rendering using Jinja2 templates
    and HTMX for dynamic interactions.
    """

    path = "/ui"
    tags: ClassVar[list[str]] = ["UI"]

    @get("/", name="ui_index")
    async def index(self, request: Request, service: CanvasService) -> Template:
        """Render the dashboard/home page.

        Args:
            request: The HTMX-aware request object.
            service: The canvas service instance.

        Returns:
            The rendered index template.
        """
        canvases = await service.list_canvases()

        # Get stats
        canvas_count = len(canvases)
        element_count = sum(len(c.elements) for c in canvases)

        # Get recent canvases (last 6)
        recent_canvases = sorted(
            canvases,
            key=lambda c: c.updated_at or c.created_at,
            reverse=True,
        )[:6]

        context = {
            "canvas_count": canvas_count,
            "element_count": element_count,
            "active_users": 0,  # TODO: Implement with connection manager
            "recent_canvases": recent_canvases,
        }

        # Return partial for HTMX requests
        if request.htmx:
            return Template(
                template_name="partials/index_content.html",
                context=context,
            )

        return Template(
            template_name="index.html",
            context=context,
        )

    @get("/canvases")
    async def canvas_list(
        self,
        request: Request,
        service: CanvasService,
        page: int = 1,
        per_page: int = 12,
        search: str | None = None,
    ) -> Template:
        """Render the canvas list page.

        Args:
            request: The HTMX-aware request object.
            service: The canvas service instance.
            page: Current page number.
            per_page: Number of items per page.
            search: Optional search query.

        Returns:
            The rendered canvas list template.
        """
        canvases = await service.list_canvases()

        # Filter by search query
        if search:
            search_lower = search.lower()
            canvases = [c for c in canvases if search_lower in c.name.lower()]

        # Sort by updated_at (most recent first)
        canvases = sorted(
            canvases,
            key=lambda c: c.updated_at or c.created_at,
            reverse=True,
        )

        # Paginate
        total = len(canvases)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_canvases = canvases[start:end]

        pagination = Pagination(page=page, per_page=per_page, total=total)

        context = {
            "canvases": paginated_canvases,
            "pagination": pagination if total > per_page else None,
            "search": search,
        }

        # Return grid partial for search/pagination (triggered by input element)
        if request.htmx and request.htmx.trigger:
            return Template(
                template_name="partials/canvas_grid.html",
                context=context,
            )

        # Return content partial for HTMX navigation (e.g., navbar links)
        if request.htmx:
            return Template(
                template_name="partials/canvas_list_content.html",
                context=context,
            )

        return Template(
            template_name="canvas_list.html",
            context=context,
        )

    @get("/canvases/new")
    async def canvas_new(self, request: Request) -> Template:
        """Render the create canvas form.

        Args:
            request: The HTMX-aware request object.

        Returns:
            The rendered create canvas template.
        """
        # Return partial for HTMX requests
        if request.htmx:
            return Template(template_name="partials/canvas_new_content.html")

        return Template(template_name="canvas_new.html")

    @post("/canvases", status_code=HTTP_201_CREATED)
    async def canvas_create(
        self,
        request: Request,
        service: CanvasService,
        data: Annotated[CreateCanvasForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
    ) -> Redirect:
        """Create a new canvas and redirect to editor.

        Args:
            request: The HTMX-aware request object.
            service: The canvas service instance.
            data: The form data for creating the canvas.

        Returns:
            Redirect to the canvas editor.
        """
        canvas = await service.create_canvas(
            name=data.name,
            width=data.width,
            height=data.height,
            background_color=data.background_color,
        )

        # Always redirect to editor (full page) - editor needs special layout
        return Redirect(path=f"/ui/canvases/{canvas.id}/edit")

    @get("/canvases/{canvas_id:uuid}/edit")
    async def canvas_edit(
        self,
        request: Request,
        service: CanvasService,
        canvas_id: UUID,
    ) -> Template:
        """Render the canvas editor page.

        Args:
            request: The HTMX-aware request object.
            service: The canvas service instance.
            canvas_id: The canvas UUID.

        Returns:
            The rendered canvas editor template.
        """
        canvas = await service.get_canvas(canvas_id)

        # Generate a user ID for the session (in production, this would come from auth)
        user_id = str(uuid4())
        user_name = "Anonymous"

        context = {
            "canvas": canvas,
            "user_id": user_id,
            "user_name": user_name,
        }

        return Template(
            template_name="canvas_editor.html",
            context=context,
        )


def get_template_directory() -> Path:
    """Get the path to the templates directory.

    Returns:
        Path to the templates directory.
    """
    return Path(__file__).parent.parent / "templates"
