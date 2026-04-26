from pydantic import BaseModel, Field
from typing import Literal

AssetCategory = Literal["ui", "cards", "icons", "enemies", "backgrounds"]

class AssetSpec(BaseModel):
    id: str
    category: AssetCategory
    type: str
    size: tuple[int, int]
    variants: list[str] = Field(default_factory=list)
    needs_text: bool = False
    prompt: str = ""
    notes: str = ""

class AssetManifest(BaseModel):
    project: str = "go-fish-roguelike-deckbuilder"
    style: str = "dark macabre pixel-inspired"
    assets: list[AssetSpec]
