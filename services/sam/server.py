"""SAM segmentation service.

Wraps Hugging Face `facebook/sam-vit-base` (SAM v1) for bounding-box prompted
segmentation. CPU-only; ~3-10s per request depending on image size.

POST /segment
    { "image_b64": "...PNG...", "box": [x, y, w, h] }
returns
    { "cutout_b64": "...PNG with transparent background...", "mask_b64": "...PNG mask..." }

To upgrade to SAM2 in the future, change the ARTPIPE_SAM_MODEL env var and the
model class import. The bbox-prompted segmentation API is the same.
"""

from __future__ import annotations

import base64
import io
import logging
import os
from typing import Optional

import numpy as np
import torch
from fastapi import FastAPI, HTTPException
from PIL import Image
from pydantic import BaseModel
from transformers import SamModel, SamProcessor

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("sam")

MODEL_NAME = os.environ.get("ARTPIPE_SAM_MODEL", "facebook/sam-vit-base")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

log.info("Loading SAM model %s on %s ...", MODEL_NAME, DEVICE)
processor = SamProcessor.from_pretrained(MODEL_NAME)
model = SamModel.from_pretrained(MODEL_NAME).to(DEVICE)
model.eval()
log.info("SAM model ready.")

app = FastAPI(title="SAM Segmentation Service", version="1.0.0")


class SegmentRequest(BaseModel):
    image_b64: Optional[str] = None
    image_path: Optional[str] = None
    box: list[int]


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": MODEL_NAME, "device": DEVICE}


def _decode_image(req: SegmentRequest) -> Image.Image:
    if req.image_b64:
        raw = base64.b64decode(req.image_b64)
        return Image.open(io.BytesIO(raw)).convert("RGB")
    if req.image_path:
        return Image.open(req.image_path).convert("RGB")
    raise HTTPException(status_code=400, detail="Provide image_b64 or image_path")


def _png_b64(img: Image.Image) -> str:
    out = io.BytesIO()
    img.save(out, format="PNG")
    return base64.b64encode(out.getvalue()).decode("ascii")


@app.post("/segment")
def segment(req: SegmentRequest) -> dict:
    if len(req.box) != 4:
        raise HTTPException(status_code=400, detail="box must be [x, y, w, h]")

    image = _decode_image(req)
    x, y, w, h = req.box
    x1, y1 = max(0, x), max(0, y)
    x2 = min(image.width, x + w)
    y2 = min(image.height, y + h)
    if x2 <= x1 or y2 <= y1:
        raise HTTPException(status_code=400, detail="bbox outside image bounds")

    input_boxes = [[[x1, y1, x2, y2]]]
    inputs = processor(image, input_boxes=input_boxes, return_tensors="pt").to(DEVICE)

    with torch.no_grad():
        outputs = model(**inputs)

    masks = processor.image_processor.post_process_masks(
        outputs.pred_masks.cpu(),
        inputs["original_sizes"].cpu(),
        inputs["reshaped_input_sizes"].cpu(),
    )
    scores = outputs.iou_scores.cpu().squeeze(0).squeeze(0)
    best_idx = int(torch.argmax(scores).item())
    mask_tensor = masks[0][0][best_idx]
    mask_np = mask_tensor.numpy().astype(np.uint8) * 255

    rgba = np.zeros((image.height, image.width, 4), dtype=np.uint8)
    rgb_arr = np.array(image)
    rgba[..., :3] = rgb_arr
    rgba[..., 3] = mask_np

    cropped = rgba[y1:y2, x1:x2]
    cutout_img = Image.fromarray(cropped, mode="RGBA")
    mask_img = Image.fromarray(mask_np[y1:y2, x1:x2], mode="L")

    return {
        "cutout_b64": _png_b64(cutout_img),
        "mask_b64": _png_b64(mask_img),
        "score": float(scores[best_idx].item()),
    }
