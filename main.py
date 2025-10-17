"""FastAPI application entrypoint.

Run locally:
    uvicorn main:app --reload

This app exposes a CSV/Excel processing endpoint under /process/csv.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path

from app.core.config import settings
from app.routers.process import router as process_router


app = FastAPI(title=settings.APP_NAME)

# CORS configuration
allow_origins = (
    [o.strip() for o in settings.CORS_ALLOW_ORIGINS.split(",") if o.strip()]
    if settings.CORS_ALLOW_ORIGINS
    else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure export directory exists before mounting and background tasks start.
settings.EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# Mount exports directory statically to serve downloadable files
app.mount("/downloads", StaticFiles(directory=str(settings.EXPORT_DIR)), name="downloads")

# Serve simple frontend (UI) for testing at /
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def root_ui() -> HTMLResponse:
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(index_path.read_text(encoding="utf-8"))
    return HTMLResponse("<html><body><h1>No UI found</h1></body></html>")

# Routers
app.include_router(process_router, prefix="/process", tags=["processing"])


@app.get("/health", tags=["health"])  # simple health check
async def health() -> dict[str, str]:
    """Health endpoint to verify the app is running."""
    return {"status": "ok"}


# Startup/Shutdown lifecycle hooks
from app.services.cleanup import start_cleanup_task, stop_cleanup_task  # noqa: E402


@app.on_event("startup")
async def on_startup() -> None:
    # Ensure export directory exists (re-try in case mount became available later)
    settings.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    await start_cleanup_task(app)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await stop_cleanup_task(app)
