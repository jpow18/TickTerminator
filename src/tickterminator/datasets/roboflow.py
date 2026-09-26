"""Download COCO exports from Roboflow Universe. Needs a free Roboflow API key."""

import io
import json
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from tickterminator.datasets import DatasetSpec

API_URL = "https://api.roboflow.com"
EXPORT_POLL_SECONDS = 5
EXPORT_TIMEOUT_SECONDS = 600


def download_coco(dataset: DatasetSpec, destination: Path, api_key: str) -> None:
    """Extract the export to `destination`: one folder for each split, with images and
    `_annotations.coco.json`."""
    with urllib.request.urlopen(export_link(dataset, api_key)) as response:
        zipfile.ZipFile(io.BytesIO(response.read())).extractall(destination)


def export_link(dataset: DatasetSpec, api_key: str) -> str:
    """Roboflow prepares an export on the first request. Ask again until it is ready."""
    query = urllib.parse.urlencode({"api_key": api_key})
    url = f"{API_URL}/{dataset.workspace}/{dataset.project}/{dataset.version}/coco?{query}"
    deadline = time.monotonic() + EXPORT_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        with urllib.request.urlopen(url) as response:
            export = json.load(response).get("export")
        if export and export.get("link"):
            return export["link"]
        time.sleep(EXPORT_POLL_SECONDS)
    raise TimeoutError(f"Roboflow did not prepare the export of {dataset.url} in time.")
