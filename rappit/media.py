"""Fetch a generated file back from the GitHub Actions artifact of the run that made it."""
import io
import os
import zipfile
from pathlib import Path

import requests

from .common import ROOT

CACHE = ROOT / "out_cache"


def fetch(run_id: str, relpath: str) -> Path:
    dest = CACHE / str(run_id) / relpath
    if dest.exists():
        return dest
    repo = os.environ["GITHUB_REPOSITORY"]
    h = {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
         "Accept": "application/vnd.github+json"}
    arts = requests.get(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts",
                        headers=h, timeout=60).json().get("artifacts", [])
    art = next((a for a in arts if a["name"] == f"media-{run_id}"), None)
    if not art:
        raise FileNotFoundError(f"No media artifact for run {run_id} (expired after 30 days?)")
    z = requests.get(art["archive_download_url"], headers=h, timeout=600)
    z.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(z.content)) as zf:
        zf.extractall(CACHE / str(run_id))
    if not dest.exists():
        raise FileNotFoundError(f"{relpath} not found in artifact media-{run_id}")
    return dest
