from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import get_settings
from app.db.session import async_session
from app.db.seed import seed_templates
from app.routes.auth import router as auth_router
from app.routes.cvs import router as cvs_router
from app.routes.assets import router as assets_router
from app.routes.templates import router as templates_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_session() as session:
        await seed_templates(session)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Build professional CVs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(cvs_router, prefix="/api/v1/cvs")
app.include_router(assets_router, prefix="/api/v1/assets")
app.include_router(templates_router, prefix="/api/v1/templates")


@app.get("/healthz")
async def health():
    return {"status": "ok", "app": settings.app_name}


STATIC_DIR = Path("/app/static")

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.mount("/uploads", StaticFiles(directory="/app/uploads"), name="uploads")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = STATIC_DIR / full_path.replace("..", "")
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
