# scribbl-py Development Plan

## Completed

### Phase 1: Project Setup
- [x] Project scaffolding (pyproject.toml, Makefile, CI workflows)
- [x] Pre-commit hooks, ruff, ty configuration
- [x] Documentation structure (Sphinx + shibuya)

### Phase 2: Core API + Models
- [x] Domain models: `Canvas`, `Stroke`, `Shape`, `Text`, `Point`, `ElementStyle`
- [x] Type enums: `ElementType`, `ShapeType`
- [x] Storage layer: `StorageProtocol`, `InMemoryStorage`
- [x] Service layer: `CanvasService`
- [x] REST API: Canvas CRUD, Element CRUD
- [x] Litestar plugin: `ScribblPlugin`, `ScribblConfig`
- [x] Tests: 114 passing

### Phase 3: WebSocket Real-time
- [x] WebSocket handler for canvas sessions (`CanvasWebSocketHandler`)
- [x] Connection manager for tracking users (`ConnectionManager`)
- [x] Broadcast element changes to connected clients
- [x] Cursor position sync
- [x] Conflict resolution strategy (last-write-wins with version tracking)
- [x] Message types: join, leave, element_add/update/delete, cursor_move
- [x] Tests: 137 passing

### Phase 4: Database Persistence
- [x] SQLAlchemy models (`CanvasModel`, `ElementModel` with JSON columns)
- [x] Alembic migrations (`001_initial_schema`)
- [x] `DatabaseStorage` implementing `StorageProtocol`
- [x] `[db]` optional extra (advanced-alchemy, alembic, asyncpg)
- [x] Lazy imports to avoid errors when db extra not installed
- [x] Tests: 164 passing

### Phase 5: Canvas Operations
- [x] Element layers with z-index ordering (`z_index` field on Element)
- [x] Z-ordering operations: `bring_to_front`, `send_to_back`, `move_forward`, `move_backward`
- [x] Command pattern for undo/redo (`CommandHistory`, `CommandHistoryManager`)
- [x] Command types: Add, Delete, Update, Move, Reorder, Group, Ungroup
- [x] Element grouping with `Group` element type and `group_id` field
- [x] Group operations: `group_elements`, `ungroup_elements`
- [x] Copy/paste elements with per-user clipboard
- [x] Database migration for z_index and group_id (`002_add_z_index_and_group`)
- [x] Tests: 207 passing

### Phase 6: Export
- [x] `ExportService` for canvas rendering to multiple formats
- [x] Export canvas as JSON (dict/string)
- [x] Export canvas as SVG (strokes, shapes, text with full styling)
- [x] Export canvas as PNG (via cairosvg, optional `[export]` extra)
- [x] REST API endpoints: `/export/json`, `/export/svg`, `/export/png`
- [x] Tests: 237 passing

## API Endpoints

### REST API

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

**Message Types (Client -> Server):**
- `join` - Join canvas session with user_id/user_name
- `element_add` - Add stroke/shape/text element
- `element_update` - Update element properties
- `element_delete` - Delete an element
- `cursor_move` - Update cursor position

**Message Types (Server -> Client):**
- `sync` - Full canvas state on join
- `user_joined` / `user_left` - User presence
- `element_added` / `element_updated` / `element_deleted` - Element changes
- `cursor_moved` - Other users' cursor positions
- `error` - Error responses

## Next Up

### Phase 10: Persistence & Deployment ✅
- [x] Docker deployment (Dockerfile + docker-compose.yml)
- [x] SQLite storage backend for persistence
  - [x] Create SQLite storage implementation (`storage/db/auth_storage.py`)
  - [x] User, Session, UserStats models (`storage/db/auth_models.py`)
  - [x] Database setup and session factory (`storage/db/setup.py`)
  - [x] Wire up DATABASE_URL environment variable
- [x] Wire up stats recording to game events
  - [x] TelemetryService with tracking for connections, games, rounds, guesses, drawings
  - [x] Room created/closed tracking
  - [x] Game started/ended tracking with winner
  - [x] Round started tracking with drawer
  - [x] Guess tracking (correct/wrong, time)
  - [x] Drawing completed tracking
  - [x] Player join/leave tracking
- [x] Telemetry & Analytics
  - [x] Stats API endpoint (`/stats`)
  - [x] Optional Sentry integration (SENTRY_DSN env var)
  - [x] Optional PostHog integration (POSTHOG_API_KEY env var)
  - [x] Custom callback support for external integrations

### Phase 11: Developer Experience & Tooling ✅
- [x] Swap to Scalar default + Swagger OpenAPI plugin
  - [x] ScalarRenderPlugin at `/schema/` (primary)
  - [x] SwaggerRenderPlugin at `/schema/swagger` (secondary)
  - [x] Custom Scalar theme CSS (`frontend/dist/css/scalar-theme.css`)
- [x] Database CLI commands via advanced-alchemy SQLAlchemyPlugin
  - [x] `litestar database upgrade` - Run migrations
  - [x] `litestar database downgrade` - Rollback migrations
  - [x] `litestar database make-migrations` - Autogenerate migrations from models
  - [x] `litestar database show-current-revision` - Check current state
- [x] Custom query CLI commands (`litestar query`)
  - [x] `litestar query users` - List users with search
  - [x] `litestar query stats` - Show user statistics
  - [x] `litestar query sessions` - List sessions (with --active flag)
  - [x] `litestar query leaderboard` - Show leaderboard (by wins/games/accuracy)
  - [x] `litestar query tables` - List all tables with row counts
  - [x] `litestar query sql "SELECT ..."` - Execute raw SELECT queries
- [x] Environment configuration
  - [x] `.env.example` with all environment variables documented
  - [x] LITESTAR_APP for CLI discovery
  - [x] DATABASE_URL support in migrations
- [x] Database migrations
  - [x] `001_initial_schema` - Canvas and Element tables
  - [x] `002_add_z_index_and_group` - Z-index and grouping (SQLite batch mode)
  - [x] `003_auth_tables` - Users, UserStats, Sessions tables

### Phase 12: Production Hardening ✅
- [x] Request/response validation error handling
  - [x] Structured error responses with `ErrorResponse` dataclass
  - [x] Per-field validation error details
  - [x] Exception handlers for all custom exceptions
  - [x] HTTP exception handler with appropriate error codes
- [x] Health check endpoints (`/health`, `/ready`)
  - [x] `/health` - Liveness probe with component health status
  - [x] `/ready` - Readiness probe checking dependencies
  - [x] Database health check with latency measurement
- [x] Structured logging with correlation IDs
  - [x] `CorrelationIdMiddleware` for request tracking
  - [x] `RequestLoggingMiddleware` for request/response logging
  - [x] `X-Correlation-ID` header propagation
  - [x] Structlog integration with context variables
  - [x] JSON logging option for production
- [x] Rate limiting
  - [x] `RateLimitConfig` using Litestar's built-in middleware
  - [x] Configurable via environment variables (`RATE_LIMIT_*`)
  - [x] Default: 100 requests/minute, excludes health checks
  - [x] Returns `429 Too Many Requests` with `RateLimit-*` headers
- [x] Task queue with [Huey](https://huey.readthedocs.io/) (SQLite backend)
  - [x] `SqliteHuey` configuration with environment variables (`TASK_QUEUE_*`)
  - [x] Periodic tasks: session cleanup, weekly stats reset, canvas cleanup, telemetry aggregation
  - [x] CLI commands: `litestar tasks run`, `litestar tasks status`, `litestar tasks list`
  - [x] Manual task runners: `cleanup-sessions`, `cleanup-canvases`, `reset-weekly`
  - [x] `[tasks]` optional extra for Huey dependency

### Phase 9.2: Collaborative Mode ✅
Free-form collaborative whiteboard where everyone draws simultaneously.

**Features:**
- [x] All users can draw at same time
- [x] Real-time cursor positions
- [x] Layer management (visibility, lock, reorder, delete)
- [x] Export to PNG/SVG

---

## Future Phases

### Phase 13: Canvas Editor Enhancements
Advanced drawing tools and capabilities.

- [ ] Image Upload & Manipulation (upload, resize, rotate, crop, opacity)
- [ ] Advanced Shape Tools (polygon, star, arrows, speech bubbles, Bezier curves)
- [ ] Text Formatting (font selection, bold/italic/underline, alignment, text-along-path)
- [ ] Layer opacity sliders
- [ ] Blend modes for layers
- [ ] Infinite canvas with pan/zoom

### Phase 14: Additional Game Modes
New Canvas Clash variations.

- [ ] **Speed Draw** - Rapid-fire 15-30 second rounds
- [ ] **Blind Contour** - Can't see strokes until time's up
- [ ] **Telephone Game** - Alternating draw/guess, each sees only previous entry
- [ ] **Multiplayer Canvas** - Everyone draws simultaneously, layer per user, time-lapse export

### Phase 15: Social Features
Community and engagement features.

- [ ] User Profiles (public gallery, achievements, badges)
- [ ] Drawing Gallery (browse, like, comment, share community art)
- [ ] Drawing Challenges (daily/weekly prompts with voting)
- [ ] Following/followers system
- [ ] Sticky notes and annotations for collaborative mode

### Phase 16: Print & Merchandise
Monetization and physical products.

- [ ] Image to T-Shirt (print-on-demand integration: Printful, Printify)
- [ ] Sticker Sheets (print-ready PDF with cut lines)
- [ ] Canvas Prints (high-res export, standard print sizes)
- [ ] Design marketplace
- [ ] NFT Minting (optional blockchain integration)

### Phase 17: Mobile & Desktop Apps
Native applications.

- [ ] Progressive Web App (PWA) with offline support
- [ ] Native iOS app with Apple Pencil support
- [ ] Native Android app with stylus support
- [ ] Desktop apps (Electron or Tauri)
- [ ] Tablet-optimized interface

### Phase 18: API & Integrations
Third-party connectivity.

- [ ] Webhooks (canvas updates, game events, Discord/Slack integration)
- [ ] Public API with OAuth2 and rate limiting
- [ ] Embed Widget (customizable canvas for external sites)
- [ ] AI Assistance (auto-complete strokes, style transfer, background removal, upscaling)
- [ ] Video/voice chat integration

### Phase 19: Infrastructure Scaling
Production-grade deployment.

- [ ] Redis session storage for horizontal scaling
- [ ] WebSocket message broker (Redis Pub/Sub) for multi-instance
- [ ] CDN integration for static assets
- [ ] S3/GCS storage backend for large canvases
- [ ] Kubernetes Helm chart
- [ ] Terraform modules for cloud deployment

---

## Completed

### Phase 9.1: CanvasClash Mode ✅
Pictionary-style drawing game - fully implemented with:
- Game lobby with room codes, public/private rooms
- Round system with drawer rotation, word selection, timer
- Drawing tools: pen, shapes, line, fill, eraser, 24 colors, brush sizes
- Chat system with guessing, close guess hints, correct guess celebrations
- Spectator mode, custom word lists, content moderation
- All UI components: lobby, game screen, word selection, round end, final scoreboard

### Phase 8: Auth & Permissions ✅
- OAuth2 authentication (Google, Discord, GitHub)
- User profiles with avatars and stats
- Global leaderboards (wins, fastest, drawer, games played)
- Room permissions (kick, ban, transfer host)
- 38 auth + permissions tests passing

### Phase 7: Bug Fixes & Polish ✅
- WebSocket reconnection with exponential backoff
- Real-time stroke streaming (no delay until mouse release)
- All drawing tools working (shapes, text, eraser, fill)
- Undo/redo functionality
- PNG export with Pillow (no system dependencies)

### Phase 8: Frontend UI
Modern, interactive frontend using HTMX + Tailwind CSS + DaisyUI with Bun for build tooling.

#### 8.1 Project Structure & Build Setup
- [x] Create `frontend/` directory structure:
  ```
  frontend/
  ├── package.json          # Bun package manifest
  ├── bunfig.toml           # Bun configuration
  ├── tailwind.config.js    # Tailwind + DaisyUI config
  ├── src/
  │   ├── css/
  │   │   └── main.css      # Tailwind directives + custom styles
  │   └── js/
  │       └── main.js       # HTMX extensions, Alpine.js, custom JS
  └── dist/                 # Built assets (gitignored)
  ```
- [x] Initialize Bun project: `bun init`
- [x] Install dependencies:
  ```bash
  bun add tailwindcss @tailwindcss/cli daisyui
  bun add -d bun-plugin-tailwind
  ```
- [x] Configure `tailwind.config.js` with DaisyUI plugin and scribbl theme
- [x] Add build scripts to `package.json`:
  - `bun run build` - Production build
  - `bun run dev` - Watch mode for development
- [x] Add `[ui]` optional extra to pyproject.toml

#### 8.2 Litestar Integration
- [x] Install litestar-htmx: `uv add litestar-htmx`
- [x] Configure `HTMXPlugin` in Litestar app
- [x] Set up Jinja2 template engine with `JinjaTemplateEngine`
- [x] Configure static files router for built assets:
  ```python
  from litestar.static_files import create_static_files_router

  static_router = create_static_files_router(
      path="/static",
      directories=["frontend/dist"]
  )
  ```
- [x] Create template directory: `src/scribbl/templates/`
- [x] Add `HTMXRequest` type for HTMX-aware request handling

#### 8.3 Base Templates & Layout
- [x] Create `base.html` template with:
  - DaisyUI theme support (light/dark toggle)
  - HTMX script include (`<script src="https://unpkg.com/htmx.org@2"></script>`)
  - Alpine.js for client-side interactivity
  - Tailwind CSS built stylesheet
  - Navigation component with DaisyUI navbar
  - Flash message/toast container for HTMX responses
- [x] Create `partials/` directory for HTMX partial templates
- [x] Implement DaisyUI theme switcher (localStorage persistence)

#### 8.4 Canvas List & Dashboard Views
- [x] `GET /` - Dashboard/landing page
  - Recent canvases grid (DaisyUI cards)
  - Create new canvas button
  - Quick stats (total canvases, recent activity)
- [x] `GET /canvases` - Canvas list view
  - Responsive grid layout with DaisyUI cards
  - Search/filter with HTMX (`hx-get`, `hx-trigger="keyup changed delay:300ms"`)
  - Pagination with HTMX (`hx-get`, `hx-target`, `hx-swap="outerHTML"`)
  - Delete canvas with confirmation modal
- [x] Partial templates for HTMX responses:
  - `partials/canvas_card.html` - Single canvas card
  - `partials/canvas_list.html` - Canvas list container
  - `partials/canvas_grid.html` - Grid of canvas cards

#### 8.5 Canvas Editor View
- [x] `GET /canvases/{id}/edit` - Full canvas editor page
- [x] Canvas toolbar component (DaisyUI button groups):
  - Tool selection (pen, shapes, text, eraser)
  - Color picker
  - Stroke width slider
  - Undo/redo buttons
  - Layer controls
- [x] Canvas area with HTML5 `<canvas>` element
- [x] Side panel for:
  - Element properties (HTMX updates)
  - Layer list with drag-to-reorder
  - Export options
- [x] WebSocket connection indicator (DaisyUI badge)
- [x] User presence indicators (avatars, cursor positions)

#### 8.6 HTMX-Powered Interactions
- [x] Canvas CRUD with HTMX:
  - Create: `hx-post="/api/canvases"` with form
  - Update: `hx-patch="/api/canvases/{id}"` inline editing
  - Delete: `hx-delete` with `hx-confirm` or DaisyUI modal
- [x] Element operations via HTMX:
  - Add element: POST with `HTMXTemplate` response
  - Update element: PATCH with partial swap
  - Delete element: DELETE with `hx-swap="delete"`
- [x] Use `litestar-htmx` response classes:
  ```python
  from litestar_htmx.response import HTMXTemplate, Reswap, Retarget, TriggerEvent

  @get("/canvases/{id}/elements")
  async def get_elements(id: UUID) -> Template:
      return HTMXTemplate(
          template_name="partials/element_list.html",
          context={"elements": elements},
          trigger_event="elementsLoaded"
      )
  ```
- [x] Implement `HXLocation` for client-side redirects without full reload
- [x] Use `TriggerEvent` for toast notifications

#### 8.7 Real-time Features (WebSocket + HTMX)
- [x] WebSocket connection management with reconnection
- [x] HTMX WebSocket extension for real-time updates:
  ```html
  <div hx-ext="ws" ws-connect="/ws/canvas/{id}">
    <div id="canvas-elements" hx-swap-oob="true">
      <!-- Elements updated via WebSocket -->
    </div>
  </div>
  ```
- [x] Cursor position broadcasting
- [x] Live element updates from other users
- [x] Connection status indicator with DaisyUI badge states

#### 8.8 UI Components (DaisyUI)
- [x] Navigation: `navbar`, `menu`, `breadcrumbs`
- [x] Canvas cards: `card`, `card-body`, `card-actions`
- [x] Forms: `input`, `select`, `range`, `toggle`
- [x] Buttons: `btn`, `btn-primary`, `btn-group`
- [x] Feedback: `toast`, `alert`, `loading`, `progress`
- [x] Modals: `modal` for confirmations, settings
- [x] Drawers: `drawer` for mobile navigation
- [x] Tooltips: `tooltip` for toolbar hints
- [x] Theme: Custom scribbl theme extending DaisyUI

#### 8.9 Frontend Controller
- [x] Create `UIController` class:
  ```python
  from litestar import Controller, get
  from litestar_htmx import HTMXRequest
  from litestar.response import Template

  class UIController(Controller):
      path = "/ui"

      @get("/")
      async def index(self, request: HTMXRequest) -> Template:
          return Template("index.html", context={...})

      @get("/canvases")
      async def canvas_list(self, request: HTMXRequest) -> Template:
          if request.htmx:
              return HTMXTemplate("partials/canvas_list.html", ...)
          return Template("canvas_list.html", ...)
  ```
- [x] Route handlers for all UI pages
- [x] HTMX-aware responses (full page vs partial)

#### 8.10 Development Workflow
- [x] Makefile targets:
  - `make frontend-install` - Install frontend dependencies with Bun
  - `make frontend-build` - Build production assets
  - `make frontend-dev` - Watch mode for development
  - `make serve-dev` - Run Litestar with frontend watch
- [x] Hot reload setup for templates
- [x] Browser-sync or similar for CSS changes

#### Dependencies
```toml
# pyproject.toml additions
[project.optional-dependencies]
ui = [
    "litestar[jinja]",
    "litestar-htmx>=0.4.0",
]
```

```json
// frontend/package.json
{
  "dependencies": {
    "tailwindcss": "^4.0",
    "daisyui": "^5.0"
  },
  "devDependencies": {
    "bun-plugin-tailwind": "^0.1"
  }
}
```

#### Reference Patterns
- **litestar-workflows**: Tailwind CDN + Alpine.js base template pattern
- **litestar-pydotorg**: DaisyUI theming, Lucide icons, theme persistence
- **litestar-htmx**: `HTMXPlugin`, `HTMXRequest`, `HTMXTemplate` responses

## Quick Start

```bash
make dev              # Install Python dependencies
make frontend-install # Install frontend dependencies (Bun)
make frontend-build   # Build frontend assets
make serve            # Run app at http://127.0.0.1:8000 (includes UI)
make serve-dev        # Run with hot reload (run make frontend-dev in another terminal)
make serve-api        # Run API only (no UI)
make lint             # Run linters
make ci               # Run all CI checks
```
