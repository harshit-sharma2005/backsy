"""FastAPI application entrypoint.

Run locally:
    uvicorn main:app --reload

This app exposes a CSV/Excel processing endpoint under /process/csv.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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

# Mount exports directory statically to serve downloadable files
app.mount("/downloads", StaticFiles(directory=str(settings.EXPORT_DIR)), name="downloads")

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
    await start_cleanup_task(app)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await stop_cleanup_task(app)
