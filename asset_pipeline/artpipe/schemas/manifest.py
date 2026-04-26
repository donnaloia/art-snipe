from pydantic import BaseModel, Field


class AssetSpec(BaseModel):
    id: str
    category: str
    type: str
    size: tuple[int, int]
    bbox: tuple[int, int, int, int] | None = None
    variants: list[str] = Field(default_factory=lambda: ["normal"])
    needs_text: bool = False
    prompt: str = ""
    notes: str = ""


class AssetManifest(BaseModel):
    project: str = "my-game"
    style: str = ""
    mockup: str = ""
    assets: list[AssetSpec]
