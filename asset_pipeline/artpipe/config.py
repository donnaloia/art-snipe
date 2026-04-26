from pathlib import Path
import os

REPO_ROOT = Path(os.environ.get("ARTPIPE_REPO", "/repo"))
WORKSPACE = REPO_ROOT / "workspace"
ANALYSIS_DIR = WORKSPACE / "analysis"
MANIFEST_DIR = WORKSPACE / "manifests"
REFERENCES_DIR = WORKSPACE / "references"
GENERATED_DIR = WORKSPACE / "generated"
APPROVED_DIR = WORKSPACE / "approved"
REJECTED_DIR = WORKSPACE / "rejected"
LOGS_DIR = WORKSPACE / "logs"

EXPORT_DIR = Path(os.environ.get("ARTPIPE_EXPORT_DIR", REPO_ROOT / "game_assets"))
