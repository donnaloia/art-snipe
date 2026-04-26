"""Provider selection based on environment variables.

Env vars:
    ARTPIPE_VISION_PROVIDER     (default: "gemini")
    ARTPIPE_IMAGE_GEN_PROVIDER  (default: "openai")
"""

from __future__ import annotations

import os

from artpipe.providers.base import VisionProvider, ImageGenProvider


def get_vision_provider() -> VisionProvider:
    name = os.environ.get("ARTPIPE_VISION_PROVIDER", "gemini").lower()
    if name == "gemini":
        from artpipe.providers.vision.gemini import GeminiVisionProvider
        return GeminiVisionProvider()
    raise ValueError(
        f"Unknown vision provider '{name}'. "
        "Supported: gemini. Set ARTPIPE_VISION_PROVIDER."
    )


def get_image_gen_provider() -> ImageGenProvider:
    name = os.environ.get("ARTPIPE_IMAGE_GEN_PROVIDER", "openai").lower()
    if name == "openai":
        from artpipe.providers.image_gen.openai_provider import OpenAIImageGenProvider
        return OpenAIImageGenProvider()
    raise ValueError(
        f"Unknown image gen provider '{name}'. "
        "Supported: openai. Set ARTPIPE_IMAGE_GEN_PROVIDER."
    )
