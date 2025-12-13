# scribbl-py

```{rst-class} lead
A Litestar-based collaborative drawing and whiteboard application with real-time multiplayer support.
```

**scribbl-py** is a full-featured drawing application built on [Litestar](https://litestar.dev/).
It includes a collaborative canvas editor, a Pictionary-style drawing game (Canvas Clash),
real-time WebSocket synchronization, OAuth authentication, and a modern UI built with
HTMX, Tailwind CSS, and DaisyUI.

---

::::{grid} 1 2 2 3
:gutter: 3

:::{grid-item-card} {octicon}`rocket` Getting Started
:link: getting-started/index
:link-type: doc
:class-card: sd-border-0

Set up your development environment and run scribbl-py locally in minutes.
:::

:::{grid-item-card} {octicon}`gear` Configuration
:link: guides/configuration
:link-type: doc
:class-card: sd-border-0

Environment variables, OAuth setup, telemetry, rate limiting, and more.
:::

:::{grid-item-card} {octicon}`code` API Reference
:link: api/index
:link-type: doc
:class-card: sd-border-0

Complete API documentation for all modules, classes, and functions.
:::

:::{grid-item-card} {octicon}`light-bulb` Roadmap
:link: roadmap
:link-type: doc
:class-card: sd-border-0

Planned features: multiplayer canvas, print-on-demand, mobile apps, and more.
:::

::::

---

## Key Features

::::{grid} 1 2 2 3
:gutter: 3

:::{grid-item-card} Canvas Editor
:class-card: sd-border-0

Full-featured drawing tools: pen, shapes, text, eraser, fill bucket.
24 colors, adjustable brush sizes, layer management, and undo/redo.
:::

:::{grid-item-card} Canvas Clash Game
:class-card: sd-border-0

Pictionary-style multiplayer game with room codes, word selection,
timer-based rounds, chat with guessing, and global leaderboards.
:::

:::{grid-item-card} Real-time Collaboration
:class-card: sd-border-0

WebSocket-based synchronization with cursor tracking, live element
updates, and automatic reconnection with exponential backoff.
:::

:::{grid-item-card} OAuth Authentication
:class-card: sd-border-0

Sign in with Google, Discord, or GitHub. User profiles with avatars,
stats tracking, and room permissions (kick, ban, transfer host).
:::

:::{grid-item-card} Export Options
:class-card: sd-border-0

Export canvases as JSON, SVG, or PNG. Full styling preserved in all
formats with optional Pillow-based PNG rendering.
:::

:::{grid-item-card} Production Ready
:class-card: sd-border-0

Health checks, structured logging with correlation IDs, rate limiting,
Docker deployment, and optional Sentry/PostHog telemetry.
:::

::::

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/JacobCoffee/scribbl-py.git
cd scribbl-py

# Install dependencies with uv
make dev

# Install frontend dependencies with Bun
make frontend-install
make frontend-build

# Run the application
make serve
```

The application will be available at:
- **UI**: http://127.0.0.1:8000/ui/
- **Canvas Clash**: http://127.0.0.1:8000/canvas-clash/
- **API**: http://127.0.0.1:8000/api/
- **OpenAPI Schema**: http://127.0.0.1:8000/schema/

### Docker Deployment

```bash
# Build and run with Docker Compose
docker compose up -d

# View logs
docker compose logs -f
```

---

## Architecture Overview

```
scribbl-py/
├── src/scribbl_py/
│   ├── core/          # Domain models, types, error handling
│   ├── auth/          # OAuth authentication, user management
│   ├── game/          # Canvas Clash game logic
│   ├── services/      # Business logic (canvas, export, telemetry)
│   ├── storage/       # Storage backends (memory, database)
│   ├── realtime/      # WebSocket handlers
│   ├── web/           # Controllers, routes, templates
│   ├── cli/           # CLI commands
│   └── app.py         # Litestar application
├── frontend/          # HTMX + Tailwind + DaisyUI frontend
├── docs/              # Sphinx documentation
└── tests/             # pytest test suite
```

---

## REST API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/canvases` | Create canvas |
| GET | `/api/canvases` | List canvases |
| GET | `/api/canvases/{id}` | Get canvas with elements |
| PATCH | `/api/canvases/{id}` | Update canvas |
| DELETE | `/api/canvases/{id}` | Delete canvas |
| GET | `/api/canvases/{id}/elements` | List elements |
| POST | `/api/canvases/{id}/elements/strokes` | Add stroke |
| POST | `/api/canvases/{id}/elements/shapes` | Add shape |
| POST | `/api/canvases/{id}/elements/texts` | Add text |
| DELETE | `/api/canvases/{id}/elements/{eid}` | Delete element |
| GET | `/api/canvases/{id}/export/json` | Export as JSON |
| GET | `/api/canvases/{id}/export/svg` | Export as SVG |
| GET | `/api/canvases/{id}/export/png` | Export as PNG |

### WebSocket API

| Endpoint | Description |
|----------|-------------|
| `ws://.../ws/canvas/{id}` | Real-time canvas collaboration |
| `ws://.../ws/game/{room_id}` | Canvas Clash game room |

---

```{toctree}
:maxdepth: 2
:caption: Learn
:hidden:

getting-started/index
guides/index
```

```{toctree}
:maxdepth: 2
:caption: Reference
:hidden:

api/index
roadmap
changelog
```

```{toctree}
:caption: Project
:hidden:

GitHub <https://github.com/JacobCoffee/scribbl-py>
Discord <https://discord.gg/litestar>
```

---

## License

scribbl-py is released under the [MIT License](https://github.com/JacobCoffee/scribbl-py/blob/main/LICENSE).

---

## Indices and Tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
