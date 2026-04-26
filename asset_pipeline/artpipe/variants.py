"""Variant generation.

For known UI states (hover, pressed, disabled, selected), apply deterministic
PIL transforms — fast, free, perfectly consistent with the base asset.

For variants the transforms don't cover, fall back to image-gen with a prompt
suffix describing the variant.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Callable

from PIL import Image, ImageEnhance, ImageOps


def _load(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def _to_png_bytes(img: Image.Image) -> bytes:
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def _hover(img: Image.Image) -> Image.Image:
    return ImageEnhance.Brightness(img).enhance(1.18)


def _pressed(img: Image.Image) -> Image.Image:
    return ImageEnhance.Brightness(img).enhance(0.78)


def _disabled(img: Image.Image) -> Image.Image:
    rgb = img.convert("RGB")
    grey = ImageOps.grayscale(rgb).convert("RGB")
    blended = Image.blend(rgb, grey, 0.85)
    out = blended.convert("RGBA")
    out.putalpha(img.split()[-1])
    out = ImageEnhance.Brightness(out).enhance(0.7)
    a = out.split()[-1].point(lambda p: int(p * 0.7))
    out.putalpha(a)
    return out


def _selected(img: Image.Image) -> Image.Image:
    enhancer = ImageEnhance.Color(img)
    boosted = enhancer.enhance(1.25)
    return ImageEnhance.Brightness(boosted).enhance(1.1)


def _damaged(img: Image.Image) -> Image.Image:
    r, g, b, a = img.split()
    r = r.point(lambda p: min(255, int(p * 1.2)))
    g = g.point(lambda p: int(p * 0.85))
    b = b.point(lambda p: int(p * 0.85))
    return Image.merge("RGBA", (r, g, b, a))


_DETERMINISTIC: dict[str, Callable[[Image.Image], Image.Image]] = {
    "normal": lambda img: img,
    "hover": _hover,
    "pressed": _pressed,
    "disabled": _disabled,
    "selected": _selected,
    "damaged": _damaged,
}


def variant_is_deterministic(name: str) -> bool:
    return name in _DETERMINISTIC


def apply_deterministic_variant(base_path: Path, variant: str) -> bytes:
    """Apply a known PIL transform to the base PNG. Returns PNG bytes."""
    if variant not in _DETERMINISTIC:
        raise ValueError(f"No deterministic transform for variant {variant!r}")
    img = _load(base_path)
    return _to_png_bytes(_DETERMINISTIC[variant](img))


def variant_prompt_suffix(variant: str) -> str:
    """For non-deterministic variants, build a prompt suffix to send to the image gen model."""
    suffixes = {
        "idle": ", idle pose",
        "attack": ", attacking pose, mid-action",
        "walk": ", walking pose, mid-stride",
        "death": ", defeated pose, on the ground",
        "win": ", victory pose, arms raised",
    }
    return suffixes.get(variant, f", {variant.replace('_', ' ')} variant")
