"""Phase 3 preflight for availability, terms, sizes, and local capacity."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).parents[1]
SOURCES = json.loads((ROOT / "data" / "phase2_sources.json").read_text(encoding="utf-8"))


def head_size(url: str) -> dict:
    try:
        response = requests.head(url, allow_redirects=True, timeout=45)
        return {
            "status_code": response.status_code,
            "content_length": int(response.headers["content-length"]) if response.headers.get("content-length", "").isdigit() else None,
            "content_type": response.headers.get("content-type"),
            "final_url": response.url,
        }
    except requests.RequestException as exc:
        return {"status_code": None, "content_length": None, "error": str(exc)}


def hf_preflight(module: str, source: dict) -> dict:
    repo = source["dataset"]
    api = requests.get(f"https://huggingface.co/api/datasets/{quote(repo, safe='/')}", timeout=45)
    api.raise_for_status()
    metadata = api.json()
    sha = metadata.get("sha") or "main"
    siblings = metadata.get("siblings", [])
    files = []
    for item in siblings:
        name = item.get("rfilename", "")
        if name.startswith("." ) or name.endswith((".md", ".json", ".gitattributes")):
            continue
        info = head_size(f"https://huggingface.co/datasets/{repo}/resolve/{sha}/{quote(name, safe='/')}?download=true")
        files.append({"file": name, **info})
    known = [item["content_length"] for item in files if item.get("content_length") is not None]
    return {
        "module": module,
        "provider": "huggingface",
        "dataset": repo,
        "available": api.status_code == 200,
        "gated": bool(metadata.get("gated")),
        "private": bool(metadata.get("private")),
        "commit": sha,
        "license_metadata": metadata.get("cardData", {}).get("license"),
        "files": files,
        "known_size_bytes": sum(known),
        "size_complete": len(known) == len(files),
        "source": source["source"],
        "terms_note": source["license"],
    }


def kaggle_preflight(module: str, source: dict) -> dict:
    config = Path(__import__("os").environ.get("KAGGLE_CONFIG_DIR", Path.home() / ".kaggle")) / "kaggle.json"
    return {
        "module": module,
        "provider": "kaggle",
        "available": True,
        "credentials_detected": config.exists() or bool(__import__("os").environ.get("KAGGLE_API_TOKEN")),
        "source": source["source"],
        "terms_note": source["license"],
        "known_size_bytes": None,
        "discrepancy": "Kaggle API file metadata is not queried without credentials; no download attempted." if not config.exists() else None,
    }


def main() -> None:
    output = {"disk": {}, "datasets": []}
    usage = shutil.disk_usage(ROOT)
    output["disk"] = {"free_bytes": usage.free, "total_bytes": usage.total, "free_gib": round(usage.free / 2**30, 2)}
    for module, source in SOURCES.items():
        try:
            item = hf_preflight(module, source) if source["provider"] == "huggingface" else kaggle_preflight(module, source)
        except Exception as exc:
            item = {"module": module, "provider": source["provider"], "available": False, "error": str(exc), "source": source["source"]}
        output["datasets"].append(item)
    destination = ROOT / "data" / "phase3" / "preflight.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
