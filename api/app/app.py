from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.core.rate_limit import limiter
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
from app.services.renderer._pdf_runtime import close_browser as _close_browser

settings = get_settings()

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
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

if settings.environment != "production":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=False,
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
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": str(e)},
        )

    return {"status": "ok", "database": db_status, "version": settings.app_version}


STATIC_DIR = Path("./static")

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    uploads_dir = Path(settings.uploads_path)
    if uploads_dir.exists():
        app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = STATIC_DIR / full_path.replace("..", "")
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
