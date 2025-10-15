"""Background cleanup task to purge old exported files."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI

from app.core.config import settings


_task: Optional[asyncio.Task] = None


async def _cleanup_loop() -> None:
    while True:
        try:
            ttl = timedelta(seconds=settings.EXPORT_TTL_SECONDS)
            cutoff = datetime.utcnow() - ttl
            for p in Path(settings.EXPORT_DIR).glob("*"):
                try:
                    if p.is_file() and datetime.utcfromtimestamp(p.stat().st_mtime) < cutoff:
                        p.unlink(missing_ok=True)
                except Exception:
                    # Best-effort cleanup
                    pass
        except Exception:
            pass
        await asyncio.sleep(settings.CLEANUP_INTERVAL_SECONDS)


async def start_cleanup_task(app: FastAPI) -> None:
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_cleanup_loop())


async def stop_cleanup_task(app: FastAPI) -> None:
    global _task
    if _task is not None:
        _task.cancel()
        try:
            await _task
        except Exception:
            pass
        finally:
            _task = None
