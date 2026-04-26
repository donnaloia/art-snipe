"""Segmentation client.

Talks to the local SAM service to get pixel-precise masks given bounding boxes,
then falls back to rembg for background cleanup if SAM is unavailable.
"""

from __future__ import annotations

import base64
import io
import os
from pathlib import Path

import httpx
from PIL import Image


def _b64_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def segment_with_sam(
    mockup_path: Path,
    bbox: tuple[int, int, int, int],
    sam_url: str | None = None,
    timeout: float = 60.0,
) -> bytes | None:
    """Send a mockup + bbox to the SAM service. Returns cutout PNG bytes (RGBA) or None on failure."""
    sam_url = sam_url or os.environ.get("SAM_URL", "http://sam:8001")
    payload = {
        "image_b64": _b64_image(mockup_path),
        "box": list(bbox),
    }
    try:
        resp = httpx.post(f"{sam_url}/segment", json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("cutout_b64"):
            return None
        return base64.b64decode(data["cutout_b64"])
    except (httpx.HTTPError, ValueError):
        return None


def remove_background_with_rembg(
    image_bytes: bytes,
    rembg_url: str | None = None,
    timeout: float = 60.0,
) -> bytes | None:
    """Send an image to rembg for background removal. Returns RGBA PNG bytes or None on failure."""
    rembg_url = rembg_url or os.environ.get("REMBG_URL", "http://rembg:7000")
    try:
        resp = httpx.post(
            f"{rembg_url}/api/remove",
            content=image_bytes,
            headers={"Content-Type": "application/octet-stream"},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.content
    except (httpx.HTTPError, ValueError):
        return None


def crop_bbox(mockup_path: Path, bbox: tuple[int, int, int, int]) -> bytes:
    """Naive crop fallback. Returns RGBA PNG bytes of the bbox region."""
    x, y, w, h = bbox
    with Image.open(mockup_path) as img:
        img = img.convert("RGBA")
        crop = img.crop((x, y, x + w, y + h))
        out = io.BytesIO()
        crop.save(out, format="PNG")
        return out.getvalue()


def extract_reference(
    mockup_path: Path,
    bbox: tuple[int, int, int, int],
    target_size: tuple[int, int],
) -> bytes:
    """Best-effort extraction: try SAM, then rembg cleanup of the crop, then raw crop.

    Always returns RGBA PNG bytes scaled to target_size.
    """
    cutout = segment_with_sam(mockup_path, bbox)
    if cutout is None:
        crop = crop_bbox(mockup_path, bbox)
        cutout = remove_background_with_rembg(crop) or crop

    with Image.open(io.BytesIO(cutout)) as img:
        img = img.convert("RGBA")
        resized = img.resize(target_size, Image.LANCZOS)
        out = io.BytesIO()
        resized.save(out, format="PNG")
        return out.getvalue()
