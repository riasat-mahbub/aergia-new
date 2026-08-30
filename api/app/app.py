from contextlib import asynccontextmanager
import logging
from pathlib import Path
import hmac
import secrets

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.core.abuse import log_abuse_event
from app.core.auth import ACCESS_COOKIE_NAME, CSRF_COOKIE_NAME, REFRESH_COOKIE_NAME
from app.core.rate_limit import get_rate_limit_key, limiter
from app.db.session import async_session
from app.db.seed import seed_templates
from app.routes.auth import router as auth_router
from app.routes.applications import router as applications_router
from app.routes.profile import router as profile_router
from app.routes.cvs import router as cvs_router
from app.routes.library import router as library_router
from app.routes.assets import router as assets_router
from app.routes.templates import router as templates_router
from app.routes.render import router as render_router
from app.routes.imports import router as imports_router
from app.routes.tailoring import router as tailoring_router
from app.services.renderer._pdf_runtime import close_browser as _close_browser

settings = get_settings()
logger = logging.getLogger("aergia.api")

MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
REQUEST_BODY_LIMITS = {
    "/api/v1/render/ast": 2 * 1024 * 1024,
    "/api/v1/render/html": 2 * 1024 * 1024,
    "/api/v1/render/pdf": 2 * 1024 * 1024,
    "/api/v1/cvs/import/pdf": 16 * 1024 * 1024,
    "/api/v1/assets": 6 * 1024 * 1024,
    "/api/v1/tailoring/submit": 512 * 1024,
}

_SENSITIVE_VALIDATION_FIELDS = frozenset({
    "password",
    "old_password",
    "new_password",
    "refresh_token",
    "access_token",
    "api_key",
    "code",
    "capability",
})


def _allowed_origin(origin: str | None) -> bool:
    return bool(origin) and origin.rstrip("/") == settings.frontend_url.rstrip("/")


def _content_security_policy() -> str:
    if settings.environment == "production":
        return (
            "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
            "form-action 'self'; script-src 'self' https://challenges.cloudflare.com; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; "
            "connect-src 'self' https://challenges.cloudflare.com; "
            "frame-src 'self' https://challenges.cloudflare.com"
        )
    return (
        "default-src 'self' http://localhost:5173; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
        "form-action 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://challenges.cloudflare.com; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; "
        "connect-src 'self' http://localhost:5173 ws://localhost:5173 https://challenges.cloudflare.com; "
        "frame-src 'self' https://challenges.cloudflare.com"
    )


def _apply_security_headers(response, request: Request):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = _content_security_policy()
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.environment == "production" and request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if not request.cookies.get(CSRF_COOKIE_NAME):
        response.set_cookie(
            CSRF_COOKIE_NAME,
            secrets.token_urlsafe(32),
            max_age=12 * 60 * 60,
            httponly=False,
            secure=settings.environment == "production",
            samesite="lax",
            path="/",
        )
    return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_session() as session:
        await seed_templates(session)
        await session.commit()
    yield
    await _close_browser()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Build professional CVs",
    lifespan=lifespan,
)

app.state.limiter = limiter


async def rate_limit_exceeded_handler(request: Request, _exc: RateLimitExceeded):
    event = (
        "registration_rate_limited"
        if request.url.path == "/api/v1/auth/register"
        else "rate_limited"
    )
    log_abuse_event(event, route=request.url.path, client_key=get_rate_limit_key(request))
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
if getattr(limiter, "enabled", False):
    # SlowAPI only applies default_limits through its middleware. Decorated
    # routes still retain their more specific limits.
    app.add_middleware(SlowAPIMiddleware)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    limit = REQUEST_BODY_LIMITS.get(request.url.path)
    if limit is not None and request.method in MUTATING_METHODS:
        content_length = request.headers.get("content-length")
        try:
            too_large = content_length is not None and int(content_length) > limit
        except ValueError:
            too_large = False
        if too_large:
            return _apply_security_headers(
                JSONResponse(
                    status_code=413,
                    content={"detail": "Request body is too large"},
                ),
                request,
            )
    if (
        settings.csrf_protection_enabled
        and request.url.path.startswith("/api/")
        and request.method in MUTATING_METHODS
        and (request.cookies.get(ACCESS_COOKIE_NAME) or request.cookies.get(REFRESH_COOKIE_NAME))
    ):
        origin = request.headers.get("origin")
        csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
        csrf_header = request.headers.get("x-csrf-token")
        origin_ok = _allowed_origin(origin)
        token_ok = bool(csrf_cookie and csrf_header and hmac.compare_digest(csrf_cookie, csrf_header))
        if not origin_ok and not token_ok:
            return _apply_security_headers(
                JSONResponse(status_code=403, content={"detail": "CSRF validation failed"}),
                request,
            )

    return _apply_security_headers(await call_next(request), request)

if settings.environment != "production":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(cvs_router, prefix="/api/v1/cvs")
app.include_router(applications_router, prefix="/api/v1/applications")
app.include_router(profile_router, prefix="/api/v1/profile")
app.include_router(library_router, prefix="/api/v1/library")
app.include_router(assets_router, prefix="/api/v1/assets")
app.include_router(templates_router, prefix="/api/v1/templates")
app.include_router(render_router, prefix="/api/v1")
app.include_router(imports_router, prefix="/api/v1")
app.include_router(tailoring_router, prefix="/api/v1")


@app.exception_handler(RequestValidationError)
async def request_validation_error(request: Request, exc: RequestValidationError):
    """Return validation locations without echoing submitted secrets."""

    errors = []
    for error in exc.errors():
        location = list(error.get("loc", ()))
        field = str(location[-1]) if location else ""
        errors.append({
            "loc": location,
            "msg": "Invalid value" if field in _SENSITIVE_VALIDATION_FIELDS else error.get("msg", "Invalid value"),
            "type": error.get("type", "value_error"),
        })
    return JSONResponse(status_code=422, content={"detail": errors})


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    # Log only the exception class and route. Exception messages can contain
    # request data supplied by a parser, provider SDK, or validation layer.
    logger.error(
        "unhandled_api_error",
        extra={"route": request.url.path, "exception_type": type(exc).__name__},
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/healthz")
async def health():
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


@app.get("/readyz")
async def readyz(request: Request):
    from sqlalchemy import text
    from app.db.session import async_session

    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        logger.error("readiness_check_failed", extra={"exception_type": type(e).__name__})
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "unavailable"},
        )

    return {"status": "ok", "database": db_status, "version": settings.app_version}


STATIC_DIR = Path("./static")
STATIC_ROOT = STATIC_DIR.resolve()


def _safe_static_file(full_path: str) -> Path | None:
    """Resolve a SPA asset only when it remains under the static root."""

    candidate = (STATIC_ROOT / full_path).resolve()
    try:
        candidate.relative_to(STATIC_ROOT)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = _safe_static_file(full_path)
        if file_path is not None:
            return FileResponse(file_path)
        return FileResponse(STATIC_ROOT / "index.html")
