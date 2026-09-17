"""Start an isolated Aergia API and public web server for a capture run."""

from __future__ import annotations

import os
import secrets
import signal
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from subprocess import CompletedProcess
from urllib.error import URLError
from urllib.request import urlopen

from .config import ShowcaseConfig
from .migrate import migrate_database


class ShowcaseEnvironment:
    """Context manager for a disposable, production-shaped local instance."""

    def __init__(self, config: ShowcaseConfig, *, build: bool = True) -> None:
        self.config = config
        self.build = build
        self._temporary_directory: tempfile.TemporaryDirectory[str] | None = None
        self.runtime_dir: Path | None = None
        self._processes: list[tuple[str, subprocess.Popen[bytes], object]] = []
        self._environment: dict[str, str] | None = None

    @property
    def environment(self) -> dict[str, str]:
        if self._environment is None:
            raise RuntimeError("showcase environment has not started")
        return self._environment

    def __enter__(self) -> "ShowcaseEnvironment":
        self._temporary_directory = tempfile.TemporaryDirectory(prefix="aergia-showcase-")
        self.runtime_dir = Path(self._temporary_directory.name)
        try:
            print("[showcase] checking prerequisites", flush=True)
            self._preflight()
            print("[showcase] preparing the web build", flush=True)
            self._prepare_frontend()
            print("[showcase] creating the isolated database", flush=True)
            self._apply_migrations()
            print("[showcase] starting FastAPI", flush=True)
            self._start_api()
            print("[showcase] starting the public web server", flush=True)
            self._start_web()
            print("[showcase] local Aergia instance is ready", flush=True)
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, _exc_type, _exc_value, _traceback) -> None:
        self._stop_processes()
        if self._temporary_directory is not None:
            self._temporary_directory.cleanup()
            self._temporary_directory = None
        self.runtime_dir = None

    def _preflight(self) -> None:
        required = (
            self.config.python_bin,
            self.config.alembic_bin,
            self.config.web_dir / "node_modules" / ".bin" / "vite",
        )
        if not self.build:
            required += (self.config.web_dir / ".output" / "server" / "index.mjs",)
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            message = "showcase prerequisites missing:\n" + "\n".join(f"- {path}" for path in missing)
            if any(path.endswith("index.mjs") for path in missing):
                message += "\nRun `cd web && npm run build` or omit --skip-build."
            raise RuntimeError(message)
        for command in ("node", "npm", "ffmpeg", "ffprobe"):
            if not _command_exists(command):
                raise RuntimeError(f"required command not found on PATH: {command}")
        for port in (self.config.api_port, self.config.web_port):
            if _port_is_in_use(port):
                raise RuntimeError(
                    f"showcase port {port} is already in use; set AERGIA_SHOWCASE_API_PORT "
                    "and AERGIA_SHOWCASE_WEB_PORT to free ports"
                )

    def _base_environment(self) -> dict[str, str]:
        if self.runtime_dir is None:
            raise RuntimeError("showcase runtime directory is unavailable")
        database_path = self.runtime_dir / "aergia-showcase.db"
        return {
            **os.environ,
            "DATABASE_URL": f"sqlite+aiosqlite:///{database_path}",
            "ENVIRONMENT": "test",
            "TURNSTILE_BYPASS": "true",
            "CSRF_PROTECTION_ENABLED": "true",
            "ALLOW_BEARER_TOKENS": "false",
            "EXPOSE_TOKENS_IN_RESPONSE": "false",
            "SECRET_KEY": secrets.token_urlsafe(32),
            "UPLOADS_PATH": str(self.runtime_dir / "uploads"),
            "PARSER_BACKEND": "pdfplumber",
            "FRONTEND_URL": self.config.web_url,
        }

    def _prepare_frontend(self) -> None:
        if not self.build:
            return
        result = self._run(
            ["npm", "run", "build"],
            cwd=self.config.web_dir,
            env=os.environ.copy(),
            timeout=900,
        )
        if result.returncode != 0:
            raise RuntimeError(f"TanStack Start build failed:\n{_tail(result.stdout)}")

    def _apply_migrations(self) -> None:
        self._environment = self._base_environment()
        database_url = self.environment["DATABASE_URL"]
        database_path = Path(database_url.removeprefix("sqlite+aiosqlite:///"))
        migrate_database(self.config, database_path)

    def _start_api(self) -> None:
        log_path = self._require_runtime_dir() / "api.log"
        log_handle = log_path.open("wb")
        process = subprocess.Popen(
            [
                str(self.config.python_bin),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.config.api_port),
            ],
            cwd=self.config.api_dir,
            env=self.environment,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self._processes.append(("FastAPI", process, log_handle))
        self._wait_for_http(f"{self.config.api_url}/readyz", "FastAPI")

    def _start_web(self) -> None:
        log_path = self._require_runtime_dir() / "web.log"
        log_handle = log_path.open("wb")
        web_environment = {
            **self.environment,
            "AERGIA_API_ORIGIN": self.config.api_url,
            "AERGIA_FRONTEND_ORIGIN": self.config.web_url,
            "NODE_ENV": "production",
            "HOST": "127.0.0.1",
            "PORT": str(self.config.web_port),
        }
        process = subprocess.Popen(
            ["node", ".output/server/index.mjs"],
            cwd=self.config.web_dir,
            env=web_environment,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self._processes.append(("TanStack Start", process, log_handle))
        self._wait_for_http(self.config.web_url, "TanStack Start")

    def _wait_for_http(self, url: str, name: str, timeout: float = 45.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self._check_processes()
            try:
                with urlopen(url, timeout=2) as response:
                    if 200 <= response.status < 500:
                        return
            except (OSError, URLError):
                time.sleep(0.25)
        log_tail = ""
        if self.runtime_dir is not None:
            log_path = self.runtime_dir / ("api.log" if name == "FastAPI" else "web.log")
            if log_path.exists():
                log_tail = f"\n\n{log_path.name} tail:\n{_tail(log_path.read_bytes())}"
        raise RuntimeError(f"{name} did not become ready at {url}{log_tail}")

    def _check_processes(self) -> None:
        for name, process, _handle in self._processes:
            if process.poll() is not None:
                raise RuntimeError(f"{name} exited before the showcase was ready")

    def _stop_processes(self) -> None:
        for _name, process, _handle in reversed(self._processes):
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        for _name, process, handle in reversed(self._processes):
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=3)
            if hasattr(handle, "close"):
                handle.close()
        self._processes.clear()

    def _run(
        self,
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        timeout: float,
    ) -> CompletedProcess[bytes]:
        try:
            return subprocess.run(
                command,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            output = exc.stdout if isinstance(exc.stdout, bytes) else (exc.stdout or "").encode()
            raise RuntimeError(
                f"command timed out after {timeout:.0f}s: {' '.join(command)}\n{_tail(output)}"
            ) from exc

    def _require_runtime_dir(self) -> Path:
        if self.runtime_dir is None:
            raise RuntimeError("showcase runtime directory is unavailable")
        return self.runtime_dir


def _command_exists(command: str) -> bool:
    return any((Path(directory) / command).is_file() for directory in os.environ.get("PATH", "").split(os.pathsep))


def _tail(value: bytes, limit: int = 4_000) -> str:
    return value.decode("utf-8", errors="replace")[-limit:].strip()


def _port_is_in_use(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            return sock.connect_ex(("127.0.0.1", port)) == 0
    except PermissionError:
        # Some managed runners prohibit creating probe sockets. The child
        # process and readiness check still provide the authoritative result.
        return False
