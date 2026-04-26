"""Abstract provider interfaces.

Concrete implementations live in `artpipe.providers.vision.*` and
`artpipe.providers.image_gen.*`. The factory in `artpipe.providers.factory`
selects an implementation based on environment variables.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DetectedAsset:
    """A single asset identified inside a mockup by a vision model."""

    id: str
    category: str
    type: str
    bbox: tuple[int, int, int, int]
    size: tuple[int, int]
    variants: list[str] = field(default_factory=lambda: ["normal"])
    needs_text: bool = False
    prompt: str = ""
    notes: str = ""


class VisionProvider(ABC):
    """Looks at an image and produces structured information about it."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def analyze_mockup(
        self,
        mockup_path: Path,
        style_hint: str = "",
    ) -> tuple[str, list[DetectedAsset]]:
        """Analyze a mockup and return (inferred_style, list_of_assets).

        Each detected asset has a bounding box (x, y, w, h) in the mockup's
        pixel coordinates and a target output size for generation.
        """


class ImageGenProvider(ABC):
    """Generates new images from text prompts and optional reference images."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def generate(
        self,
        prompt: str,
        size: tuple[int, int],
        reference_path: Path | None = None,
        n: int = 1,
        quality: str = "medium",
    ) -> list[bytes]:
        """Return n generated images as raw PNG bytes (RGBA where supported)."""

    def cost_estimate(self, size: tuple[int, int], n: int, quality: str) -> float:
        """Estimated USD cost of one `generate` call. Free providers return 0."""
        return 0.0
