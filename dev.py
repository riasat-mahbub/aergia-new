#!/usr/bin/env python3
"""Run Aergia locally or run the isolated smoke checks."""

import argparse
from contextlib import ExitStack, contextmanager
from http.cookiejar import CookieJar
import io
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, HTTPCookieProcessor, ProxyHandler, Request, build_opener
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parent
API = ROOT / "api"
WEB = ROOT / "web"
VENV = API / ".venv"
WINDOWS = os.name == "nt"
BIN = VENV / ("Scripts" if WINDOWS else "bin")
PYTHON = BIN / ("python.exe" if WINDOWS else "python")
RUFF = BIN / ("ruff.exe" if WINDOWS else "ruff")
WEB_ENTRY = WEB / ".output" / "server" / "index.mjs"
VITE = WEB / "node_modules" / "vite" / "bin" / "vite.js"
ESLINT = WEB / "node_modules" / "eslint" / "bin" / "eslint.js"


def run(args, cwd, env):
    subprocess.run(args, cwd=cwd, env=env, check=True)


@contextmanager
def child(args, cwd, env):
    flags = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if WINDOWS else {"start_new_session": True}
    process = subprocess.Popen(args, cwd=cwd, env=env, **flags)
    try:
        yield process
    finally:
        if WINDOWS:
            if process.poll() is None:
                subprocess.run(
                    ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
                )
            process.wait(timeout=5)
        else:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)
            except ProcessLookupError:
                process.wait()
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()


def initialize(env, npm):
    if not PYTHON.is_file():
        other_python = VENV / ("bin/python" if WINDOWS else "Scripts/python.exe")
        if other_python.is_file():
            raise RuntimeError("api/.venv was created for a different platform. Use a native virtual environment.")
        run([sys.executable, "-m", "venv", VENV], API, env)
    print("=== Installing API dependencies. First-time setup can take several minutes. ===", flush=True)
    run([PYTHON, "-m", "pip", "install", "-q", "-e", ".[test,model]"], API, env)
    dotenv = ROOT / ".env"
    if dotenv.is_file():
        source = (
            "import json, sys; from dotenv import dotenv_values; "
            "print(json.dumps(dotenv_values(sys.argv[1], interpolate=False, encoding='utf-8-sig')))"
        )
        values = subprocess.check_output([PYTHON, "-c", source, dotenv], cwd=ROOT, env=env)
        env.update({key: value for key, value in json.loads(values).items() if value is not None})
    # The Playwright installer checks for the browser version this runtime uses.
    print("=== Checking Chromium for PDF export. Missing browser files will be downloaded. ===", flush=True)
    run([PYTHON, "-m", "playwright", "install", "chromium"], API, env)
    if not env.get("DATABASE_URL"):
        (API / "data").mkdir(exist_ok=True)
    if not VITE.is_file():
        print("=== Installing frontend dependencies ===", flush=True)
        run([npm, "install"], WEB, env)


def setting(env, name, default, maximum):
    try:
        value = int(env.get(name) or default)
    except ValueError:
        value = 0
    if not 1 <= value <= maximum:
        raise RuntimeError(f"{name} must be between 1 and {maximum}.")
    return value


def check_ports(api_port, web_port):
    if api_port == web_port:
        raise RuntimeError("The API and web ports must differ.")
    for port in (api_port, web_port):
        with socket.socket() as probe:
            probe.settimeout(0.5)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError(f"Port {port} is already in use.")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def request(opener, url, payload=None):
    headers = {}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    try:
        response = opener.open(Request(url, data=data, headers=headers), timeout=3)
    except HTTPError as error:
        response = error
    with response:
        return response.status, response.headers, response.read()


def wait_ready(process, opener, url, expected, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Server for {url} exited before readiness (exit {process.returncode}).")
        try:
            code, _, body = request(opener, url)
            if code == 200 and expected in body:
                return
        except (OSError, URLError):
            pass
        time.sleep(0.25)
    raise RuntimeError(f"{url} did not become ready within {timeout} seconds.")


def require(condition, description):
    if not condition:
        raise RuntimeError(f"Smoke check failed for {description}.")


def verify_smoke(opener, origin):
    def get(path):
        return request(opener, origin + path)

    code, headers, home = get("/")
    require(code == 200 and b"Aergia" in home, "SSR homepage")
    for name, value in {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }.items():
        require(headers.get(name) == value, f"homepage {name} header")

    policy = headers.get("Content-Security-Policy", "")
    scripts = re.search(r"(?:^|;\s*)script-src\s+([^;]+)", policy)
    nonce = re.search(r"'nonce-([^']+)'", scripts[1]) if scripts else None
    require(nonce and "'unsafe-inline'" not in scripts[1], "script CSP nonce")
    nonce_value = nonce[1].encode()
    require(b'nonce="' + nonce_value + b'"' in home or b"nonce='" + nonce_value + b"'" in home, "SSR script nonce")
    code, headers, _ = get("/")
    second_policy = headers.get("Content-Security-Policy")
    require(code == 200 and second_policy and second_policy != policy, "per-request CSP nonce")

    code, _, login = get("/login")
    require(code == 200 and b"Sign in" in login, "login page")
    code, headers, _ = get("/dashboard")
    require(300 <= code < 400 and headers.get("Location") == "/login", "anonymous dashboard redirect")
    code, _, config = get("/api/v1/auth/registration-config")
    require(code == 200 and "turnstile_required" in json.loads(config), "registration configuration through the gateway")

    code, headers, bundle = get("/api/v1/tailoring/skill.zip")
    require(
        code == 200
        and headers.get_content_type() == "application/zip"
        and headers.get("X-Aergia-Skill-Protocol-Version") == "10",
        "tailoring skill download",
    )
    with ZipFile(io.BytesIO(bundle)) as archive:
        names = set(archive.namelist())
        require({
            "aergia-tailor/SKILL.md",
            "aergia-tailor/scripts/session.mjs",
            "aergia-tailor/references/natural-writing.md",
        } <= names, "required skill archive entries")
        require(not any(name.endswith(("validate-candidate.mjs", "validate-editorial-review.mjs")) for name in names),
                "skill archive contents")

    credentials = {"email": f"smoke-{secrets.token_hex(8)}@example.com", "password": secrets.token_urlsafe(24)}
    code, _, _ = request(opener, origin + "/api/v1/auth/register", credentials)
    require(200 <= code < 300, "registration through the gateway")
    code, headers, _ = request(opener, origin + "/api/v1/auth/login", credentials)
    require(code == 200, "login through the gateway")
    cookies = [cookie.split(";") for cookie in headers.get_all("Set-Cookie", [])]
    for name in ("access", "refresh"):
        require(any(
            fields[0].startswith(f"aergia_{name}_token=") and "path=/" in [field.strip().lower() for field in fields[1:]]
            for fields in cookies
        ), f"{name} cookie path")
    code, _, dashboard = get("/dashboard")
    require(code == 200 and b"authenticated:!0" in dashboard, "authenticated dashboard SSR")
    print("SMOKE OK: TanStack Start SSR + nonce CSP + FastAPI gateway + root-scoped auth cookies", flush=True)


def launch(options, env, node, npm, stack):
    smoke = options.smoke
    built_server = options.build or options.prod or smoke
    if smoke:
        ruff = Path(env.get("AERGIA_SMOKE_RUFF") or RUFF).expanduser().resolve()
        for path in (PYTHON, ruff, ESLINT, VITE):
            if not path.is_file():
                raise RuntimeError(f"Smoke prerequisite missing at {path}. See api/README.md for setup.")
        api_port = setting(env, "AERGIA_SMOKE_PORT", 8765, 65535)
        web_port = setting(env, "AERGIA_SMOKE_WEB_PORT", api_port + 1, 65535)
        listen = "127.0.0.1"
        public_url = f"http://127.0.0.1:{web_port}"
        origin = public_url
        upstream = f"http://127.0.0.1:{api_port}"
        scratch = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="aergia-smoke-")))
        env.update(
            DATABASE_URL=f"sqlite+aiosqlite:///{(scratch / 'aergia-smoke.db').as_posix()}",
            UPLOADS_PATH=str(scratch / "uploads"),
            ENVIRONMENT="test",
            TURNSTILE_BYPASS="true",
            CSRF_PROTECTION_ENABLED="true",
            ALLOW_BEARER_TOKENS="false",
            EXPOSE_TOKENS_IN_RESPONSE="false",
            SECRET_KEY=secrets.token_urlsafe(32),
        )
    else:
        initialize(env, npm)
        api_port = 8000
        web_port = setting(env, "FRONTEND_PORT", 3000, 65535) if built_server else 5173
        listen = "0.0.0.0"
        public_url = f"http://localhost:{web_port}"
        origin = env.get("AERGIA_FRONTEND_ORIGIN") or env.get("FRONTEND_URL") or public_url
        upstream = env.get("AERGIA_API_ORIGIN") or "http://127.0.0.1:8000"
        env["ENVIRONMENT"] = env.get("ENVIRONMENT") or ("production" if options.prod else "development")
        if env["ENVIRONMENT"].strip().lower() != "production":
            env["TURNSTILE_BYPASS"] = env.get("TURNSTILE_BYPASS") or "true"

    check_ports(api_port, web_port)
    env.update(FRONTEND_URL=origin, AERGIA_FRONTEND_ORIGIN=origin, AERGIA_API_ORIGIN=upstream)
    if smoke:
        print("=== Smoke: backend Ruff ===", flush=True)
        run([ruff, "check", "."], API, env)
        print("=== Smoke: frontend ESLint ===", flush=True)
        run([node, ESLINT, "--config", "eslint.config.smoke.js", "."], WEB, env)
    if smoke or options.build:
        print("=== Building frontend ===", flush=True)
        run([npm, "run", "build"], WEB, env)
    if built_server and not WEB_ENTRY.is_file():
        raise RuntimeError("TanStack Start output is missing. Run python dev.py --build first.")

    print("=== Running database migrations ===", flush=True)
    migration = [PYTHON, "-m", "alembic", "upgrade", "head"]
    if smoke:
        timeout = setting(env, "SMOKE_MIGRATION_TIMEOUT_SECONDS", 30, 2_147_483)
        with child(migration, API, env) as process:
            try:
                status = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired as error:
                raise RuntimeError(f"Alembic did not finish within {timeout} seconds.") from error
            if status:
                raise RuntimeError(f"Alembic failed (exit {status}).")
    else:
        run(migration, API, env)

    opener = build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()), NoRedirect())
    print(f"=== Starting FastAPI on port {api_port} ===", flush=True)
    api_args = [
        PYTHON, "-m", "uvicorn", "app.main:app", "--host", listen, "--port", str(api_port),
        "--forwarded-allow-ips", "" if smoke else env.get("FORWARDED_ALLOW_IPS", ""),
    ]
    if smoke:
        api_args.append("--no-access-log")
    elif not options.prod:
        api_args.append("--reload")
    api = stack.enter_context(child(api_args, API, env))
    wait_ready(api, opener, f"http://127.0.0.1:{api_port}/readyz", b'"status":"ok"', 30 if smoke else 60)

    print(f"=== Starting frontend on port {web_port} ===", flush=True)
    if built_server:
        web_args = [node, WEB_ENTRY]
        web_env = {**env, "NODE_ENV": "production", "HOST": listen, "PORT": str(web_port)}
    else:
        web_args = [node, VITE, "--host", listen, "--port", str(web_port), "--strictPort"]
        web_env = env
    web = stack.enter_context(child(web_args, WEB, web_env))
    wait_ready(web, opener, public_url + "/", b"Aergia", 30 if smoke else 60)
    if smoke:
        verify_smoke(opener, public_url)
        return

    print(f"Frontend {public_url}\nAPI http://localhost:{api_port}\nPress Ctrl+C to stop both services.", flush=True)
    while True:
        for name, process in (("FastAPI", api), ("Frontend", web)):
            if process.poll() is not None:
                raise RuntimeError(f"{name} exited (exit {process.returncode}).")
        time.sleep(0.25)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prod", action="store_true", help="disable API reload and serve a built frontend")
    parser.add_argument("--build", action="store_true", help="build and serve TanStack Start on port 3000")
    parser.add_argument("--smoke", action="store_true", help="lint, build, and run isolated same-origin checks")
    options = parser.parse_args()
    if options.smoke and (options.prod or options.build):
        parser.error("--smoke cannot be combined with --prod or --build")
    if sys.version_info < (3, 12):
        parser.error("Python 3.12 or later is required")
    try:
        node = shutil.which("node")
        npm = shutil.which("npm.cmd" if WINDOWS else "npm")
        if not node or not npm:
            raise RuntimeError("Node.js and npm are required on PATH.")
        with ExitStack() as stack:
            launch(options, os.environ.copy(), node, npm, stack)
    except KeyboardInterrupt:
        print("\nServices stopped.")
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        if isinstance(error, subprocess.CalledProcessError):
            # A failed child may have arguments with local configuration values.
            print(f"Error: command exited with status {error.returncode}.", file=sys.stderr)
        else:
            print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
