# Configuration Guide

scribbl-py is configured primarily through environment variables. This guide covers all available
configuration options for the application, database, authentication, telemetry, and more.

## Environment Setup

Copy the example environment file and customize it:

```bash
cp .env.example .env
```

The application automatically loads environment variables from a `.env` file in the project root.

---

## Application Settings

### Core Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `LITESTAR_APP` | The Litestar application module path | `scribbl_py.app:app` |
| `DEBUG` | Enable debug mode (verbose logging, debug toolbar) | `false` |

```bash
LITESTAR_APP=scribbl_py.app:app
DEBUG=true
```

---

## Database Configuration

scribbl-py supports SQLite (default) and PostgreSQL databases via SQLAlchemy.

### SQLite (Development)

SQLite is the default database, ideal for development and single-instance deployments:

```bash
DATABASE_URL=sqlite+aiosqlite:///./scribbl.db
```

### PostgreSQL (Production)

For production deployments, PostgreSQL is recommended:

```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/scribbl
```

### Database Migrations

scribbl-py uses Alembic for database migrations. The following CLI commands are available:

```bash
# Apply all pending migrations
litestar database upgrade

# Rollback the last migration
litestar database downgrade

# Auto-generate a new migration from model changes
litestar database make-migrations "migration description"

# Show current database revision
litestar database show-current-revision
```

---

## OAuth Authentication

scribbl-py supports OAuth authentication with Google, Discord, and GitHub. Authentication is optional - the application works without OAuth configured.

### Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new OAuth 2.0 Client ID
3. Add `http://localhost:8000/auth/callback/google` to authorized redirect URIs

```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback/google
```

### Discord OAuth

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Under OAuth2, add `http://localhost:8000/auth/callback/discord` to redirects

```bash
DISCORD_CLIENT_ID=your-client-id
DISCORD_CLIENT_SECRET=your-client-secret
DISCORD_REDIRECT_URI=http://localhost:8000/auth/callback/discord
```

### GitHub OAuth

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Register a new OAuth application
3. Set the callback URL to `http://localhost:8000/auth/callback/github`

```bash
GITHUB_CLIENT_ID=your-client-id
GITHUB_CLIENT_SECRET=your-client-secret
GITHUB_REDIRECT_URI=http://localhost:8000/auth/callback/github
```

### Production OAuth URLs

When deploying to production, update the redirect URIs to match your domain:

```bash
GOOGLE_REDIRECT_URI=https://your-domain.com/auth/callback/google
DISCORD_REDIRECT_URI=https://your-domain.com/auth/callback/discord
GITHUB_REDIRECT_URI=https://your-domain.com/auth/callback/github
```

---

## Session & Security

### Session Secret Key

The session secret key is used to encrypt session cookies. **Generate a secure key for production:**

```bash
# Generate a secure key
python -c "import secrets; print(secrets.token_hex(32))"

# Set in environment
SESSION_SECRET_KEY=your-generated-secret-key
```

:::{warning}
Never use the default `change-me-in-production` value in production. Always generate a unique, random secret key.
:::

---

## Rate Limiting

scribbl-py includes built-in rate limiting to protect against abuse.

| Variable | Description | Default |
|----------|-------------|---------|
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `true` |
| `RATE_LIMIT_PER_MINUTE` | Default requests per minute | `100` |
| `RATE_LIMIT_API_PER_MINUTE` | API endpoint requests per minute | `60` |
| `RATE_LIMIT_AUTH_PER_MINUTE` | Auth endpoint requests per minute | `20` |

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_API_PER_MINUTE=60
RATE_LIMIT_AUTH_PER_MINUTE=20
```

Rate limiting returns a `429 Too Many Requests` response with `RateLimit-*` headers when exceeded:

```
RateLimit-Limit: 100
RateLimit-Remaining: 0
RateLimit-Reset: 1699999999
```

---

## Telemetry & Analytics

### Sentry (Error Tracking)

[Sentry](https://sentry.io/) provides error tracking and performance monitoring:

```bash
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project
SENTRY_TRACES_RATE=0.1      # Sample 10% of transactions
SENTRY_PROFILES_RATE=0.1    # Sample 10% for profiling
ENVIRONMENT=production
```

| Variable | Description | Default |
|----------|-------------|---------|
| `SENTRY_DSN` | Sentry project DSN | (none) |
| `SENTRY_TRACES_RATE` | Transaction sampling rate (0.0-1.0) | `0.1` |
| `SENTRY_PROFILES_RATE` | Profile sampling rate (0.0-1.0) | `0.1` |
| `ENVIRONMENT` | Environment name sent to Sentry | `development` |

### PostHog (Product Analytics)

[PostHog](https://posthog.com/) provides product analytics and feature flags:

```bash
POSTHOG_API_KEY=phc_your-api-key
POSTHOG_HOST=https://app.posthog.com
```

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTHOG_API_KEY` | PostHog project API key | (none) |
| `POSTHOG_HOST` | PostHog instance URL | `https://app.posthog.com` |

### Telemetry Events

When configured, scribbl-py tracks the following events:

- Connection events (WebSocket connect/disconnect)
- Game lifecycle (room created, game started, round started)
- User actions (guesses, drawings, wins)
- Player presence (join/leave)

---

## Task Queue (Huey)

scribbl-py uses [Huey](https://huey.readthedocs.io/) for background task processing with SQLite storage.

| Variable | Description | Default |
|----------|-------------|---------|
| `TASK_QUEUE_ENABLED` | Enable task queue | `true` |
| `TASK_QUEUE_DB_PATH` | SQLite database path for tasks | `./huey_tasks.db` |
| `TASK_QUEUE_IMMEDIATE` | Execute tasks immediately (testing) | `false` |
| `CANVAS_RETENTION_DAYS` | Days before old canvases are cleaned up | `30` |

```bash
TASK_QUEUE_ENABLED=true
TASK_QUEUE_DB_PATH=./huey_tasks.db
TASK_QUEUE_IMMEDIATE=false
CANVAS_RETENTION_DAYS=30
```

---

## Complete Example

Here's a complete `.env` file for production:

```bash
# Application
LITESTAR_APP=scribbl_py.app:app
DEBUG=false

# Database
DATABASE_URL=postgresql+asyncpg://scribbl:password@db:5432/scribbl

# OAuth
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx
GOOGLE_REDIRECT_URI=https://scribbl.example.com/auth/callback/google

DISCORD_CLIENT_ID=xxx
DISCORD_CLIENT_SECRET=xxx
DISCORD_REDIRECT_URI=https://scribbl.example.com/auth/callback/discord

GITHUB_CLIENT_ID=xxx
GITHUB_CLIENT_SECRET=xxx
GITHUB_REDIRECT_URI=https://scribbl.example.com/auth/callback/github

# Security
SESSION_SECRET_KEY=your-64-character-hex-secret-key-here

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=100

# Telemetry
SENTRY_DSN=https://xxx@sentry.io/xxx
SENTRY_TRACES_RATE=0.1
ENVIRONMENT=production

POSTHOG_API_KEY=phc_xxx
POSTHOG_HOST=https://app.posthog.com

# Task Queue
TASK_QUEUE_ENABLED=true
CANVAS_RETENTION_DAYS=30
```

---

## Environment Variable Reference

### All Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LITESTAR_APP` | No | `scribbl_py.app:app` | Application module path |
| `DEBUG` | No | `false` | Enable debug mode |
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./scribbl.db` | Database connection string |
| `SESSION_SECRET_KEY` | Yes (prod) | `change-me-in-production` | Session encryption key |
| `GOOGLE_CLIENT_ID` | No | (none) | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | No | (none) | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | No | (none) | Google OAuth callback URL |
| `DISCORD_CLIENT_ID` | No | (none) | Discord OAuth client ID |
| `DISCORD_CLIENT_SECRET` | No | (none) | Discord OAuth client secret |
| `DISCORD_REDIRECT_URI` | No | (none) | Discord OAuth callback URL |
| `GITHUB_CLIENT_ID` | No | (none) | GitHub OAuth client ID |
| `GITHUB_CLIENT_SECRET` | No | (none) | GitHub OAuth client secret |
| `GITHUB_REDIRECT_URI` | No | (none) | GitHub OAuth callback URL |
| `RATE_LIMIT_ENABLED` | No | `true` | Enable rate limiting |
| `RATE_LIMIT_PER_MINUTE` | No | `100` | Default rate limit |
| `RATE_LIMIT_API_PER_MINUTE` | No | `60` | API rate limit |
| `RATE_LIMIT_AUTH_PER_MINUTE` | No | `20` | Auth rate limit |
| `SENTRY_DSN` | No | (none) | Sentry DSN for error tracking |
| `SENTRY_TRACES_RATE` | No | `0.1` | Sentry transaction sampling |
| `SENTRY_PROFILES_RATE` | No | `0.1` | Sentry profiling sampling |
| `ENVIRONMENT` | No | `development` | Environment name |
| `POSTHOG_API_KEY` | No | (none) | PostHog API key |
| `POSTHOG_HOST` | No | `https://app.posthog.com` | PostHog host URL |
| `TASK_QUEUE_ENABLED` | No | `true` | Enable Huey task queue |
| `TASK_QUEUE_DB_PATH` | No | `./huey_tasks.db` | Huey SQLite path |
| `TASK_QUEUE_IMMEDIATE` | No | `false` | Immediate task execution |
| `CANVAS_RETENTION_DAYS` | No | `30` | Canvas cleanup retention |
