#!/usr/bin/env bash
# Phase 8 hardening smoke runner.
# Exercises the HTML-first three-axis architecture end to end without
# touching user data. Runs against a fresh temporary SQLite database and
# the just-built frontend assets, then removes its working directory.
# Lives at <repo>/scripts/smoke.sh; the dispatcher is `dev.sh --smoke`.

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
API_DIR="$ROOT_DIR/api"
WEB_DIR="$ROOT_DIR/web"

# ── Preflight ───────────────────────────────────────────────────────
for cmd in node npm; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command not found on PATH: $cmd" >&2
    exit 1
  fi
done

VENV="$API_DIR/.venv"
for tool in "$VENV/bin/python" "$VENV/bin/pytest" "$VENV/bin/ruff" \
            "$VENV/bin/alembic" "$VENV/bin/uvicorn"; do
  if [[ ! -x "$tool" ]]; then
    echo "ERROR: smoke prerequisite missing: $tool" >&2
    echo "       run ./dev.sh once to install backend dependencies" >&2
    exit 1
  fi
done

for tool in "$WEB_DIR/node_modules/.bin/vitest" \
            "$WEB_DIR/node_modules/.bin/eslint" \
            "$WEB_DIR/node_modules/.bin/vite"; do
  if [[ ! -x "$tool" ]]; then
    echo "ERROR: smoke prerequisite missing: $tool" >&2
    echo "       run ./dev.sh once to install frontend dependencies" >&2
    exit 1
  fi
done

SMOKE_PORT="${AERGIA_SMOKE_PORT:-8765}"
TMP_DIR="$(mktemp -d -t aergia-smoke.XXXXXX)"
SERVER_LOG="$TMP_DIR/server.log"
SERVER_PID=""
PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}"

if ss -tln 2>/dev/null | grep -qE "[:.]${SMOKE_PORT}[[:space:]]"; then
  echo "ERROR: smoke port ${SMOKE_PORT} is already in use; set AERGIA_SMOKE_PORT to a free port" >&2
  exit 2
fi

cleanup() {
  local exit_code=$?
  if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    pkill -P "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  sleep 0.3
  rm -rf "$TMP_DIR"
  exit "$exit_code"
}
trap cleanup EXIT INT TERM

export DATABASE_URL="sqlite+aiosqlite:///$TMP_DIR/aergia-smoke.db"
export API_TEST_DB_URL="$DATABASE_URL"
export ENVIRONMENT=test
export TURNSTILE_BYPASS=true

# ── Stage 1: backend pytest ──────────────────────────────────────────
echo "=== Smoke: backend pytest ==="
(cd "$API_DIR" && "$VENV/bin/pytest" -q)

# ── Stage 2: backend ruff ───────────────────────────────────────────
echo "=== Smoke: backend ruff ==="
(cd "$API_DIR" && "$VENV/bin/ruff" check .)

# ── Stage 3: frontend vitest ─────────────────────────────────────────
echo "=== Smoke: frontend vitest ==="
(cd "$WEB_DIR" && npm run test -- --run)

# ── Stage 4: frontend eslint (React Hooks contract) ─────────────────
echo "=== Smoke: frontend eslint (react-hooks) ==="
(cd "$WEB_DIR" && "$WEB_DIR/node_modules/.bin/eslint" --config "$WEB_DIR/eslint.config.smoke.js" .)

# ── Stage 5: frontend production build ──────────────────────────────
echo "=== Smoke: frontend build ==="
(cd "$WEB_DIR" && npm run build)

# ── Stage 6: live render smoke ───────────────────────────────────────
echo "=== Smoke: live render ==="
SERVER_DIR="$TMP_DIR/api"
mkdir -p "$SERVER_DIR/static"
cp -r "$WEB_DIR/dist/." "$SERVER_DIR/static/"

(cd "$API_DIR" && "$VENV/bin/alembic" upgrade head)

(cd "$SERVER_DIR" \
  && PYTHONPATH="$API_DIR" \
     exec "$VENV/bin/uvicorn" app.main:app \
       --host 127.0.0.1 --port "$SMOKE_PORT" \
       > "$SERVER_LOG" 2>&1) &
SERVER_PID=$!

# Wait for /readyz.
ready=0
for _ in $(seq 1 120); do
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "ERROR: smoke server exited before readiness" >&2
    cat "$SERVER_LOG" >&2
    exit 1
  fi
  body="$(curl -fsS "http://127.0.0.1:${SMOKE_PORT}/readyz" 2>/dev/null || true)"
  if [[ -n "$body" ]] && [[ "$body" == *'"status":"ok"'* ]]; then
    ready=1
    break
  fi
  sleep 0.25
done

if [[ "$ready" -ne 1 ]]; then
  echo "ERROR: smoke server did not become ready within 30s" >&2
  cat "$SERVER_LOG" >&2
  exit 1
fi

# Live checks: register, login, exercise each seed template.
(cd "$API_DIR" && "$VENV/bin/python" "$API_DIR/scripts/smoke_live.py" \
  --base-url "http://127.0.0.1:${SMOKE_PORT}")

echo "SMOKE OK: modern/classic/minimal preview + PDF + built SPA"
