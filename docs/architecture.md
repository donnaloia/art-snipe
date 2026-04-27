# Architecture

## Services

```text
artpipe-cli         Python CLI orchestrating the pipeline. Calls vision +
                    image-gen APIs, talks to local services for segmentation
                    and background removal.

sam                 FastAPI wrapper around Hugging Face SAM v1 for
                    bounding-box prompted segmentation. CPU-only.
                    Endpoint: POST /segment

rembg               danielgatis/rembg image, used as a background-removal
                    fallback when SAM is unavailable or for additional
                    cleanup. Endpoint: POST /api/remove

review-ui           FastAPI + Jinja2 web app on port 8473 for approving or
                    rejecting candidate generations.
```

## Data Flow

```text
mockups/foo.png
   │
   │  artpipe analyze
   ▼
   ├─► vision provider (Gemini API)
   └─► workspace/manifests/asset_manifest.json   (asset list with bboxes)
        │
        │  artpipe segment
        ▼
        ├─► sam service (HTTP) → mask + cutout
        ├─► rembg service (HTTP) → cleaned cutout
        └─► workspace/references/<category>/<id>_reference.png
              │
              │  artpipe generate
              ▼
              ├─► image gen provider (OpenAI API, with reference)
              └─► workspace/generated/<category>/<id>/<id>_v01.png ...
                    │
                    │  human review at http://localhost:8473
                    ▼
                    └─► workspace/approved/<category>/<id>_normal.png
                          │
                          │  artpipe variants
                          ▼
                          ├─► PIL transforms (hover/pressed/disabled/...)
                          ├─► image gen provider (for non-deterministic variants)
                          └─► workspace/approved/<category>/<id>_<variant>.png
                                │
                                │  artpipe validate
                                │  artpipe export
                                ▼
                                └─► game_assets/<category>/<id>_<variant>.png
```

## Provider Abstraction

`asset_pipeline/artpipe/providers/` contains:

- `base.py` — abstract `VisionProvider` and `ImageGenProvider` interfaces
- `factory.py` — env-var-driven selection of concrete providers
- `vision/gemini.py` — Gemini 2.5 Flash implementation
- `image_gen/openai_provider.py` — OpenAI gpt-image-1 implementation

Adding a new provider is purely additive: implement the interface, register in the factory, set the env var. The CLI never depends on a specific provider.

## Environment Variables

All variables are set directly in `docker-compose.yml` under each service's `environment` block. `artpipe-cli` consumes the API keys and provider-selection variables; `sam` consumes `ARTPIPE_SAM_MODEL`; `review-ui` consumes `WORKSPACE` and `EXPORT_DIR`.
