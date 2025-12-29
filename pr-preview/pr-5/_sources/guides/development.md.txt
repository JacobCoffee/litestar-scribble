# Development Guide

This guide covers setting up a local development environment for scribbl-py.

## Prerequisites

- **Python 3.10+** - scribbl-py supports Python 3.10, 3.11, 3.12, and 3.13
- **uv** - Fast Python package manager ([install](https://docs.astral.sh/uv/getting-started/installation/))
- **Bun** - Fast JavaScript runtime for frontend builds ([install](https://bun.sh/))
- **Git** - Version control

## Quick Start

```bash
# Clone the repository
git clone https://github.com/JacobCoffee/scribbl-py.git
cd scribbl-py

# Install Python dependencies
make dev

# Install frontend dependencies
make frontend-install

# Build frontend assets
make frontend-build

# Run the application
make serve
```

The application will be available at http://127.0.0.1:8000.

---

## Project Structure

```
scribbl-py/
├── src/scribbl_py/      # Main package
│   ├── __init__.py      # Public API exports
│   ├── app.py           # Litestar application
│   ├── plugin.py        # ScribblPlugin and ScribblConfig
│   ├── exceptions.py    # Custom exceptions
│   ├── core/            # Domain models and types
│   │   ├── models.py    # Canvas, Element, Stroke, etc.
│   │   ├── types.py     # Type aliases and enums
│   │   ├── style.py     # ElementStyle dataclass
│   │   ├── logging.py   # Structured logging setup
│   │   ├── error_handling.py  # Exception handlers
│   │   └── rate_limit.py      # Rate limiting config
│   ├── auth/            # Authentication
│   │   ├── config.py    # OAuth configuration
│   │   ├── models.py    # User, Session, UserStats
│   │   ├── service.py   # AuthService
│   │   └── controller.py # Auth endpoints
│   ├── game/            # Canvas Clash game
│   │   ├── models.py    # Room, Player, Round, etc.
│   │   ├── wordbank.py  # Word selection system
│   │   ├── moderation.py # Content moderation
│   │   └── word_lists.py # Default word lists
│   ├── services/        # Business logic
│   │   ├── canvas.py    # CanvasService
│   │   ├── export.py    # ExportService (JSON, SVG, PNG)
│   │   ├── game.py      # GameService
│   │   └── telemetry.py # TelemetryService
│   ├── storage/         # Data persistence
│   │   ├── base.py      # StorageProtocol
│   │   ├── memory.py    # InMemoryStorage
│   │   └── db/          # Database storage
│   │       ├── models.py      # SQLAlchemy models
│   │       ├── storage.py     # DatabaseStorage
│   │       └── migrations/    # Alembic migrations
│   ├── realtime/        # WebSocket handlers
│   │   ├── handler.py   # CanvasWebSocketHandler
│   │   ├── game_handler.py # GameWebSocketHandler
│   │   ├── manager.py   # ConnectionManager
│   │   └── messages.py  # Message types
│   ├── web/             # HTTP layer
│   │   ├── controllers.py # Canvas/Element controllers
│   │   ├── health.py    # Health check endpoints
│   │   ├── ui.py        # UI controller
│   │   └── dto.py       # Data transfer objects
│   ├── cli/             # CLI commands
│   │   └── database.py  # Query commands
│   └── templates/       # Jinja2 templates
├── frontend/            # Frontend assets
│   ├── src/
│   │   ├── css/         # Tailwind CSS
│   │   └── js/          # JavaScript
│   └── dist/            # Built assets
├── tests/               # Test suite
├── docs/                # Documentation
└── examples/            # Example applications
```

---

## Makefile Commands

scribbl-py includes a comprehensive Makefile for common development tasks.

### Setup & Installation

```bash
make install-uv      # Install uv package manager
make dev             # Install dev dependencies
make install         # Production install (no dev deps)
make upgrade         # Upgrade dependencies
make install-prek    # Install prek git hooks
```

### Code Quality

```bash
make lint            # Run prek hooks on all files
make fmt             # Format code with ruff
make fmt-check       # Check formatting without changes
make fmt-fix         # Auto-fix ruff issues
make ruff            # Run ruff with unsafe fixes
make type-check      # Run ty type checker
```

### Testing

```bash
make test            # Run pytest
make test-cov        # Run tests with coverage report
make test-fast       # Quick tests (exit on first failure)
```

### Documentation

```bash
make docs            # Build documentation
make docs-serve      # Serve docs with live reload (port 8001)
make docs-clean      # Clean build artifacts
```

### Frontend

```bash
make frontend-install  # Install frontend dependencies
make frontend-build    # Build frontend for production
make frontend-dev      # Watch mode for development
```

### Application

```bash
make serve           # Run full app (builds frontend first)
make serve-dev       # Run app with hot reload
make serve-api       # Run API only (no UI)
```

### Testing Multiplayer

```bash
make game-test       # Open two browser windows for testing
make game-serve      # Start server and open test browsers
```

---

## Running Tests

scribbl-py uses pytest with pytest-asyncio for async test support.

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
uv run pytest tests/test_canvas.py

# Run specific test
uv run pytest tests/test_canvas.py::test_create_canvas -v

# Run tests matching a pattern
uv run pytest -k "canvas" -v
```

### Test Categories

Tests are marked with pytest markers:

```bash
# Run only unit tests
uv run pytest -m unit

# Run integration tests
uv run pytest -m integration

# Run database tests
uv run pytest -m db
```

---

## Code Quality

### Linting with Ruff

scribbl-py uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check for issues
make ruff-check

# Fix issues automatically
make fmt-fix

# Format code
make fmt
```

### Type Checking

Type checking uses [ty](https://github.com/astral-sh/ty):

```bash
make type-check
```

### Pre-commit Hooks

The project uses [prek](https://prek.dev/) for git hooks:

```bash
# Install hooks
make install-prek

# Run hooks manually
make lint
```

---

## Database Development

### Creating Migrations

```bash
# Generate a migration from model changes
litestar database make-migrations "add user preferences"

# Apply migrations
litestar database upgrade

# Rollback
litestar database downgrade
```

### Query CLI

scribbl-py includes CLI commands for querying the database:

```bash
# List users
litestar query users

# Search users
litestar query users --search "john"

# Show stats
litestar query stats

# List active sessions
litestar query sessions --active

# Show leaderboard
litestar query leaderboard --by wins

# List tables
litestar query tables

# Execute raw SQL
litestar query sql "SELECT * FROM users LIMIT 10"
```

---

## WebSocket Development

### Canvas Collaboration

The canvas WebSocket endpoint (`/ws/canvas/{id}`) handles:

- Element operations (add, update, delete)
- Cursor position sync
- User presence (join/leave)
- Full canvas sync on connect

### Game WebSocket

The game WebSocket endpoint (`/ws/game/{room_id}`) handles:

- Room management (join, leave)
- Game lifecycle (start, round start, round end)
- Drawing updates
- Chat and guessing
- Scoreboard updates

### Testing WebSockets

Use the `make game-test` command to open two browser windows for multiplayer testing.

---

## Frontend Development

### Build System

The frontend uses Bun for package management and builds:

```bash
# Install dependencies
cd frontend && bun install

# Development build (watch mode)
bun run dev

# Production build
bun run build
```

### Stack

- **HTMX** - Dynamic HTML updates
- **Alpine.js** - Client-side interactivity
- **Tailwind CSS** - Utility-first CSS
- **DaisyUI** - Component library

### Hot Reload

For development with hot reload:

```bash
# Terminal 1: Start the server
make serve-dev

# Terminal 2: Watch frontend changes
make frontend-dev
```

---

## Git Worktrees

scribbl-py supports git worktrees for parallel development:

```bash
# Create a new worktree
make wt NAME=feature-name

# List worktrees
make wt-ls

# Prune stale worktrees
make worktree-prune
```

---

## CI/CD

### Running CI Locally

```bash
# Run all CI checks
make ci

# Run with act (local GitHub Actions)
make act-ci
```

### CI Checks

The CI pipeline runs:

1. Linting (`make lint`)
2. Type checking (`make type-check`)
3. Format checking (`make fmt-check`)
4. Tests (`make test`)

---

## Contributing

### Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `make test`
5. Run linting: `make lint`
6. Commit with conventional commits: `git commit -m "feat: add my feature"`
7. Push and create a pull request

### Commit Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Test additions/changes
- `chore:` - Maintenance tasks

---

## Troubleshooting

### Common Issues

**UV not found**
```bash
make install-uv
```

**Bun not found**
```bash
curl -fsSL https://bun.sh/install | bash
```

**Database locked (SQLite)**
```bash
# Kill any running processes
pkill -f uvicorn
# Delete the database and migrate fresh
rm scribbl.db
litestar database upgrade
```

**Port already in use**
```bash
# Find process on port 8000
lsof -i :8000
# Kill it
kill -9 <PID>
```

**Frontend assets not loading**
```bash
make frontend-build
```
