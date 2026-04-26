"""OpenAI gpt-image-1 image generation provider.

Requires OPENAI_API_KEY env var. Pricing (medium quality, 1024x1024):
  ~$0.042 per image. See https://openai.com/api/pricing/

Quality levels accepted: "low", "medium", "high".
"""

from __future__ import annotations

import base64
import io
import os
from pathlib import Path

from PIL import Image

from artpipe.providers.base import ImageGenProvider


_VALID_QUALITIES = {"low", "medium", "high"}
_VALID_SIZES = {(1024, 1024), (1536, 1024), (1024, 1536)}

# Approximate USD cost per image at 1024x1024. Larger sizes scale roughly
# linearly with pixel count. Source: OpenAI pricing page (gpt-image-1).
_COST_PER_IMAGE = {
    "low": 0.011,
    "medium": 0.042,
    "high": 0.167,
}


def _nearest_supported_size(target: tuple[int, int]) -> tuple[int, int]:
    """gpt-image-1 only supports a few sizes. Pick the closest by aspect ratio."""
    tw, th = target
    target_aspect = tw / th
    best = min(
        _VALID_SIZES,
        key=lambda s: abs((s[0] / s[1]) - target_aspect),
    )
    return best


class OpenAIImageGenProvider(ImageGenProvider):
    @property
    def name(self) -> str:
        return "openai"

    def __init__(self, model: str | None = None):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Get a key at "
                "https://platform.openai.com/api-keys and add it to .env"
            )
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError(
                "openai is not installed. Run `pip install openai`."
            ) from e
        self._client = OpenAI(api_key=api_key)
        self._model = model or os.environ.get("ARTPIPE_OPENAI_IMAGE_MODEL", "gpt-image-1")

    def generate(
        self,
        prompt: str,
        size: tuple[int, int],
        reference_path: Path | None = None,
        n: int = 1,
        quality: str = "medium",
    ) -> list[bytes]:
        if quality not in _VALID_QUALITIES:
            raise ValueError(f"quality must be one of {_VALID_QUALITIES}, got {quality!r}")

        api_size = _nearest_supported_size(size)
        api_size_str = f"{api_size[0]}x{api_size[1]}"

        if reference_path is not None and reference_path.exists():
            with reference_path.open("rb") as f:
                response = self._client.images.edit(
                    model=self._model,
                    image=f,
                    prompt=prompt,
                    n=n,
                    size=api_size_str,
                    quality=quality,
                    background="transparent",
                )
        else:
            response = self._client.images.generate(
                model=self._model,
                prompt=prompt,
                n=n,
                size=api_size_str,
                quality=quality,
                background="transparent",
            )

        results: list[bytes] = []
        for item in response.data:
            png_bytes = base64.b64decode(item.b64_json)
            if api_size != size:
                png_bytes = _resize_png(png_bytes, size)
            results.append(png_bytes)
        return results

    def cost_estimate(self, size: tuple[int, int], n: int, quality: str) -> float:
        per_image = _COST_PER_IMAGE.get(quality, _COST_PER_IMAGE["medium"])
        api_size = _nearest_supported_size(size)
        scale = (api_size[0] * api_size[1]) / (1024 * 1024)
        return per_image * scale * n


def _resize_png(png_bytes: bytes, target: tuple[int, int]) -> bytes:
    """Resize generated PNG to the target size requested by the manifest."""
    with Image.open(io.BytesIO(png_bytes)) as img:
        img = img.convert("RGBA")
        resized = img.resize(target, Image.LANCZOS)
        out = io.BytesIO()
        resized.save(out, format="PNG")
        return out.getvalue()
