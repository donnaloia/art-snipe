# Architecture

## Services

```text
artpipe-cli
  Orchestrates the workflow.

sam
  Placeholder segmentation service. Replace with SAM/SAM2 inference.

comfyui
  Optional local image generation service. Enable with Docker Compose profile `gpu`.

rembg
  Background removal service.

review-ui
  Placeholder local file server for visual review.
```

## Command Flow

```bash
make up
make run MOCKUP=mockups/gameplay.png
make review
make export
```

## GPU Notes

Local generation is easiest on Linux with an NVIDIA GPU and NVIDIA Container Toolkit. On macOS, Docker-based GPU acceleration may be limited, so ComfyUI may need to run directly on the host or use a hosted API.
