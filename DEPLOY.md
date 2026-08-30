# Deployment Guide

## Prerequisites

- A VPS with Docker and Docker Compose installed
- Minimum 1 vCPU, 1GB RAM, 20GB SSD
- A domain name and HTTPS termination (required for production auth cookies)

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
# Do not leave SECRET_KEY empty or use the example placeholder.
# Set the Turnstile site/secret keys and the public hostname as well.

# 4. Start the service
docker compose up -d
# The container runs `alembic upgrade head` before starting Uvicorn.

# 5. Verify it's running
curl http://localhost:8000/healthz
# Expected: {"status":"ok","app":"Aergia CV Builder","version":"0.1.0"}

# 6. Open in browser
# https://your-domain.com
# Port 8000 is loopback-only; access the app through the HTTPS tunnel.
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | **Yes** | — | JWT signing key (generate with `secrets.token_urlsafe(32)`) |
| `ENVIRONMENT` | Fixed by Compose | `production` | Enables production security settings |
| `TURNSTILE_SITE_KEY` | **Yes** | — | Public site key for the registration widget |
| `TURNSTILE_SECRET_KEY` | **Yes** | — | Server-only Turnstile verification secret |
| `TURNSTILE_EXPECTED_HOSTNAME` | **Yes** | — | Public hostname returned by Turnstile |
| `TURNSTILE_EXPECTED_ACTION` | No | `register` | Expected Turnstile action |
| `TURNSTILE_VERIFICATION_TIMEOUT_SECONDS` | No | `3.0` | Bounded server-side provider timeout |
| `TRUSTED_PROXY_IPS` | No | empty | Exact immediate proxy IPs/CIDRs allowed to supply `X-Forwarded-For` |
| `FORWARDED_ALLOW_IPS` | No | empty | Exact Uvicorn proxy peers for forwarded scheme/host handling |

Database configuration is automatic — SQLite stores data in `/app/data/aergia.db` (Docker volume).
Accounts default to the `free` tier, which permits three active applications and
three active CVs. The `premium` tier currently removes those two creation caps
while continuing to maintain the counters. Tier changes are operator-controlled
for now; billing, upgrade UI, and membership workflows are not part of this
deployment.
The limiter uses process-local memory storage and the supplied deployment runs one
Uvicorn process. Adding workers or API replicas requires choosing shared limiter
storage before relying on the configured limits across the fleet.

## Managing the App

```bash
# View logs
docker compose logs -f

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
```

## Database

SQLite stores all data in a single file at `/app/data/aergia.db` (Docker volume `data`).

### Backup
```bash
docker compose cp api:/app/data/aergia.db ./backup-$(date +%Y%m%d).db
```

### Restore
```bash
docker compose cp ./backup.db api:/app/data/aergia.db
docker compose restart api
```

## Uploads

Uploaded photos are stored in a Docker volume (`uploads_data`). To back them up:

```bash
docker run --rm -v aergia_uploads_data:/source -v $(pwd):/backup alpine tar czf /backup/uploads.tar.gz -C /source .
```

## HTTPS & DDoS Protection

Production mode marks authentication cookies as `Secure`, so serve the app
through HTTPS before signing in. The direct port-8000 check is suitable for a
local health check; use the HTTPS domain for the application.

### Option 1: Cloudflare Tunnel (recommended — includes DDoS protection)

1. Point your domain to Cloudflare
2. Install `cloudflared` on the VPS
3. Run: `cloudflared tunnel --url http://localhost:8000`

Cloudflare's free tier includes DDoS mitigation, rate limiting, WAF, and automatic HTTPS.

The Compose file exposes the API only on loopback. With a tunnel or reverse
proxy, set `TRUSTED_PROXY_IPS` to the actual immediate peer seen by the API
and set `FORWARDED_ALLOW_IPS` to the same explicitly known peer set when
forwarded scheme/host handling is required. Leave both empty when there is no
proxy. Never use `*` and never trust an arbitrary client-supplied
`X-Forwarded-For`; the application ignores that header unless the immediate
peer is configured.

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
