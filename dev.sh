#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
API_DIR="$ROOT_DIR/api"
WEB_DIR="$ROOT_DIR/web"

# Docker is no longer required for local dev (SQLite replaces PostgreSQL)

PROD=false
BUILD=false
SMOKE=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prod)  PROD=true;  shift ;;
    --build) BUILD=true; shift ;;
    --smoke)
      SMOKE=true
      shift
      ;;
    --help)
      echo "Usage: ./dev.sh [--prod] [--build] [--smoke]"
      echo ""
      echo "  --prod    Run uvicorn without --reload (production-like)"
      echo "  --build   Build the TanStack Start server and run it (no Vite dev server)"
      echo "  --smoke   Run backend checks, frontend ESLint/build, and an isolated live-render smoke test"
      exit 0
      ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
done

if [[ "$SMOKE" == true ]]; then
  if [[ "$PROD" == true || "$BUILD" == true ]]; then
    echo "ERROR: --smoke cannot be combined with --prod or --build" >&2
    exit 2
  fi
  exec "$ROOT_DIR/scripts/smoke.sh"
fi

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
# Local runtime exercises application extraction, so install the pinned model
# extra as well as the model-free test dependencies. The model itself remains
# lazy and is downloaded only when the first application is processed.
pip install -q -e ".[test,model]"

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
    echo "TanStack Start server built to web/.output/"
fi

# ── 4. Start API server ───────────────────────────────────────────
echo "=== Starting API on :8000 ==="
cd "$API_DIR"
UVICORN_OPTS=(--host 0.0.0.0 --port 8000)
if [ "$PROD" = false ]; then
    UVICORN_OPTS+=(--reload)
fi
if [ "$PROD" = true ]; then
    export ENVIRONMENT="${ENVIRONMENT:-production}"
else
    export ENVIRONMENT="${ENVIRONMENT:-development}"
fi
export FORWARDED_ALLOW_IPS="${FORWARDED_ALLOW_IPS:-}"
if [ "$ENVIRONMENT" != "production" ]; then
    # Local development has no Turnstile credentials by default. This is an
    # explicit non-production bypass and can be disabled when testing the
    # real integration with TURNSTILE_BYPASS=false.
    export TURNSTILE_BYPASS="${TURNSTILE_BYPASS:-true}"
fi
UVICORN_OPTS+=(--forwarded-allow-ips "$FORWARDED_ALLOW_IPS")
uvicorn app.main:app "${UVICORN_OPTS[@]}" &
API_PID=$!

# ── 5. Start the frontend ────────────────────────────────────────
WEB_PID=""
if [ "$BUILD" = false ] && [ "$PROD" = false ]; then
    echo "=== Starting Frontend on :5173 ==="
    cd "$WEB_DIR"
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    AERGIA_API_ORIGIN="${AERGIA_API_ORIGIN:-http://127.0.0.1:8000}" \
    AERGIA_FRONTEND_ORIGIN="${AERGIA_FRONTEND_ORIGIN:-http://127.0.0.1:5173}" \
      npm run dev -- --host 0.0.0.0 &
    WEB_PID=$!
elif [ "$BUILD" = true ] || [ "$PROD" = true ]; then
    if [ ! -f "$WEB_DIR/.output/server/index.mjs" ]; then
        echo "ERROR: TanStack Start output is missing; run ./dev.sh --build first" >&2
        exit 1
    fi
    FRONTEND_PORT="${FRONTEND_PORT:-3000}"
    echo "=== Starting TanStack Start on :$FRONTEND_PORT ==="
    cd "$WEB_DIR"
    AERGIA_API_ORIGIN="${AERGIA_API_ORIGIN:-http://127.0.0.1:8000}" \
    AERGIA_FRONTEND_ORIGIN="${AERGIA_FRONTEND_ORIGIN:-http://127.0.0.1:$FRONTEND_PORT}" \
    NODE_ENV=production \
    HOST=0.0.0.0 PORT="$FRONTEND_PORT" \
      node .output/server/index.mjs &
    WEB_PID=$!
fi

echo ""
echo "==================================="
echo "  Aergia CV Builder is running!"
if [ -n "$WEB_PID" ]; then
    if [ "$BUILD" = true ] || [ "$PROD" = true ]; then
      echo "  Frontend: http://localhost:${FRONTEND_PORT:-3000}"
    else
      echo "  Frontend: http://localhost:5173"
    fi
fi
echo "  API:      http://localhost:8000"
echo "  Press Ctrl+C to stop all services"
echo "==================================="

wait $API_PID $WEB_PID
