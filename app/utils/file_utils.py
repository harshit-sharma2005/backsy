"""Utilities for file handling: downloading, naming, and MIME helpers."""
from __future__ import annotations

import hashlib
import mimetypes
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import httpx

from app.core.config import settings


SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename(name: str, default: str = "file") -> str:
    """Sanitize a filename by removing unsafe characters.

    Args:
        name: Input filename or title.
        default: Fallback base name if result is empty.
    """
    name = name.strip() if name else default
    name = SAFE_FILENAME_RE.sub("_", name)
    name = name.lstrip("._-") or default
    return name[:200]


def guess_extension_from_mime(mime: str) -> Optional[str]:
    """Return a file extension for a given MIME type if known."""
    ext = mimetypes.guess_extension(mime or "")
    # Prefer .xlsx for common excel mimes
    if mime in {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}:
        return ".xlsx"
    if mime in {"application/vnd.ms-excel"}:
        return ".xls"
    return ext


async def download_to_temp(url: str, timeout: float = 30.0) -> Tuple[Path, Optional[str]]:
    """Download the file at URL into the exports directory with a hashed name.

    Returns the local path and the response MIME type if available.
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        content = resp.content
        mime = resp.headers.get("content-type")

    sha = hashlib.sha256(content).hexdigest()[:16]
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    base = f"download_{ts}_{sha}"

    # Guess extension from mime or URL
    ext = None
    if mime:
        ext = guess_extension_from_mime(mime.split(";")[0])
    if not ext:
        # try from URL path
        ext = os.path.splitext(url.split("?")[0].split("#")[0])[1]

    ext = ext or ".csv"
    path = settings.EXPORT_DIR / f"{base}{ext}"
    path.write_bytes(content)
    return path, mime


def build_download_url(relative_path: Path) -> str:
    """Build a download URL path mounted under /downloads."""
    # Ensure path is under the export dir
    rel = relative_path.name if relative_path.is_absolute() else relative_path
    return f"/downloads/{rel}"
