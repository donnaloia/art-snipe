"""Review UI for asset candidate approval.

Reads the manifest and the workspace candidate folders, lets the user approve or
reject candidates. Approving moves the chosen candidate into workspace/approved/
named `<asset_id>_normal.png`. Rejecting moves the candidate into
workspace/rejected/.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

WORKSPACE = Path(os.environ.get("WORKSPACE", "/app/workspace"))
EXPORT_DIR = Path(os.environ.get("EXPORT_DIR", "/app/game_assets"))

MANIFEST_PATH = WORKSPACE / "manifests" / "asset_manifest.json"
GENERATED_DIR = WORKSPACE / "generated"
APPROVED_DIR = WORKSPACE / "approved"
REJECTED_DIR = WORKSPACE / "rejected"
REFERENCES_DIR = WORKSPACE / "references"

for d in (GENERATED_DIR, APPROVED_DIR, REJECTED_DIR, REFERENCES_DIR):
    d.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="ArtPipe Review UI", version="1.0.0")
templates = Jinja2Templates(directory="templates")


def _load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {"project": "(no manifest)", "style": "", "assets": []}
    return json.loads(MANIFEST_PATH.read_text())


def _approved_path_for(asset: dict) -> Path:
    return APPROVED_DIR / asset["category"] / f"{asset['id']}_normal.png"


def _candidates_for(asset_id: str, category: str) -> list[Path]:
    folder = GENERATED_DIR / category / asset_id
    if not folder.exists():
        return []
    return sorted(folder.glob("*.png"))


def _reference_for(asset: dict) -> Path | None:
    p = REFERENCES_DIR / asset["category"] / f"{asset['id']}_reference.png"
    return p if p.exists() else None


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    manifest = _load_manifest()
    enriched = []
    for asset in manifest["assets"]:
        candidates = _candidates_for(asset["id"], asset["category"])
        approved = _approved_path_for(asset).exists()
        enriched.append({
            "id": asset["id"],
            "category": asset["category"],
            "type": asset.get("type", ""),
            "size": asset.get("size", []),
            "candidate_count": len(candidates),
            "approved": approved,
        })
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "project": manifest.get("project", ""),
            "style": manifest.get("style", ""),
            "assets": enriched,
            "total": len(enriched),
            "approved_count": sum(1 for a in enriched if a["approved"]),
        },
    )


@app.get("/asset/{asset_id}", response_class=HTMLResponse)
def asset_view(request: Request, asset_id: str) -> HTMLResponse:
    manifest = _load_manifest()
    asset = next((a for a in manifest["assets"] if a["id"] == asset_id), None)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")

    candidates = _candidates_for(asset_id, asset["category"])
    reference = _reference_for(asset)
    approved = _approved_path_for(asset)

    return templates.TemplateResponse(
        "asset.html",
        {
            "request": request,
            "asset": asset,
            "candidates": [c.name for c in candidates],
            "reference": reference.name if reference else None,
            "approved_exists": approved.exists(),
        },
    )


@app.post("/asset/{asset_id}/approve/{filename}")
def approve(asset_id: str, filename: str) -> RedirectResponse:
    manifest = _load_manifest()
    asset = next((a for a in manifest["assets"] if a["id"] == asset_id), None)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")
    src = GENERATED_DIR / asset["category"] / asset_id / filename
    if not src.exists():
        raise HTTPException(status_code=404, detail="candidate not found")
    dst = _approved_path_for(asset)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return RedirectResponse(url=f"/asset/{asset_id}", status_code=303)


@app.post("/asset/{asset_id}/reject/{filename}")
def reject(asset_id: str, filename: str) -> RedirectResponse:
    manifest = _load_manifest()
    asset = next((a for a in manifest["assets"] if a["id"] == asset_id), None)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")
    src = GENERATED_DIR / asset["category"] / asset_id / filename
    if not src.exists():
        raise HTTPException(status_code=404, detail="candidate not found")
    dst = REJECTED_DIR / asset["category"] / asset_id / filename
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return RedirectResponse(url=f"/asset/{asset_id}", status_code=303)


@app.post("/asset/{asset_id}/unapprove")
def unapprove(asset_id: str) -> RedirectResponse:
    manifest = _load_manifest()
    asset = next((a for a in manifest["assets"] if a["id"] == asset_id), None)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")
    dst = _approved_path_for(asset)
    if dst.exists():
        dst.unlink()
    return RedirectResponse(url=f"/asset/{asset_id}", status_code=303)


@app.get("/img/candidate/{category}/{asset_id}/{filename}")
def img_candidate(category: str, asset_id: str, filename: str) -> FileResponse:
    p = GENERATED_DIR / category / asset_id / filename
    if not p.exists():
        raise HTTPException(status_code=404)
    return FileResponse(p)


@app.get("/img/reference/{category}/{filename}")
def img_reference(category: str, filename: str) -> FileResponse:
    p = REFERENCES_DIR / category / filename
    if not p.exists():
        raise HTTPException(status_code=404)
    return FileResponse(p)


@app.get("/img/approved/{category}/{filename}")
def img_approved(category: str, filename: str) -> FileResponse:
    p = APPROVED_DIR / category / filename
    if not p.exists():
        raise HTTPException(status_code=404)
    return FileResponse(p)
