"""Resource-guarded M5 extraction, integrity, schema, and provenance validation."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pandas as pd

import sys
ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "ai-service"))
from app.resource_guard import ResourceGuard  # noqa: E402

ZIP_PATH = ROOT / "data/phase2/kaggle/product_demand/m5-forecasting-accuracy.zip"
OUT = ROOT / "data/phase2/kaggle/product_demand/extracted"
EXPECTED = {"calendar.csv", "sales_train_evaluation.csv", "sales_train_validation.csv", "sample_submission.csv", "sell_prices.csv"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024): digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    guard = ResourceGuard()
    if not guard.safe_to_start(): raise RuntimeError("ResourceGuard denied M5 extraction")
    if not ZIP_PATH.exists(): raise FileNotFoundError(ZIP_PATH)
    with zipfile.ZipFile(ZIP_PATH) as archive:
        corrupt = archive.testzip()
        names = {item.filename for item in archive.infolist()}
        if corrupt: raise RuntimeError(f"Corrupt archive member: {corrupt}")
        if names != EXPECTED: raise RuntimeError(f"Unexpected archive members: {sorted(names ^ EXPECTED)}")
        OUT.mkdir(parents=True, exist_ok=True)
        for member in archive.infolist():
            target = OUT / member.filename
            if not target.exists() or target.stat().st_size != member.file_size:
                archive.extract(member, OUT)
    calendar = pd.read_csv(OUT / "calendar.csv", nrows=10)
    sales = pd.read_csv(OUT / "sales_train_validation.csv", nrows=10)
    prices = pd.read_csv(OUT / "sell_prices.csv", nrows=10)
    schemas = {"calendar.csv": list(calendar.columns), "sales_train_validation.csv": list(sales.columns), "sell_prices.csv": list(prices.columns)}
    expected_columns = {"calendar.csv": ["date", "wm_yr_wk", "d"], "sales_train_validation.csv": ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"], "sell_prices.csv": ["store_id", "item_id", "wm_yr_wk", "sell_price"]}
    missing = {name: sorted(set(columns) - set(schemas[name])) for name, columns in expected_columns.items()}
    files = []
    for name in sorted(EXPECTED):
        path = OUT / name
        files.append({"file": name, "size_bytes": path.stat().st_size, "sha256": sha256(path)})
    result = {"status": "complete", "archive_size_bytes": ZIP_PATH.stat().st_size, "archive_sha256": sha256(ZIP_PATH), "files": files, "schemas": schemas, "missing_expected_columns": missing, "calendar_sample_rows": len(calendar), "sales_sample_rows": len(sales), "price_sample_rows": len(prices), "license": "Kaggle competition terms; use subject to accepted competition rules", "source": "https://www.kaggle.com/competitions/m5-forecasting-accuracy/data", "resource": guard.as_dict()}
    destination = ROOT / "data/phase4/m5_validation.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
