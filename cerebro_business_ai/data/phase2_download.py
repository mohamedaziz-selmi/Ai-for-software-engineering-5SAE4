"""Guarded Phase 2 dataset downloader.

Smoke mode uses the Hugging Face dataset-server rows API and downloads only a
small JSONL sample. Kaggle modes only inspect credentials/metadata unless the
user explicitly supplies an approved local file. No full download is started by
this script without ``--allow-large-download``.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).parents[1]
MANIFEST = ROOT / "data" / "phase2_sources.json"
OUT = ROOT / "data" / "phase2" / "smoke"
PROVENANCE = ROOT / "data" / "phase2" / "provenance.json"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ai-service"))
from app.resource_guard import ResourceGuard  # noqa: E402
from data.provenance import record_file, write_manifest  # noqa: E402


def disk_check(required_bytes: int = 250 * 1024 * 1024) -> None:
    """Require a conservative amount of free space before writing data."""
    free = shutil.disk_usage(ROOT).free
    if free < required_bytes:
        raise RuntimeError(f"Insufficient disk space: {free / 2**30:.2f} GiB free")


def hf_smoke(dataset: str, output: Path, columns: list[str], rows: int = 100) -> dict:
    """Fetch a bounded sample from the Hugging Face dataset viewer API."""
    guard = ResourceGuard()
    if not guard.safe_to_start(gpu_required=False):
        raise RuntimeError("ResourceGuard denied smoke download due to CPU/RAM pressure")
    disk_check()
    url = f"https://datasets-server.huggingface.co/rows?dataset={quote(dataset)}&config=default&split=train&offset=0&length={rows}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    payload = response.json()
    records = [item.get("row", {}) for item in payload.get("rows", [])]
    if not records:
        raise RuntimeError(f"No rows returned for {dataset}; inspect available configs/splits")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in records:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    actual = list(records[0].keys())
    missing = [column for column in columns if column not in actual]
    if missing:
        raise RuntimeError(f"Schema discrepancy for {dataset}; missing expected columns: {missing}; observed: {actual}")
    return record_file(output, f"https://huggingface.co/datasets/{dataset}", "dataset-card license; verify upstream terms", len(records), actual)


def kaggle_status(module: str, source: dict) -> dict:
    """Report whether Kaggle credentials are available without exposing them."""
    kaggle_json = Path(os.environ.get("KAGGLE_CONFIG_DIR", Path.home() / ".kaggle")) / "kaggle.json"
    available = kaggle_json.exists() or bool(os.environ.get("KAGGLE_API_TOKEN"))
    return {"module": module, "provider": "kaggle", "credentials_detected": available, "downloaded": False, "source": source["source"], "discrepancy": "Full Kaggle download not started: explicit large-download approval is still required."}


def kaggle_full(module: str, source: dict) -> dict:
    """Download a Kaggle competition only after the explicit CLI opt-in."""
    guard = ResourceGuard()
    if not guard.safe_to_start(gpu_required=False):
        raise RuntimeError("ResourceGuard denied full download start due to CPU/RAM pressure")
    kaggle_json = Path(os.environ.get("KAGGLE_CONFIG_DIR", Path.home() / ".kaggle")) / "kaggle.json"
    if not kaggle_json.exists() and not os.environ.get("KAGGLE_API_TOKEN"):
        raise RuntimeError("Kaggle credentials not found. Configure KAGGLE_CONFIG_DIR or KAGGLE_API_TOKEN locally; never commit the token.")
    disk_check(required_bytes=3 * 1024 * 1024 * 1024)
    destination = ROOT / "data" / "phase2" / "kaggle" / module
    destination.mkdir(parents=True, exist_ok=True)
    kaggle_executable = Path(sys.executable).with_name("kaggle.exe")
    if source.get("kaggle_dataset"):
        command = [str(kaggle_executable), "datasets", "download", source["kaggle_dataset"], "-p", str(destination), "--unzip"]
    else:
        command = [str(kaggle_executable), "competitions", "download", source["kaggle_slug"], "-p", str(destination)]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    files = [path for path in destination.rglob("*") if path.is_file()]
    total_size = sum(path.stat().st_size for path in files)
    return {"module": module, "provider": "kaggle", "downloaded": True, "source": source["source"], "directory": str(destination), "file_count": len(files), "size_bytes": total_size, "stdout": completed.stdout[-1000:]}


def hf_full(module: str, source: dict) -> dict:
    """Download a Hugging Face repository after explicit large-download opt-in."""
    from huggingface_hub import snapshot_download
    guard = ResourceGuard()
    if not guard.safe_to_start(gpu_required=False):
        raise RuntimeError("ResourceGuard denied full download start due to CPU/RAM pressure")
    disk_check(required_bytes=3 * 1024 * 1024 * 1024)
    destination = ROOT / "data" / "phase2" / "huggingface" / module
    snapshot_download(repo_id=source["dataset"], repo_type="dataset", local_dir=str(destination), max_workers=1)
    if guard.should_pause(gpu_required=False):
        raise RuntimeError("ResourceGuard detected post-download CPU/RAM threshold; processing must pause")
    files = [path for path in destination.rglob("*") if path.is_file()]
    return {"module": module, "provider": "huggingface", "downloaded": True, "source": source["source"], "directory": str(destination), "file_count": len(files), "size_bytes": sum(path.stat().st_size for path in files)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", choices=["job_fraud", "job_description", "product_demand", "product_listing"], required=True)
    parser.add_argument("--smoke", action="store_true", help="Download at most 100 Hugging Face rows or report Kaggle status")
    parser.add_argument("--allow-large-download", action="store_true", help="Explicit opt-in required for any full download")
    args = parser.parse_args()
    sources = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source = sources[args.module]
    if not args.smoke and not args.allow_large_download:
        raise SystemExit("Refusing to download: use --smoke or explicitly provide --allow-large-download")
    if source["provider"] == "huggingface" and args.smoke:
        output = OUT / f"{args.module}.jsonl"
        record = hf_smoke(source["dataset"], output, source["expected_columns"])
        records = [record]
    elif source["provider"] == "huggingface":
        records = [hf_full(args.module, source)]
    else:
        records = [kaggle_status(args.module, source)] if args.smoke else [kaggle_full(args.module, source)]
    previous = []
    if PROVENANCE.exists():
        previous = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    keyed = {item.get("module", item.get("path", str(index))): item for index, item in enumerate(previous)}
    for item in records:
        item["module"] = args.module
        for key, existing in list(keyed.items()):
            if existing.get("module") == args.module or existing.get("path") == item.get("path"):
                keyed.pop(key)
        keyed[args.module] = item
    write_manifest(PROVENANCE, list(keyed.values()))
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
