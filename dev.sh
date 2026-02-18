#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
API_DIR="$ROOT_DIR/api"
WEB_DIR="$ROOT_DIR/web"

# ── Dependency checks ──────────────────────────────────────────────
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found"; exit 1; }
command -v pip3 >/dev/null 2>&1 || command -v pip >/dev/null 2>&1 || { echo "ERROR: pip not found"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "ERROR: node not found"; exit 1; }
command -v npm  >/dev/null 2>&1 || { echo "ERROR: npm not found"; exit 1; }

PIP="$(command -v pip3 || command -v pip)"

# Detect docker compose command
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
elif docker-compose --version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
else
    echo "ERROR: neither 'docker compose' nor 'docker-compose' found"
    exit 1
fi

# ── Cleanup handler ────────────────────────────────────────────────
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $API_PID 2>/dev/null || true
    kill $WEB_PID 2>/dev/null || true
    $DOCKER_COMPOSE -f "$ROOT_DIR/docker-compose.yml" stop 2>/dev/null || true
    echo "All services stopped."
    exit 0
}
trap cleanup SIGINT SIGTERM

# ── 1. Start PostgreSQL ────────────────────────────────────────────
echo "=== Starting PostgreSQL ==="
$DOCKER_COMPOSE -f "$ROOT_DIR/docker-compose.yml" up -d postgres

echo "Waiting for PostgreSQL to be ready..."
for i in $(seq 1 30); do
    if $DOCKER_COMPOSE -f "$ROOT_DIR/docker-compose.yml" exec -T postgres pg_isready -U aergia_user >/dev/null 2>&1; then
        echo "PostgreSQL is ready."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "ERROR: PostgreSQL failed to start within 30 seconds"
        exit 1
    fi
    sleep 1
done

# ── 2. Install API deps ────────────────────────────────────────────
echo "=== Setting up API ==="
if [ ! -d "$API_DIR/.venv" ]; then
    python3 -m venv "$API_DIR/.venv"
fi
source "$API_DIR/.venv/bin/activate"
cd "$API_DIR"
$PIP install -q -e ".[test]"

# ── 3. Run migrations ──────────────────────────────────────────────
echo "=== Running database migrations ==="
alembic upgrade head

# ── 4. Start API server ────────────────────────────────────────────
echo "=== Starting API on :8000 ==="
cd "$API_DIR"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

# ── 5. Install frontend deps ───────────────────────────────────────
echo "=== Setting up Frontend ==="
if [ ! -d "$WEB_DIR/node_modules" ]; then
    cd "$WEB_DIR" && npm install
fi

# ── 6. Start frontend dev server ───────────────────────────────────
echo "=== Starting Frontend on :5173 ==="
cd "$WEB_DIR"
npm run dev &
WEB_PID=$!

echo ""
echo "==================================="
echo "  Aergia CV Builder is running!"
echo "  Frontend: http://localhost:5173"
echo "  API:      http://localhost:8000"
echo "  Press Ctrl+C to stop all services"
echo "==================================="

wait $API_PID $WEB_PID
