from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="SAM Segmentation Service Placeholder")

class SegmentRequest(BaseModel):
    image_path: str
    box: list[int] | None = None
    points: list[list[int]] | None = None

@app.get("/health")
def health():
    return {"status": "ok", "service": "sam-placeholder"}

@app.post("/segment")
def segment(req: SegmentRequest):
    # Replace this with real SAM/SAM2 inference.
    return {
        "status": "placeholder",
        "image_path": req.image_path,
        "box": req.box,
        "mask_path": None,
        "message": "Wire SAM/SAM2 here to return a mask PNG path."
    }
