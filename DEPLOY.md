# Deployment Guide

## Prerequisites

- A VPS with Docker and Docker Compose installed
- Minimum 2 vCPU, 4GB RAM, 50GB SSD
- A domain name (optional, for HTTPS)

## Quick Start

```bash
# 1. SSH into your VPS
ssh user@your-vps-ip

# 2. Clone the repository
git clone https://github.com/your-org/aergia.git /opt/aergia
cd /opt/aergia

# 3. Set up environment variables
cp .env.example .env
# Edit .env — generate a strong SECRET_KEY:
#   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Set a strong DB_PASS as well

# 4. Start the services
docker compose up -d

# 5. Run database migrations
docker compose exec api alembic upgrade head

# 6. Verify it's running
curl http://localhost:8000/healthz
# Expected: {"status":"ok","app":"Aergia CV Builder","version":"0.1.0"}

# 7. Open in browser
# http://your-vps-ip:8000
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | **Yes** | `change-me-in-production` | JWT signing key (generate with `secrets.token_urlsafe(32)`) |
| `DATABASE_URL` | No | `postgresql+asyncpg://aergia_user:aergia_pass@postgres:5432/aergia` | Postgres connection string |
| `DB_USER` | No | `aergia_user` | Postgres user |
| `DB_PASS` | No | `aergia_pass` | Postgres password |
| `DB_NAME` | No | `aergia` | Postgres database name |

## Managing the App

```bash
# View logs
docker compose logs -f

# View API logs only
docker compose logs -f api

# Restart the API
docker compose restart api

# Stop everything
docker compose down

# Rebuild and restart (after code updates)
git pull
docker compose up -d --build
```

## Updating

```bash
git pull
docker compose up -d --build
docker compose exec api alembic upgrade head
```

## Database

```bash
# Backup
docker compose exec postgres pg_dump -U aergia_user aergia > backup.sql

# Restore
cat backup.sql | docker compose exec -T postgres psql -U aergia_user aergia

# Run migrations
docker compose exec api alembic upgrade head

# Check migration status
docker compose exec api alembic current
```

## Uploads

Uploaded photos are stored in a Docker volume (`uploads_data`). To back them up:

```bash
docker run --rm -v aergia_uploads_data:/source -v $(pwd):/backup alpine tar czf /backup/uploads.tar.gz -C /source .
```

## HTTPS

### Option 1: Cloudflare Tunnel (easiest)

1. Point your domain to Cloudflare
2. Install `cloudflared` on the VPS
3. Run: `cloudflared tunnel --url http://localhost:8000`

### Option 2: Caddy (automatic HTTPS)

Add to `docker-compose.yml` as a sidecar service:

```yaml
  caddy:
    image: caddy:2
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
    depends_on:
      - api

networks:
  aergia:
    driver: bridge
```

Create `Caddyfile`:

```
your-domain.com {
    reverse_proxy api:8000
}
```

## Troubleshooting

**API won't start — "SECRET_KEY is set to the default value"**
→ Generate a real secret key and update your `.env` file.

**PDF export fails**
→ Verify Playwright Chromium is installed: `docker compose exec api python -c "from playwright.sync_api import sync_playwright; print('OK')"`

**Port 8000 already in use**
→ Change the host port mapping in `docker-compose.yml`: `"8000:8000"` → `"8080:8000"`

**Database connection refused**
→ Ensure Postgres is healthy: `docker compose ps` (should show `healthy` under STATUS for postgres)
→ Check the logs: `docker compose logs postgres`
