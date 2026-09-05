#!/usr/bin/env bash
# Phase 8 hardening smoke runner.
# Exercises the HTML-first three-axis architecture end to end without
# touching user data. Runs against a fresh temporary SQLite database and
# the just-built TanStack Start server, then removes its working directory. The
# legacy test suite is intentionally deferred until the separate test reset.
# Lives at <repo>/scripts/smoke.sh; the dispatcher is `dev.sh --smoke`.

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
API_DIR="$ROOT_DIR/api"
WEB_DIR="$ROOT_DIR/web"

# ── Preflight ───────────────────────────────────────────────────────
for cmd in node npm timeout; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command not found on PATH: $cmd" >&2
    exit 1
  fi
done

VENV="$API_DIR/.venv"
for tool in "$VENV/bin/python" "$VENV/bin/ruff" \
            "$VENV/bin/alembic" "$VENV/bin/uvicorn"; do
  if [[ ! -x "$tool" ]]; then
    echo "ERROR: smoke prerequisite missing: $tool" >&2
    echo "       run ./dev.sh once to install backend dependencies" >&2
    exit 1
  fi
done

for tool in "$WEB_DIR/node_modules/.bin/eslint" \
            "$WEB_DIR/node_modules/.bin/vite"; do
  if [[ ! -x "$tool" ]]; then
    echo "ERROR: smoke prerequisite missing: $tool" >&2
    echo "       run ./dev.sh once to install frontend dependencies" >&2
    exit 1
  fi
done

SMOKE_PORT="${AERGIA_SMOKE_PORT:-8765}"
WEB_PORT="${AERGIA_SMOKE_WEB_PORT:-$((SMOKE_PORT + 1))}"
SMOKE_MIGRATION_TIMEOUT_SECONDS="${AERGIA_SMOKE_MIGRATION_TIMEOUT_SECONDS:-30}"
TMP_DIR="$(mktemp -d -t aergia-smoke.XXXXXX)"
API_SERVER_LOG="$TMP_DIR/api-server.log"
WEB_SERVER_LOG="$TMP_DIR/web-server.log"
API_SERVER_PID=""
WEB_SERVER_PID=""
PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}"

for port in "$SMOKE_PORT" "$WEB_PORT"; do
  if ss -tln 2>/dev/null | grep -qE "[:.]${port}[[:space:]]"; then
    echo "ERROR: smoke port ${port} is already in use; choose free AERGIA_SMOKE_PORT/AERGIA_SMOKE_WEB_PORT values" >&2
    exit 2
  fi
done

cleanup() {
  local exit_code=$?
  for pid in "$WEB_SERVER_PID" "$API_SERVER_PID"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      pkill -P "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
  done
  sleep 0.3
  rm -rf "$TMP_DIR"
  exit "$exit_code"
}
trap cleanup EXIT INT TERM

export DATABASE_URL="sqlite+aiosqlite:///$TMP_DIR/aergia-smoke.db"
export API_TEST_DB_URL="$DATABASE_URL"
export ENVIRONMENT=test
export TURNSTILE_BYPASS=true

# ── Stage 1: backend ruff ───────────────────────────────────────────
echo "=== Smoke: backend ruff ==="
(cd "$API_DIR" && "$VENV/bin/ruff" check .)

# ── Stage 2: frontend eslint (React Hooks contract) ─────────────────
echo "=== Smoke: frontend eslint (react-hooks) ==="
(cd "$WEB_DIR" && "$WEB_DIR/node_modules/.bin/eslint" --config "$WEB_DIR/eslint.config.smoke.js" .)

# ── Stage 3: frontend production build ──────────────────────────────
echo "=== Smoke: frontend build ==="
(cd "$WEB_DIR" && npm run build)

# ── Stage 4: live Start/API smoke ───────────────────────────────────
echo "=== Smoke: live TanStack Start + FastAPI gateway ==="

if (cd "$API_DIR" && timeout "$SMOKE_MIGRATION_TIMEOUT_SECONDS" "$VENV/bin/alembic" upgrade head); then
  :
else
  migration_status=$?
  if [[ "$migration_status" -eq 124 ]]; then
    echo "ERROR: Alembic migration did not finish within ${SMOKE_MIGRATION_TIMEOUT_SECONDS}s" >&2
    echo "       This usually indicates an async SQLite/runtime compatibility issue." >&2
  else
    echo "ERROR: Alembic migration failed with status ${migration_status}" >&2
  fi
  exit "$migration_status"
fi

(cd "$API_DIR" \
  && FRONTEND_URL="http://127.0.0.1:${WEB_PORT}" \
     PYTHONPATH="$API_DIR" \
     exec "$VENV/bin/uvicorn" app.main:app \
       --host 127.0.0.1 --port "$SMOKE_PORT" \
       > "$API_SERVER_LOG" 2>&1) &
API_SERVER_PID=$!

# Wait for FastAPI /readyz.
api_ready=0
for _ in $(seq 1 120); do
  if ! kill -0 "$API_SERVER_PID" 2>/dev/null; then
    echo "ERROR: FastAPI smoke server exited before readiness" >&2
    cat "$API_SERVER_LOG" >&2
    exit 1
  fi
  body="$(curl -fsS "http://127.0.0.1:${SMOKE_PORT}/readyz" 2>/dev/null || true)"
  if [[ -n "$body" ]] && [[ "$body" == *'"status":"ok"'* ]]; then
    api_ready=1
    break
  fi
  sleep 0.25
done

if [[ "$api_ready" -ne 1 ]]; then
  echo "ERROR: FastAPI smoke server did not become ready within 30s" >&2
  cat "$API_SERVER_LOG" >&2
  exit 1
fi

# Start is the public origin; FastAPI remains the private upstream.
(cd "$WEB_DIR" \
  && AERGIA_API_ORIGIN="http://127.0.0.1:${SMOKE_PORT}" \
     AERGIA_FRONTEND_ORIGIN="http://127.0.0.1:${WEB_PORT}" \
     NODE_ENV=production \
     HOST=127.0.0.1 PORT="$WEB_PORT" \
     exec node .output/server/index.mjs \
       > "$WEB_SERVER_LOG" 2>&1) &
WEB_SERVER_PID=$!

web_ready=0
for _ in $(seq 1 120); do
  if ! kill -0 "$WEB_SERVER_PID" 2>/dev/null; then
    echo "ERROR: TanStack Start smoke server exited before readiness" >&2
    cat "$WEB_SERVER_LOG" >&2
    exit 1
  fi
  if curl -fsS "http://127.0.0.1:${WEB_PORT}/" 2>/dev/null | grep -q "Aergia"; then
    web_ready=1
    break
  fi
  sleep 0.25
done

if [[ "$web_ready" -ne 1 ]]; then
  echo "ERROR: TanStack Start smoke server did not become ready within 30s" >&2
  cat "$WEB_SERVER_LOG" >&2
  exit 1
fi

WEB_URL="http://127.0.0.1:${WEB_PORT}"
home_headers="$TMP_DIR/home.headers"
home_html="$TMP_DIR/home.html"
curl -fsS -D "$home_headers" -o "$home_html" "$WEB_URL/"
grep -q "Aergia" "$home_html"
grep -qi '^x-content-type-options: nosniff' "$home_headers"
grep -qi '^x-frame-options: DENY' "$home_headers"
grep -qi '^referrer-policy: strict-origin-when-cross-origin' "$home_headers"
grep -qi '^permissions-policy: camera=(), microphone=(), geolocation=()' "$home_headers"
csp_header="$(awk 'BEGIN {IGNORECASE=1} /^content-security-policy:/ {sub(/^[^:]*:[[:space:]]*/, ""); print}' "$home_headers")"
[[ "$csp_header" == *"script-src"* ]] && [[ "$csp_header" == *"'nonce-"* ]]
[[ "$csp_header" != *"script-src 'unsafe-inline'"* ]]
csp_nonce="$(printf '%s\n' "$csp_header" | sed -n "s/.*'nonce-\([^']*\)'.*/\1/p")"
[[ -n "$csp_nonce" ]]
grep -Fq "nonce=\"$csp_nonce\"" "$home_html" || grep -Fq "nonce='$csp_nonce'" "$home_html"

second_headers="$TMP_DIR/home-second.headers"
curl -fsS -D "$second_headers" -o /dev/null "$WEB_URL/"
second_csp="$(awk 'BEGIN {IGNORECASE=1} /^content-security-policy:/ {sub(/^[^:]*:[[:space:]]*/, ""); print}' "$second_headers")"
[[ "$csp_header" != "$second_csp" ]]

curl -fsS "$WEB_URL/login" | grep -q "Sign in"
dashboard_headers="$TMP_DIR/dashboard.headers"
curl -fsS -D "$dashboard_headers" -o /dev/null "$WEB_URL/dashboard"
grep -q '^location: /login' "$dashboard_headers"
curl -fsS "$WEB_URL/api/v1/auth/registration-config" | grep -q 'turnstile_required'

cookie_jar="$TMP_DIR/cookies.txt"
smoke_email="smoke-${BASHPID}@example.com"
curl -fsS -c "$cookie_jar" -b "$cookie_jar" \
  -H 'Content-Type: application/json' \
  -X POST "$WEB_URL/api/v1/auth/register" \
  --data "{\"email\":\"${smoke_email}\",\"password\":\"testpass123\"}" \
  >/dev/null
login_headers="$TMP_DIR/login.headers"
curl -fsS -D "$login_headers" -o /dev/null -c "$cookie_jar" -b "$cookie_jar" \
  -H 'Content-Type: application/json' \
  -X POST "$WEB_URL/api/v1/auth/login" \
  --data "{\"email\":\"${smoke_email}\",\"password\":\"testpass123\"}"
grep -q 'aergia_access_token=.*Path=/' "$login_headers"
grep -q 'aergia_refresh_token=.*Path=/' "$login_headers"
curl -fsS -b "$cookie_jar" "$WEB_URL/dashboard" | grep -q 'authenticated:!0'

echo "SMOKE OK: TanStack Start SSR + nonce CSP + FastAPI gateway + root-scoped auth cookies"
