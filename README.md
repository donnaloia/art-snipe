# Art Snipe

Art Snipe takes a single gameplay mockup and produces a complete, organized set of 2D game-ready asset candidates. Provide one mockup of the screen; the pipeline identifies every distinct asset, generates clean reference cutouts of each, produces multiple stylistically-consistent candidates per asset, lets you approve the ones you like in a local web UI, then auto-generates the missing UI states (hover, pressed, disabled, etc.) and exports everything in the right sizes to a folder your engine can import.

## Why this exists

The first asset pass for a 2D game is one of the most time-consuming and least-creative parts of game development. A typical screen has 20–40 distinct visual elements — buttons, icons, card frames, panels, characters, backgrounds — each of which usually needs multiple state variants. For a small team or solo developer, producing that initial asset set traditionally means one of:

- **Commissioning an artist:** weeks of turnaround, expensive, slow iteration cycles, and the artist still needs a full asset list and style brief from you first.
- **DIY in Photoshop/Aseprite:** dozens of hours of repetitive manual work before you can even playtest the screen.
- **Ad-hoc AI generation (ChatGPT, Midjourney, etc.):** every asset is a one-off conversation with no shared context — drift in style, no consistency in proportions or composition, no automation of variants, manual cropping/resizing/organizing for every single piece, and no record of how anything was made when you need to regenerate.

Art Snipe collapses all of that into a single deterministic pipeline. You go from a rough mockup (even a hand-drawn one) to a folder of categorized, sized, transparent-background PNGs ready for your engine, in roughly the time it takes to drink a coffee. For a 30-asset screen with four state variants each (120 final files), the manual workflows above take 10–20 hours; Art Snipe takes about 30–45 minutes of mostly-unattended runtime plus 15 minutes of human review.

## Where it fits in game development

Art Snipe is built for the parts of the workflow where speed and consistency matter more than artistic originality:

- **Pre-production / style exploration.** Want to compare three different aesthetic directions for the same UI? Run the pipeline three times with different `style` hints. Compare them side-by-side in 90 minutes total instead of weeks of concept art.
- **Production-quality placeholders.** Get assets that look real enough to playtest and demo with — far better than gray-box prototypes, without committing your artist's time.
- **Iterating on game design.** When design changes mid-development (new card type, new enemy archetype, new UI panel), regenerate just the affected assets in the existing project style without breaking visual coherence.
- **Game jams and prototypes.** Most of a 48-hour jam isn't spent on art. Art Snipe can hand you a coherent visual layer in the first hour so you can spend the rest on gameplay.
- **Solo devs and small studios.** When you can't afford a full art team, Art Snipe gets you to a shippable visual standard for the 80% of assets that are functional UI/icons/states, so an actual artist's time can go toward the 20% that defines your game's look (key art, hero characters, signature visuals).

What it doesn't replace: a real art director, original IP design, or signature concept art. Art Snipe fills in the asset volume around a vision you've already established. The mockup you feed it is where the creative work happens; the pipeline turns that vision into deliverable files.

## How it works

The pipeline is seven sequential steps. You start it with one command and a mockup image; the only step that requires you to be present is step 4 (review).

### 1. Analyze

| | |
|---|---|
| **Input** | Your mockup PNG (any resolution, any style — even a hand-drawn photo works) |
| **Powered by** | Gemini 2.5 Flash (free tier, no credit card needed) |
| **What it does** | A vision model examines the mockup and identifies every distinct visual element that should become a reusable asset — buttons, icons, card frames, characters, backgrounds, etc. For each one it figures out a stable ID, a category, the bounding box where it appears, the recommended output size, what state variants it needs (e.g. a button needs `hover`/`pressed`/`disabled`), and writes a detailed text-to-image prompt describing it. |
| **Output** | `workspace/manifests/asset_manifest.json` — a complete, structured asset list, ready for the rest of the pipeline. You can hand-edit this file before continuing if you want to tweak prompts, sizes, or skip assets. |

### 2. Segment

| | |
|---|---|
| **Input** | The manifest from step 1, plus your original mockup |
| **Powered by** | A local SAM v1 model running on your CPU, plus `rembg` for background cleanup |
| **What it does** | For each asset's bounding box, SAM produces a pixel-precise mask of just that element, then rembg strips any leftover background. The result is a clean, transparent-background PNG of each asset as it appears in the mockup. These cutouts aren't final art — they're **reference images** that will guide the next step. |
| **Output** | `workspace/references/<category>/<id>_reference.png` for every asset |

### 3. Generate

| | |
|---|---|
| **Input** | Each asset's prompt and reference cutout from steps 1 and 2 |
| **Powered by** | OpenAI gpt-image-1 (paid, ~$0.04 per image at medium quality) |
| **What it does** | For each asset, the image generator produces 3 candidate versions. The reference cutout tells it the rough shape, proportions, and composition you want; the prompt tells it the style and details. Because all prompts share the same project-level `style` field, every candidate stays visually consistent with every other. |
| **Output** | `workspace/generated/<category>/<id>/<id>_v01.png`, `_v02.png`, `_v03.png` — three options per asset |

### 4. Review (the only manual step)

| | |
|---|---|
| **Input** | All the candidates from step 3 |
| **Powered by** | A local web UI at `http://localhost:8473` |
| **What it does** | The web UI shows each asset alongside its reference cutout and three candidates. You click **Approve** on the one you like, or **Reject** on ones you don't want. Approving sets that candidate as the canonical "normal" state for that asset. Typical review time: ~15–30 minutes for a 30-asset screen. |
| **Output** | `workspace/approved/<category>/<id>_normal.png` for each asset you approve |

### 5. Variants

| | |
|---|---|
| **Input** | Your approved "normal" assets from step 4, and the variants list from the manifest |
| **Powered by** | Local PIL image transforms for known UI states; OpenAI gpt-image-1 for everything else |
| **What it does** | UI state variants like `hover`, `pressed`, `disabled`, `selected`, `damaged` are produced by deterministic image transforms (brighten, darken, desaturate, etc.) applied to the approved base — instant, free, and perfectly consistent with the original. Non-UI variants like character poses (`idle`, `attack`, `walk`) get sent back to the image generator with a variant-specific prompt suffix. |
| **Output** | `workspace/approved/<category>/<id>_<variant>.png` for every variant of every asset |

### 6. Validate

| | |
|---|---|
| **Input** | The full set of approved + variant files |
| **Powered by** | Built-in checks |
| **What it does** | Confirms every variant the manifest expects actually exists, has the correct dimensions, and is RGBA (transparent background) — catches any missed approvals or generation failures before they reach your engine. |
| **Output** | A pass/fail report. Pipeline halts on failure so you can fix and rerun. |

### 7. Export

| | |
|---|---|
| **Input** | The validated approved set |
| **Powered by** | A simple file copy |
| **What it does** | Copies every approved variant into your final asset folder, organized by category. From here, your game engine (Godot, Unity, GameMaker, custom — any engine that imports PNGs) can pull them straight in. |
| **Output** | `game_assets/<category>/<id>_<variant>.png` — your finished asset library |

---

No GPU required. Works on Mac, Linux, and Windows. Steps 1, 3, and the non-UI parts of 5 hit hosted APIs; everything else runs locally on your machine.

## Requirements

- Docker + Docker Compose
- A free [Google AI Studio](https://aistudio.google.com/apikey) account for vision (no card required)
- An [OpenAI API key](https://platform.openai.com/api-keys) for image generation (~$0.04/image at medium quality, ~$4 per full pipeline run on a typical mockup)

## Setup

1. Open `docker-compose.yml` and fill in the two API keys near the top of the `artpipe-cli` service:

   ```yaml
   GEMINI_API_KEY: "your-gemini-key-here"
   OPENAI_API_KEY: "your-openai-key-here"
   ```

2. (Optional but recommended) Stop git from tracking your edits to that file so your keys don't leak into commits:

   ```bash
   git update-index --skip-worktree docker-compose.yml
   ```

3. Bring everything up:

   ```bash
   make up
   ```

First `make up` will take ~5–10 minutes because the SAM service downloads its model (~375 MB) and PyTorch CPU into the container image. Subsequent runs are instant.

## Usage

End-to-end run on one mockup:

```bash
make run MOCKUP=mockups/your_mockup.png
```

That will:

1. **analyze** — vision model identifies every asset in the mockup, returns a fully-populated `workspace/manifests/asset_manifest.json` with bounding boxes, asset IDs, categories, and per-asset prompts
2. **segment** — for each detected asset, SAM extracts a clean cutout from the mockup; rembg cleans up any remaining background; the result is saved to `workspace/references/`
3. **generate** — for each asset, the image gen model produces 3 candidate PNGs in `workspace/generated/<category>/<asset_id>/`

Then open the review UI:

```bash
open http://localhost:8473
```

Click each asset, pick the candidate you like, hit **Approve**. Approved candidates land in `workspace/approved/`.

When you've approved everything you want, finish the pipeline:

```bash
make variants    # produce hover/pressed/disabled/etc. for each approved asset
make validate    # check every approved variant matches manifest specs
make export      # copy approved assets into game_assets/
```

## Folder Overview

```text
asset_pipeline/         Python CLI orchestration code
  artpipe/providers/    Pluggable vision + image gen providers
services/
  sam/                  Local SAM segmentation service (FastAPI)
  review-ui/            Local approve/reject web UI (FastAPI + Jinja2)
workspace/              All intermediate files generated by the pipeline
  manifests/            Asset manifest JSON (auto-generated by analyze)
  references/           Reference cutouts (output of segment)
  generated/            Image generation candidates (output of generate)
  approved/             Candidates promoted by you in the review UI
  rejected/             Candidates you rejected
game_assets/            Final exported assets
mockups/                Source gameplay mockups (input)
models/                 Local model weights cache (gitignored)
docs/                   Pipeline design notes
```

## Make Targets

| target | what it does |
|---|---|
| `make up` | Build images and start sam, rembg, and review-ui in the background |
| `make down` | Stop all services |
| `make logs` | Tail logs from all services |
| `make shell` | Open a bash shell inside the Art Snipe-cli container |
| `make run MOCKUP=...` | analyze + segment + generate end-to-end on one mockup |
| `make analyze MOCKUP=...` | Just the analyze step |
| `make manifest` | Validate the existing manifest |
| `make segment` | Just the segment step (uses manifest's mockup path) |
| `make generate` | Just the generate step |
| `make variants` | Build variants for every approved base asset |
| `make validate` | Check approved assets match manifest specs |
| `make review` | Bring the review UI to the foreground (logs visible) |
| `make export` | Copy approved assets into game_assets/ |
| `make clean` | Wipe workspace/ subdirectories |

## Configuration

All configuration lives in `docker-compose.yml` under the `artpipe-cli` service's `environment` block. The most useful knobs:

- `ARTPIPE_IMAGE_QUALITY: low|medium|high` — image gen quality. Low is ~$0.011/image, medium ~$0.042, high ~$0.167. Default: medium.
- `ARTPIPE_PROJECT_NAME: ...` — project label written into the manifest.
- `ARTPIPE_GEMINI_MODEL: gemini-2.5-flash` — switch to a different Gemini model (e.g. `gemini-2.5-pro`).
- `ARTPIPE_SAM_MODEL: facebook/sam-vit-base` — swap in a larger SAM model (e.g. `facebook/sam-vit-large`). This one lives under the `sam` service, not `artpipe-cli`.

After changing values, run `make down && make up` to rebuild.

## Swapping Providers

The pipeline talks to vision and image-gen providers through abstract interfaces in `asset_pipeline/artpipe/providers/`. To add (for example) a Claude vision provider:

1. Create `asset_pipeline/artpipe/providers/vision/claude.py` implementing `VisionProvider`.
2. Register it in `asset_pipeline/artpipe/providers/factory.py`.
3. Set `ARTPIPE_VISION_PROVIDER: claude` in `docker-compose.yml`.

No other code changes required.

## Costs

Default config (Gemini Flash + gpt-image-1 medium):

- **Vision (analyze):** Free (Gemini Flash free tier; ~$0.01 if you exceed the limit and are billed)
- **Segmentation:** Free (local SAM)
- **Image generation:** ~$0.042 × 3 candidates × ~30 assets = **~$4 per full pipeline run**
- **Variants:** Free for UI states (PIL transforms); ~$0.042 each for non-UI variants

A typical mockup with 30 assets costs **~$4 to run end-to-end** at medium quality, or **~$1** at low quality.

## Troubleshooting

**`GEMINI_API_KEY is not set`**
Add it to `docker-compose.yml` under the `artpipe-cli` service (free at https://aistudio.google.com/apikey), then `make down && make up`.

**`OPENAI_API_KEY is not set`**
Add it to `docker-compose.yml` under the `artpipe-cli` service, then `make down && make up`. Verify the key has billing enabled at https://platform.openai.com/account/billing.

**SAM service is slow to start the first time**
Yes — the first `make up` builds the SAM image which downloads the model and PyTorch CPU (~2 GB total). Subsequent starts are instant.

**`segment` produces poor cutouts on detailed assets**
Try the larger SAM model: set `ARTPIPE_SAM_MODEL: facebook/sam-vit-large` under the `sam` service in `docker-compose.yml` and rebuild with `docker compose build sam`. ~900 MB instead of ~375 MB.

**`generate` produces visually inconsistent assets**
Tighten the `style` field in the manifest (or pass `--style "..."` to `make analyze`). The style is prepended to every per-asset prompt during generation.

**I accidentally committed my API keys**
Run `git rm --cached docker-compose.yml`, rotate both keys at the provider dashboards, paste the new keys into `docker-compose.yml`, then run `git update-index --skip-worktree docker-compose.yml` so it doesn't happen again.
