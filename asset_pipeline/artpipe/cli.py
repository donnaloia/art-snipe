from pathlib import Path
import json
import shutil
import click
from rich.console import Console
from PIL import Image, ImageDraw

from artpipe.config import (
    REPO_ROOT, ANALYSIS_DIR, MANIFEST_DIR, REFERENCES_DIR,
    GENERATED_DIR, APPROVED_DIR, GODOT_ASSETS_DIR
)
from artpipe.schemas.manifest import AssetManifest

console = Console()


def ensure_dirs():
    for d in [ANALYSIS_DIR, MANIFEST_DIR, REFERENCES_DIR, GENERATED_DIR, APPROVED_DIR, GODOT_ASSETS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def placeholder_png(path: Path, size: tuple[int, int], label: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", size, (30, 24, 32, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, size[0]-1, size[1]-1], outline=(180, 170, 150, 255), width=3)
    draw.text((12, 12), label[:48], fill=(230, 220, 200, 255))
    img.save(path)


DEFAULT_MANIFEST = {
    "project": "go-fish-roguelike-deckbuilder",
    "style": "dark macabre pixel-inspired gothic card battler",
    "assets": [
        {"id": "button_end_turn", "category": "ui", "type": "button", "size": [320, 96], "variants": ["normal", "hover", "pressed", "disabled"], "needs_text": False, "prompt": "Ornate gothic end turn button frame, transparent background, no text."},
        {"id": "panel_action_counter", "category": "ui", "type": "panel", "size": [256, 96], "variants": ["normal"], "needs_text": False, "prompt": "Small gothic UI panel for action counter, transparent background, no text."},
        {"id": "card_frame_basic", "category": "cards", "type": "card_frame", "size": [256, 384], "variants": ["normal", "selected", "disabled"], "needs_text": False, "prompt": "Dark macabre pixel-inspired card frame, empty center, transparent background."},
        {"id": "card_back_cursed", "category": "cards", "type": "card_back", "size": [256, 384], "variants": ["normal"], "needs_text": False, "prompt": "Cursed gothic card back with bone ornamentation and occult pattern."},
        {"id": "icon_heart", "category": "icons", "type": "icon", "size": [64, 64], "variants": ["normal"], "needs_text": False, "prompt": "Small readable gothic heart health icon, transparent background."},
        {"id": "icon_coin", "category": "icons", "type": "icon", "size": [64, 64], "variants": ["normal"], "needs_text": False, "prompt": "Small tarnished gold coin icon, transparent background."},
        {"id": "enemy_collector_idle", "category": "enemies", "type": "character", "size": [512, 512], "variants": ["idle", "damaged"], "needs_text": False, "prompt": "Dark macabre pixel-inspired card opponent called The Collector, transparent background."},
        {"id": "background_table_room", "category": "backgrounds", "type": "background", "size": [1920, 1080], "variants": ["normal"], "needs_text": False, "prompt": "16:9 dark gothic card room background, table foreground, no characters, no UI."}
    ]
}


@click.group()
def main():
    """ArtPipe CLI: local AI art pipeline scaffold."""
    ensure_dirs()


@main.command()
@click.option("--mockup", required=True, type=click.Path())
def analyze(mockup):
    """Analyze mockup and create a screen analysis JSON placeholder."""
    mockup_path = Path(mockup)
    out = ANALYSIS_DIR / "screen_analysis.json"
    analysis = {
        "mockup": str(mockup_path),
        "status": "placeholder",
        "layout": {
            "top": "enemy/opponent area",
            "center": "play area/table",
            "bottom": "player hand/action cards",
            "sides": "stats, deck, discard, relics"
        },
        "style": DEFAULT_MANIFEST["style"],
        "next_step": "Replace this with vision model output when integrated."
    }
    out.write_text(json.dumps(analysis, indent=2))
    console.print(f"[green]Wrote[/green] {out}")


@main.command()
def manifest():
    """Create and validate the default asset manifest."""
    out = MANIFEST_DIR / "asset_manifest.json"
    if not out.exists():
        out.write_text(json.dumps(DEFAULT_MANIFEST, indent=2))
    parsed = AssetManifest.model_validate_json(out.read_text())
    console.print(f"[green]Manifest valid:[/green] {len(parsed.assets)} assets at {out}")


@main.command()
def segment():
    """Create rough reference placeholders for assets."""
    manifest_path = MANIFEST_DIR / "asset_manifest.json"
    parsed = AssetManifest.model_validate_json(manifest_path.read_text())
    for asset in parsed.assets:
        path = REFERENCES_DIR / asset.category / f"{asset.id}_reference.png"
        placeholder_png(path, asset.size, f"REFERENCE\n{asset.id}")
    console.print(f"[green]Created reference placeholders in[/green] {REFERENCES_DIR}")


@main.command()
def generate():
    """Create generated asset candidate placeholders."""
    parsed = AssetManifest.model_validate_json((MANIFEST_DIR / "asset_manifest.json").read_text())
    for asset in parsed.assets:
        for i in range(1, 4):
            path = GENERATED_DIR / asset.category / asset.id / f"{asset.id}_v{i:02d}.png"
            placeholder_png(path, asset.size, f"CANDIDATE {i}\n{asset.id}")
    console.print(f"[green]Created generated candidate placeholders in[/green] {GENERATED_DIR}")


@main.command()
def variants():
    """Create simple placeholder variants for approved assets."""
    parsed = AssetManifest.model_validate_json((MANIFEST_DIR / "asset_manifest.json").read_text())
    for asset in parsed.assets:
        variants = asset.variants or ["normal"]
        for variant in variants:
            path = APPROVED_DIR / asset.category / f"{asset.id}_{variant}.png"
            placeholder_png(path, asset.size, f"APPROVED\n{asset.id}\n{variant}")
    console.print(f"[green]Created approved variant placeholders in[/green] {APPROVED_DIR}")


@main.command()
def validate():
    """Validate approved PNGs against the manifest."""
    parsed = AssetManifest.model_validate_json((MANIFEST_DIR / "asset_manifest.json").read_text())
    failures = []
    for asset in parsed.assets:
        variants = asset.variants or ["normal"]
        for variant in variants:
            path = APPROVED_DIR / asset.category / f"{asset.id}_{variant}.png"
            if not path.exists():
                failures.append(f"Missing {path}")
                continue
            with Image.open(path) as img:
                if img.size != asset.size:
                    failures.append(f"Wrong size {path}: {img.size} != {asset.size}")
                if img.mode != "RGBA":
                    failures.append(f"Not RGBA {path}")
    if failures:
        for failure in failures:
            console.print(f"[red]{failure}[/red]")
        raise SystemExit(1)
    console.print("[green]All approved assets validated.[/green]")


@main.command("export")
def export_assets():
    """Export approved assets into the Godot asset folders."""
    if not APPROVED_DIR.exists():
        console.print("[yellow]No approved assets found. Run `artpipe variants` first in this scaffold.[/yellow]")
        return
    for src in APPROVED_DIR.rglob("*.png"):
        rel = src.relative_to(APPROVED_DIR)
        dst = GODOT_ASSETS_DIR / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    console.print(f"[green]Exported approved assets to[/green] {GODOT_ASSETS_DIR}")


@main.command()
@click.option("--mockup", required=True, type=click.Path())
def run(mockup):
    """Run the scaffold pipeline end-to-end with placeholders."""
    ctx = click.get_current_context()
    for cmd, kwargs in [
        (analyze, {"mockup": mockup}),
        (manifest, {}),
        (segment, {}),
        (generate, {}),
        (variants, {}),
        (validate, {}),
        (export_assets, {}),
    ]:
        ctx.invoke(cmd, **kwargs)
