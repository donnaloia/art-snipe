"""Gemini 2.5 Flash vision provider.

Uses Google's free AI Studio tier. Requires GEMINI_API_KEY env var.
Sign up: https://aistudio.google.com/apikey
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from PIL import Image

from artpipe.providers.base import DetectedAsset, VisionProvider


_SYSTEM_INSTRUCTION = """You analyze game UI mockups and identify every distinct
visual asset that would need to be produced as a standalone game asset.

For each asset, return:
- id: snake_case identifier (e.g. "button_end_turn", "icon_health", "card_frame_basic")
- category: one of "ui", "icons", "cards", "characters", "props", "backgrounds", "tiles", "effects"
- type: short description of the asset type (e.g. "button", "icon", "card_frame", "character")
- bbox: [x, y, width, height] in pixel coordinates of the mockup (origin top-left)
- size: [width, height] of the recommended output asset size in pixels (round to multiples of 64)
- variants: list of state variants this asset would need; for buttons use ["normal","hover","pressed","disabled"], for characters use ["idle"], for everything else ["normal"]
- needs_text: true only if the asset MUST contain baked-in text
- prompt: a detailed text-to-image prompt describing the asset's appearance, including style cues, with "transparent background" for non-background assets and "no text" unless needs_text is true
- notes: any additional context (optional)

Also return:
- style: a single sentence describing the overall art style of the mockup (palette, mood, technique)

Skip background pixels you'd render programmatically (solid color fills, gradients without art).
Skip text labels that would be rendered by the game engine.
Group repeated identical assets into a single entry; do not list every instance.
Be exhaustive about distinct visual elements but conservative about what's actually a reusable asset."""


_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "style": {"type": "string"},
        "assets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "category": {"type": "string"},
                    "type": {"type": "string"},
                    "bbox": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 4,
                        "maxItems": 4,
                    },
                    "size": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 2,
                        "maxItems": 2,
                    },
                    "variants": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "needs_text": {"type": "boolean"},
                    "prompt": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["id", "category", "type", "bbox", "size", "prompt"],
            },
        },
    },
    "required": ["style", "assets"],
}


class GeminiVisionProvider(VisionProvider):
    @property
    def name(self) -> str:
        return "gemini"

    def __init__(self, model: str | None = None):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Get a free key at "
                "https://aistudio.google.com/apikey and add it to .env"
            )
        try:
            from google import genai
        except ImportError as e:
            raise RuntimeError(
                "google-genai is not installed. Run `pip install google-genai`."
            ) from e
        self._genai = genai
        self._client = genai.Client(api_key=api_key)
        self._model = model or os.environ.get("ARTPIPE_GEMINI_MODEL", "gemini-2.5-flash")

    def analyze_mockup(
        self,
        mockup_path: Path,
        style_hint: str = "",
    ) -> tuple[str, list[DetectedAsset]]:
        if not mockup_path.exists():
            raise FileNotFoundError(f"Mockup not found: {mockup_path}")

        image = Image.open(mockup_path)
        user_prompt = (
            "Analyze this gameplay mockup and produce the asset list."
        )
        if style_hint:
            user_prompt += f"\n\nStyle hint from the project: {style_hint}"
        user_prompt += f"\n\nThe mockup is {image.width}x{image.height} pixels."

        response = self._client.models.generate_content(
            model=self._model,
            contents=[image, user_prompt],
            config={
                "system_instruction": _SYSTEM_INSTRUCTION,
                "response_mime_type": "application/json",
                "response_schema": _RESPONSE_SCHEMA,
            },
        )

        payload = json.loads(response.text)
        style = payload.get("style", "")
        assets: list[DetectedAsset] = []
        for raw in payload.get("assets", []):
            bbox = tuple(int(v) for v in raw["bbox"])
            size = tuple(int(v) for v in raw["size"])
            assets.append(
                DetectedAsset(
                    id=raw["id"],
                    category=raw["category"],
                    type=raw["type"],
                    bbox=bbox,  # type: ignore[arg-type]
                    size=size,  # type: ignore[arg-type]
                    variants=raw.get("variants") or ["normal"],
                    needs_text=bool(raw.get("needs_text", False)),
                    prompt=raw.get("prompt", ""),
                    notes=raw.get("notes", ""),
                )
            )
        return style, assets
