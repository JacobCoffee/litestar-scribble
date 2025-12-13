# syntax=docker/dockerfile:1.9
FROM python:3.12-slim AS build

SHELL ["sh", "-exc"]

# Install build dependencies
RUN <<EOT
apt-get update -qy
apt-get install -qyy \
    -o APT::Install-Recommends=false \
    -o APT::Install-Suggests=false \
    build-essential \
    curl \
    ca-certificates
EOT

# Install uv (only needed in build stage)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# uv configuration for optimal Docker builds:
# - UV_LINK_MODE=copy: Don't use hard links (not supported in containers)
# - UV_COMPILE_BYTECODE=1: Byte-compile for faster startup
# - UV_PYTHON_DOWNLOADS=never: Use system Python, don't download
# - UV_PROJECT_ENVIRONMENT=/app: Install into /app virtualenv
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=/usr/local/bin/python3.12 \
    UV_PROJECT_ENVIRONMENT=/app

# Sync DEPENDENCIES only (cached until uv.lock/pyproject.toml change)
# This layer is cached separately from application code
RUN --mount=type=cache,id=uv-cache,target=/root/.cache \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project --all-extras

# Now install the APPLICATION (separate layer, changes more often)
COPY . /src
WORKDIR /src
RUN --mount=type=cache,id=uv-cache,target=/root/.cache \
    uv sync --locked --no-dev --no-editable --all-extras


# Frontend build stage
FROM node:20-slim AS frontend

RUN npm install -g bun

WORKDIR /app/frontend
COPY frontend/package.json frontend/bun.lock* ./
RUN bun install --frozen-lockfile

COPY frontend/ ./
RUN bun run build


# Runtime stage - minimal, no build tools, no uv
FROM python:3.12-slim

SHELL ["sh", "-exc"]

# Add virtualenv to PATH
ENV PATH=/app/bin:$PATH

# Create non-root user
RUN <<EOT
groupadd -r app
useradd -r -d /app -g app -N app
EOT

# Install only runtime dependencies (no uv, no build tools)
RUN <<EOT
apt-get update -qy
apt-get install -qyy \
    -o APT::Install-Recommends=false \
    -o APT::Install-Suggests=false \
    curl

apt-get clean
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
EOT

# Copy pre-built virtualenv from build stage
COPY --from=build --chown=app:app /app /app

# Copy built frontend assets
COPY --from=frontend --chown=app:app /app/frontend/dist /app/frontend/dist

# Create data directory for SQLite
RUN mkdir -p /app/data && chown app:app /app/data

USER app
WORKDIR /app

# Smoke test - verify the app can be imported
RUN <<EOT
python -V
python -Im site
python -Ic 'import scribbl_py'
EOT

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Use SIGINT for graceful shutdown
STOPSIGNAL SIGINT

CMD ["uvicorn", "scribbl_py.app:app", "--host", "0.0.0.0", "--port", "8000"]
