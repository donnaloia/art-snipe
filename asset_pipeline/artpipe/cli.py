from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from PIL import Image

from artpipe.config import (
    REPO_ROOT, ANALYSIS_DIR, MANIFEST_DIR, REFERENCES_DIR,
    GENERATED_DIR, APPROVED_DIR, REJECTED_DIR, LOGS_DIR, EXPORT_DIR,
)
from artpipe.progress import (
    RunStats, append_run_log, console, fmt_money, fmt_duration,
    print_run_footer, print_run_header, progress_bar, spinner, step,
)
from artpipe.providers import get_image_gen_provider, get_vision_provider
from artpipe.schemas.manifest import AssetManifest, AssetSpec
from artpipe.segmenter import extract_reference
from artpipe.variants import (
    apply_deterministic_variant,
    variant_is_deterministic,
    variant_prompt_suffix,
)

load_dotenv(REPO_ROOT / ".env", override=False)


MANIFEST_PATH = MANIFEST_DIR / "asset_manifest.json"
ANALYSIS_PATH = ANALYSIS_DIR / "screen_analysis.json"
RUN_LOG_PATH = LOGS_DIR / "run.log"


def ensure_dirs() -> None:
    for d in [ANALYSIS_DIR, MANIFEST_DIR, REFERENCES_DIR, GENERATED_DIR,
              APPROVED_DIR, REJECTED_DIR, LOGS_DIR, EXPORT_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def _load_manifest() -> AssetManifest:
    if not MANIFEST_PATH.exists():
        console.print(
            f"[red]No manifest found at {MANIFEST_PATH}.[/red] "
            "Run [bold]artpipe analyze --mockup ...[/bold] first."
        )
        sys.exit(1)
    return AssetManifest.model_validate_json(MANIFEST_PATH.read_text())


def _save_manifest(manifest: AssetManifest) -> None:
    MANIFEST_PATH.write_text(manifest.model_dump_json(indent=2))


def _gen_quality() -> str:
    return os.environ.get("ARTPIPE_IMAGE_QUALITY", "medium")


def _finish(run: RunStats, next_steps: str = "") -> None:
    print_run_footer(run, next_steps=next_steps)
    append_run_log(run, RUN_LOG_PATH)


# ────────────────── step implementations ──────────────────

def _do_analyze(run: RunStats, mockup: str, style_hint: str) -> AssetManifest:
    mockup_path = Path(mockup).resolve()
    run.mockup = str(mockup_path)
    with step(run, "analyze") as s:
        provider = get_vision_provider()
        s.extras["provider"] = provider.name
        with spinner(f"Calling {provider.name}..."):
            inferred_style, detected = provider.analyze_mockup(mockup_path, style_hint=style_hint)
        final_style = style_hint or inferred_style
        manifest = AssetManifest(
            project=os.environ.get("ARTPIPE_PROJECT_NAME", "my-game"),
            style=final_style,
            mockup=str(mockup_path),
            assets=[
                AssetSpec(
                    id=a.id,
                    category=a.category,
                    type=a.type,
                    size=a.size,
                    bbox=a.bbox,
                    variants=a.variants,
                    needs_text=a.needs_text,
                    prompt=a.prompt,
                    notes=a.notes,
                )
                for a in detected
            ],
        )
        _save_manifest(manifest)
        ANALYSIS_PATH.write_text(json.dumps({
            "mockup": str(mockup_path),
            "provider": provider.name,
            "style": final_style,
            "asset_count": len(detected),
        }, indent=2))
        s.items = len(detected)
        s.extras["style"] = (final_style[:40] + "…") if len(final_style) > 40 else final_style
    return manifest


def _do_segment(run: RunStats, manifest: AssetManifest) -> None:
    if not manifest.mockup:
        console.print("[red]Manifest has no mockup path. Re-run analyze.[/red]")
        sys.exit(1)
    mockup_path = Path(manifest.mockup)
    if not mockup_path.exists():
        console.print(f"[red]Mockup file not found:[/red] {mockup_path}")
        sys.exit(1)

    boxed = [a for a in manifest.assets if a.bbox is not None]
    skipped = [a.id for a in manifest.assets if a.bbox is None]

    with step(run, "segment") as s:
        if skipped:
            s.extras["skipped"] = str(len(skipped))
        with progress_bar("Extracting references", total=len(boxed)) as bar:
            for asset in boxed:
                bar.set_current(f"{asset.id} [dim]({asset.category})")
                try:
                    out = REFERENCES_DIR / asset.category / f"{asset.id}_reference.png"
                    out.parent.mkdir(parents=True, exist_ok=True)
                    png_bytes = extract_reference(mockup_path, asset.bbox, asset.size)
                    out.write_bytes(png_bytes)
                    s.items += 1
                except Exception as e:
                    s.failures.append(f"{asset.id}: {e}")
                    bar.write(f"[red]✗[/red] {asset.id}: {e}")
                bar.advance()


def _do_generate(
    run: RunStats,
    manifest: AssetManifest,
    candidates: int,
    quality: str,
    use_references: bool,
) -> None:
    provider = get_image_gen_provider()
    full_prompt_prefix = (manifest.style + ". ") if manifest.style else ""
    total_calls = len(manifest.assets)

    estimated_total = sum(
        provider.cost_estimate(a.size, candidates, quality) for a in manifest.assets
    )

    with step(run, "generate") as s:
        s.extras["provider"] = provider.name
        s.extras["quality"] = quality
        s.extras["estimate"] = fmt_money(estimated_total)

        spent = 0.0
        with progress_bar(
            f"Generating ({candidates} per asset, est. {fmt_money(estimated_total)})",
            total=total_calls,
        ) as bar:
            for asset in manifest.assets:
                ref_path = REFERENCES_DIR / asset.category / f"{asset.id}_reference.png"
                ref = ref_path if (use_references and ref_path.exists()) else None
                prompt = (full_prompt_prefix + asset.prompt).strip()
                bar.set_current(
                    f"{asset.id} [dim]({asset.category}) "
                    f"spent={fmt_money(spent)}/{fmt_money(estimated_total)}"
                )
                try:
                    images = provider.generate(
                        prompt=prompt,
                        size=asset.size,
                        reference_path=ref,
                        n=candidates,
                        quality=quality,
                    )
                    spent += provider.cost_estimate(asset.size, candidates, quality)
                    for i, png in enumerate(images, start=1):
                        out = GENERATED_DIR / asset.category / asset.id / f"{asset.id}_v{i:02d}.png"
                        out.parent.mkdir(parents=True, exist_ok=True)
                        out.write_bytes(png)
                    s.items += 1
                except Exception as e:
                    s.failures.append(f"{asset.id}: {e}")
                    bar.write(f"[red]✗[/red] {asset.id}: {e}")
                bar.advance()

        s.extras["spent"] = fmt_money(spent)


def _do_variants(run: RunStats, manifest: AssetManifest, quality: str) -> None:
    provider = None
    full_prompt_prefix = (manifest.style + ". ") if manifest.style else ""

    spent = 0.0
    deterministic_count = 0
    generated_count = 0
    skipped_assets: list[str] = []

    work: list[tuple[AssetSpec, str]] = []
    for asset in manifest.assets:
        base_path = APPROVED_DIR / asset.category / f"{asset.id}_normal.png"
        if not base_path.exists():
            skipped_assets.append(asset.id)
            continue
        for variant in (asset.variants or ["normal"]):
            if variant == "normal":
                continue
            work.append((asset, variant))

    with step(run, "variants") as s:
        if skipped_assets:
            s.extras["skipped"] = str(len(skipped_assets))
        if not work:
            s.extras["note"] = "no work to do"
            return
        with progress_bar("Building variants", total=len(work)) as bar:
            for asset, variant in work:
                base_path = APPROVED_DIR / asset.category / f"{asset.id}_normal.png"
                out = APPROVED_DIR / asset.category / f"{asset.id}_{variant}.png"
                bar.set_current(f"{asset.id} [dim]→[/dim] {variant}")
                try:
                    if variant_is_deterministic(variant):
                        out.write_bytes(apply_deterministic_variant(base_path, variant))
                        deterministic_count += 1
                    else:
                        if provider is None:
                            provider = get_image_gen_provider()
                        prompt = (
                            full_prompt_prefix + asset.prompt + variant_prompt_suffix(variant)
                        ).strip()
                        images = provider.generate(
                            prompt=prompt,
                            size=asset.size,
                            reference_path=base_path,
                            n=1,
                            quality=quality,
                        )
                        out.write_bytes(images[0])
                        spent += provider.cost_estimate(asset.size, 1, quality)
                        generated_count += 1
                    s.items += 1
                except Exception as e:
                    s.failures.append(f"{asset.id}/{variant}: {e}")
                    bar.write(f"[red]✗[/red] {asset.id}/{variant}: {e}")
                bar.advance()

        s.extras["transforms"] = str(deterministic_count)
        s.extras["generated"] = str(generated_count)
        if spent > 0:
            s.extras["spent"] = fmt_money(spent)


def _do_validate(run: RunStats, manifest: AssetManifest) -> bool:
    with step(run, "validate") as s:
        total_variants = sum(len(a.variants or ["normal"]) for a in manifest.assets)
        with progress_bar("Validating approved files", total=total_variants) as bar:
            for asset in manifest.assets:
                for variant in (asset.variants or ["normal"]):
                    bar.set_current(f"{asset.id} [dim]→[/dim] {variant}")
                    path = APPROVED_DIR / asset.category / f"{asset.id}_{variant}.png"
                    if not path.exists():
                        s.failures.append(f"missing {path.name}")
                    else:
                        try:
                            with Image.open(path) as img:
                                if img.size != asset.size:
                                    s.failures.append(
                                        f"{path.name}: size {img.size} != {asset.size}"
                                    )
                                if img.mode != "RGBA":
                                    s.failures.append(f"{path.name}: mode {img.mode} != RGBA")
                        except Exception as e:
                            s.failures.append(f"{path.name}: {e}")
                    s.items += 1
                    bar.advance()
    return not run.steps[-1].failures


def _do_export(run: RunStats) -> int:
    with step(run, "export") as s:
        files = list(APPROVED_DIR.rglob("*.png"))
        if not files:
            s.extras["note"] = "no approved files"
            return 0
        with progress_bar("Copying approved → game_assets", total=len(files)) as bar:
            for src in files:
                rel = src.relative_to(APPROVED_DIR)
                bar.set_current(str(rel))
                dst = EXPORT_DIR / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                s.items += 1
                bar.advance()
        s.extras["target"] = str(EXPORT_DIR)
        return s.items


# ────────────────── click commands ──────────────────

@click.group()
def main() -> None:
    """ArtPipe CLI: AI-driven 2D asset pipeline."""
    ensure_dirs()


@main.command()
@click.option("--mockup", required=True, type=click.Path(exists=True, dir_okay=False))
@click.option("--style", default="", help="Optional style hint to bias asset prompts.")
def analyze(mockup: str, style: str) -> None:
    """Analyze a mockup with the vision provider and create the asset manifest."""
    run = RunStats()
    _do_analyze(run, mockup, style)
    _finish(run)


@main.command()
def manifest() -> None:
    """Validate the existing asset manifest."""
    parsed = _load_manifest()
    console.print(
        f"[green]✓[/green]  manifest valid: [bold]{len(parsed.assets)}[/bold] assets, "
        f"project=[cyan]{parsed.project}[/cyan]"
    )


@main.command()
def segment() -> None:
    """Extract reference cutouts from the mockup using SAM + rembg."""
    run = RunStats()
    parsed = _load_manifest()
    run.mockup = parsed.mockup
    _do_segment(run, parsed)
    _finish(run)


@main.command()
@click.option("--candidates", default=3, help="Candidates to generate per asset.")
@click.option("--quality", default=None, help="Override image gen quality (low/medium/high).")
@click.option("--use-references/--no-references", default=True,
              help="Pass reference cutouts to the image gen model.")
def generate(candidates: int, quality: str | None, use_references: bool) -> None:
    """Generate candidate assets via the image gen provider."""
    run = RunStats()
    parsed = _load_manifest()
    run.mockup = parsed.mockup
    _do_generate(run, parsed, candidates, quality or _gen_quality(), use_references)
    _finish(run)


@main.command()
@click.option("--quality", default=None, help="Override image gen quality (low/medium/high).")
def variants(quality: str | None) -> None:
    """Build all variant files for assets that have an approved 'normal' base."""
    run = RunStats()
    parsed = _load_manifest()
    run.mockup = parsed.mockup
    _do_variants(run, parsed, quality or _gen_quality())
    _finish(run)


@main.command()
def validate() -> None:
    """Validate every approved variant matches the manifest."""
    run = RunStats()
    parsed = _load_manifest()
    run.mockup = parsed.mockup
    ok = _do_validate(run, parsed)
    _finish(run)
    if not ok:
        sys.exit(1)


@main.command("export")
def export_assets() -> None:
    """Copy approved assets into the export folder."""
    run = RunStats()
    _do_export(run)
    _finish(run)


@main.command()
@click.option("--mockup", required=True, type=click.Path(exists=True, dir_okay=False))
@click.option("--style", default="", help="Optional style hint.")
@click.option("--candidates", default=3, help="Candidates per asset.")
@click.option("--quality", default=None, help="Image gen quality (low/medium/high).")
def run(mockup: str, style: str, candidates: int, quality: str | None) -> None:
    """End-to-end: analyze → segment → generate.

    After this, open http://localhost:8473 to approve candidates, then:
    artpipe variants && artpipe validate && artpipe export
    """
    quality = quality or _gen_quality()
    run_stats = RunStats(mockup=str(Path(mockup).resolve()))
    print_run_header(
        f"ArtPipe — {Path(mockup).name}",
        {
            "Project": os.environ.get("ARTPIPE_PROJECT_NAME", "my-game"),
            "Quality": quality,
            "Vision": os.environ.get("ARTPIPE_VISION_PROVIDER", "gemini"),
            "Image-gen": os.environ.get("ARTPIPE_IMAGE_GEN_PROVIDER", "openai"),
            "Candidates": str(candidates),
        },
    )
    manifest_obj = _do_analyze(run_stats, mockup, style)
    _do_segment(run_stats, manifest_obj)
    _do_generate(run_stats, manifest_obj, candidates, quality, use_references=True)
    _finish(
        run_stats,
        next_steps=(
            "[bold cyan]Next:[/bold cyan] open [link=http://localhost:8473]http://localhost:8473[/link] "
            "to approve candidates,\n"
            "      then run [bold]artpipe variants && artpipe validate && artpipe export[/bold]"
        ),
    )
