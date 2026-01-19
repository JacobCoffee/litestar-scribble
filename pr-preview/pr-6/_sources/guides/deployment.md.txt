# Deployment Guide

This guide covers deploying scribbl-py to production environments.

## Docker Deployment

The recommended way to deploy scribbl-py is with Docker.

### Docker Compose (Recommended)

The simplest way to deploy is with the included `docker-compose.yml`:

```bash
# Build and start
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

### Customizing Docker Compose

Create a `docker-compose.override.yml` for customization:

```yaml
services:
  scribbl:
    environment:
      - DEBUG=false
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/scribbl
      - SESSION_SECRET_KEY=${SESSION_SECRET_KEY}
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - SENTRY_DSN=${SENTRY_DSN}
    ports:
      - "80:8000"
```

### Building the Docker Image

```bash
# Build the image
docker build -t scribbl-py .

# Run the container
docker run -d \
  -p 8000:8000 \
  -v scribbl_data:/app/data \
  -e DATABASE_URL=sqlite:///data/scribbl.db \
  --name scribbl \
  scribbl-py
```

### Multi-Stage Build

The Dockerfile uses a multi-stage build for optimized images:

1. **Build stage** - Installs uv and dependencies
2. **Frontend stage** - Builds frontend assets with Bun
3. **Runtime stage** - Minimal image with only runtime dependencies

Final image size is approximately 200MB.

---

## Production Configuration

### Environment Variables

Create a `.env` file with production settings:

```bash
# Application
DEBUG=false
ENVIRONMENT=production

# Database (PostgreSQL recommended)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/scribbl

# Security (REQUIRED - generate a unique key)
SESSION_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# OAuth (configure at least one provider)
GOOGLE_CLIENT_ID=xxx
GOOGLE_CLIENT_SECRET=xxx
GOOGLE_REDIRECT_URI=https://your-domain.com/auth/callback/google

# Telemetry
SENTRY_DSN=https://xxx@sentry.io/xxx
ENVIRONMENT=production
```

### Database

#### PostgreSQL Setup

For production, use PostgreSQL:

```bash
# Create database
createdb scribbl

# Set connection string
export DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/scribbl

# Run migrations
litestar database upgrade
```

#### Connection Pooling

For high-traffic deployments, consider using PgBouncer or similar connection pooling.

---

## Reverse Proxy Setup

### Nginx

```nginx
upstream scribbl {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # WebSocket support
    location /ws/ {
        proxy_pass http://scribbl;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # HTTP requests
    location / {
        proxy_pass http://scribbl;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files (optional - for CDN offloading)
    location /static/ {
        alias /app/frontend/dist/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Caddy

```caddyfile
your-domain.com {
    reverse_proxy localhost:8000

    # WebSocket routes
    @websockets {
        path /ws/*
    }
    reverse_proxy @websockets localhost:8000
}
```

---

## Health Checks

scribbl-py provides health check endpoints for container orchestration:

### Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/health` | Liveness probe - checks application is running |
| `/ready` | Readiness probe - checks dependencies (database) |

### Docker Health Check

The Dockerfile includes a health check:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1
```

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

---

## Scaling

### Horizontal Scaling

scribbl-py can be horizontally scaled with some considerations:

1. **Database** - Use PostgreSQL (not SQLite)
2. **Sessions** - Use Redis for session storage (planned feature)
3. **WebSockets** - Use a message broker for cross-instance communication

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scribbl
spec:
  replicas: 3
  selector:
    matchLabels:
      app: scribbl
  template:
    metadata:
      labels:
        app: scribbl
    spec:
      containers:
      - name: scribbl
        image: ghcr.io/jacobcoffee/scribbl-py:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: scribbl-secrets
              key: database-url
        - name: SESSION_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: scribbl-secrets
              key: session-secret
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
```

---

## Monitoring

### Structured Logging

scribbl-py uses structlog for structured JSON logging in production:

```bash
# Enable JSON logging
DEBUG=false
```

Log output includes:
- Correlation IDs for request tracing
- Request/response metadata
- Error stack traces

### Sentry Integration

For error tracking and performance monitoring:

```bash
SENTRY_DSN=https://xxx@sentry.io/xxx
SENTRY_TRACES_RATE=0.1
SENTRY_PROFILES_RATE=0.1
ENVIRONMENT=production
```

### PostHog Analytics

For product analytics:

```bash
POSTHOG_API_KEY=phc_xxx
POSTHOG_HOST=https://app.posthog.com
```

---

## Backup & Recovery

### Database Backup

#### PostgreSQL

```bash
# Backup
pg_dump -h localhost -U user scribbl > backup.sql

# Restore
psql -h localhost -U user scribbl < backup.sql
```

#### SQLite

```bash
# Backup
sqlite3 scribbl.db ".backup 'backup.db'"

# Or simply copy the file
cp scribbl.db backup.db
```

### Docker Volumes

```bash
# Backup Docker volume
docker run --rm \
  -v scribbl_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/scribbl_data.tar.gz /data

# Restore
docker run --rm \
  -v scribbl_data:/data \
  -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/scribbl_data.tar.gz --strip 1"
```

---

## Security Checklist

- [ ] Generate unique `SESSION_SECRET_KEY`
- [ ] Use HTTPS in production
- [ ] Configure OAuth redirect URIs for your domain
- [ ] Enable rate limiting
- [ ] Use PostgreSQL instead of SQLite
- [ ] Set `DEBUG=false`
- [ ] Configure Sentry for error tracking
- [ ] Review OAuth scopes and permissions
- [ ] Set up database backups
- [ ] Configure firewall rules
- [ ] Use secrets management (not plain text .env files)

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose logs scribbl

# Common issues:
# - Missing environment variables
# - Database connection failed
# - Port already in use
```

### Database Migration Errors

```bash
# Check current revision
litestar database show-current-revision

# Reset and migrate (destroys data!)
litestar database downgrade base
litestar database upgrade
```

### WebSocket Connection Issues

1. Ensure reverse proxy is configured for WebSocket upgrade
2. Check firewall allows WebSocket connections
3. Verify `X-Forwarded-Proto` header is set correctly

### High Memory Usage

1. Increase container memory limits
2. Check for memory leaks with Sentry profiling
3. Consider connection pooling for database
