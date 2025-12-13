# scribbl-py

[![CI](https://github.com/JacobCoffee/scribbl-py/actions/workflows/ci.yml/badge.svg)](https://github.com/JacobCoffee/scribbl-py/actions/workflows/ci.yml)
[![Documentation](https://github.com/JacobCoffee/scribbl-py/actions/workflows/docs.yml/badge.svg)](https://jacobcoffee.github.io/scribbl-py)
[![PyPI version](https://img.shields.io/pypi/v/scribbl-py.svg)](https://pypi.org/project/scribbl-py/)
[![Python versions](https://img.shields.io/pypi/pyversions/scribbl-py.svg)](https://pypi.org/project/scribbl-py/)
[![License](https://img.shields.io/github/license/JacobCoffee/scribbl-py)](https://github.com/JacobCoffee/scribbl-py/blob/main/LICENSE)

A real-time collaborative drawing and whiteboard application built with [Litestar](https://litestar.dev), featuring a Pictionary-style game mode (Canvas Clash).

## Features

- **Real-time Collaboration** - Multiple users can draw simultaneously with live cursor tracking
- **Canvas Clash Game Mode** - Pictionary-style drawing game with rounds, scoring, and chat
- **Drawing Tools** - Pen, shapes, lines, fill, eraser, 24 colors, multiple brush sizes
- **OAuth Authentication** - Sign in with Google, Discord, or GitHub
- **Leaderboards** - Track wins, accuracy, fastest guesses, and games played
- **Export** - Save canvases as PNG, SVG, or JSON
- **WebSocket API** - Real-time sync for all canvas operations
- **REST API** - Full CRUD for canvases and elements

## Quick Start

### Using Docker (Recommended)

```bash
# Clone and run
git clone https://github.com/JacobCoffee/scribbl-py
cd scribbl-py
docker compose up -d

# Open in browser
open http://localhost:8000/canvas-clash/
```

### Using pip/uv

```bash
# Install
pip install scribbl-py[all]
# or
uv add scribbl-py[all]

# Run
uvicorn scribbl_py.app:app --reload
```

### From Source

```bash
git clone https://github.com/JacobCoffee/scribbl-py
cd scribbl-py
make dev              # Install dependencies
make frontend-build   # Build frontend assets
make serve            # Run the app
```

## URLs

| Path | Description |
|------|-------------|
| `/canvas-clash/` | Pictionary-style drawing game |
| `/ui/` | Canvas management dashboard |
| `/api/` | REST API |
| `/schema` | OpenAPI documentation (Scalar) |
| `/health` | Health check endpoint |

## Deployment

### Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/scribbl-py)

The project includes a `Dockerfile` ready for Railway deployment. Just connect your repo and deploy.

### Docker

```bash
docker compose up -d
```

### Production Configuration

```bash
cp .env.example .env
# Edit .env with:
# - DEBUG=false
# - Unique SESSION_SECRET_KEY
# - DATABASE_URL (PostgreSQL recommended)
# - OAuth credentials (optional)
```

See [deployment guide](https://jacobcoffee.github.io/scribbl-py/guides/deployment.html) for full instructions.

## Installation Options

```bash
# Core only
pip install scribbl-py

# With database support (PostgreSQL)
pip install scribbl-py[db]

# With OAuth authentication
pip install scribbl-py[auth]

# With background task queue (Huey)
pip install scribbl-py[tasks]

# Everything
pip install scribbl-py[all]
```

## API Overview

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/canvases` | Create canvas |
| `GET` | `/api/canvases` | List canvases |
| `GET` | `/api/canvases/{id}` | Get canvas |
| `DELETE` | `/api/canvases/{id}` | Delete canvas |
| `POST` | `/api/canvases/{id}/elements/strokes` | Add stroke |
| `POST` | `/api/canvases/{id}/elements/shapes` | Add shape |
| `GET` | `/api/canvases/{id}/export/png` | Export as PNG |
| `GET` | `/api/canvases/{id}/export/svg` | Export as SVG |

### WebSocket

Connect to `ws://host/ws/canvas/{canvas_id}` for real-time collaboration.

**Message Types:**
- `join` / `leave` - Session management
- `element_add` / `element_update` / `element_delete` - Drawing operations
- `cursor_move` - Cursor position sync

## Development

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended)
- [Bun](https://bun.sh/) (for frontend)

### Setup

```bash
git clone https://github.com/JacobCoffee/scribbl-py
cd scribbl-py
make dev              # Install dependencies
make install-prek     # Install git hooks
make frontend-build   # Build frontend
```

### Commands

```bash
make help             # Show all commands
make serve            # Run full app
make serve-dev        # Run with hot reload
make test             # Run tests
make lint             # Run linters
make fmt              # Format code
make docs-serve       # Serve documentation
```

### Database Commands

```bash
litestar database upgrade              # Run migrations
litestar database make-migrations "msg" # Create migration
litestar query users                   # List users
litestar query leaderboard             # Show leaderboard
litestar query sql "SELECT ..."        # Run SQL query
```

## Tech Stack

- **Backend**: [Litestar](https://litestar.dev) + Python 3.10+
- **Database**: SQLite (default) or PostgreSQL
- **Frontend**: HTMX + Alpine.js + Tailwind CSS + DaisyUI
- **Build**: [uv](https://docs.astral.sh/uv/) + [Bun](https://bun.sh/)
- **Real-time**: WebSockets
- **Auth**: OAuth2 (Google, Discord, GitHub)

## Documentation

Full documentation at [jacobcoffee.github.io/scribbl-py](https://jacobcoffee.github.io/scribbl-py)

## Contributing

Contributions welcome! Please read the contributing guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit using conventional commits (`git commit -m 'feat: add feature'`)
4. Push and open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.
