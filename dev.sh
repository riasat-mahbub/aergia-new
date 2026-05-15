#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
API_DIR="$ROOT_DIR/api"
WEB_DIR="$ROOT_DIR/web"

# Docker is no longer required for local dev (SQLite replaces PostgreSQL)

# ── Parse flags ──────────────────────────────────────────────────
PROD=false
BUILD=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prod)  PROD=true;  shift ;;
    --build) BUILD=true; shift ;;
    --help)
      echo "Usage: ./dev.sh [--prod] [--build]"
      echo ""
      echo "  --prod    Run uvicorn without --reload (production-like)"
      echo "  --build   Build frontend and serve via FastAPI (no Vite dev server)"
      echo "  --help    Show this message"
      exit 0
      ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
done

# ── Load .env if present ──────────────────────────────────────────
if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

# ── Dependency checks ─────────────────────────────────────────────
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "ERROR: node not found"; exit 1; }
command -v npm  >/dev/null 2>&1 || { echo "ERROR: npm not found"; exit 1; }

# ── Cleanup handler ───────────────────────────────────────────────
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $API_PID 2>/dev/null || true
    [ -n "$WEB_PID" ] && kill $WEB_PID 2>/dev/null || true
    echo "All services stopped."
    exit 0
}
trap cleanup SIGINT SIGTERM

# ── 1. Install API deps ───────────────────────────────────────────
echo "=== Setting up API ==="
if [ ! -d "$API_DIR/.venv" ]; then
    python3 -m venv "$API_DIR/.venv"
fi
# shellcheck disable=SC1091
source "$API_DIR/.venv/bin/activate"
cd "$API_DIR"
pip install -q -e ".[test]"

# Install Playwright browsers if missing
if [ ! -d "$HOME/.cache/ms-playwright" ]; then
    echo "Installing Playwright browsers..."
    python -m playwright install chromium
fi
export PLAYWRIGHT_BROWSERS_PATH="$HOME/.cache/ms-playwright"

# ── 2. Run migrations ─────────────────────────────────────────────
echo "=== Running database migrations ==="
alembic upgrade head

# ── 3. Build frontend (if --build) ────────────────────────────────
if [ "$BUILD" = true ]; then
    echo "=== Building Frontend ==="
    cd "$WEB_DIR"
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    npm run build
    echo "Frontend built to web/dist/"
    STATIC_DIR="$API_DIR/static"
    mkdir -p "$STATIC_DIR"
    cp -r dist/* "$STATIC_DIR/"
    echo "Copied frontend build to $STATIC_DIR"
fi

# ── 4. Start API server ───────────────────────────────────────────
echo "=== Starting API on :8000 ==="
cd "$API_DIR"
UVICORN_OPTS="--host 0.0.0.0 --port 8000"
if [ "$PROD" = false ]; then
    UVICORN_OPTS="$UVICORN_OPTS --reload"
fi
export ENVIRONMENT="${ENVIRONMENT:-development}"
uvicorn app.main:app "$UVICORN_OPTS" &
API_PID=$!

# ── 5. Start frontend dev server (unless --build or --prod) ───────
WEB_PID=""
if [ "$BUILD" = false ] && [ "$PROD" = false ]; then
    echo "=== Starting Frontend on :5173 ==="
    cd "$WEB_DIR"
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    npm run dev &
    WEB_PID=$!
fi

echo ""
echo "==================================="
echo "  Aergia CV Builder is running!"
if [ -n "$WEB_PID" ]; then
    echo "  Frontend: http://localhost:5173"
fi
echo "  API:      http://localhost:8000"
echo "  Press Ctrl+C to stop all services"
echo "==================================="

wait $API_PID $WEB_PID
