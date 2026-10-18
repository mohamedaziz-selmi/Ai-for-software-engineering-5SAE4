"""Dataset manifest: provenance, size, schema, and usage terms for each raw file.

Run: ..\\rag_service\\.venv\\Scripts\\python.exe -m src.manifest
"""

from datetime import datetime

import pandas as pd

from .common import file_sha256, utc_now, write_json
from .config import DATA_DIR, REPO_DIR, RETAIL_XLSX, STORE_SALES_FILES

SOURCES = {
	"online_retail": {
		"title": "Online Retail (UCI Machine Learning Repository, id 352)",
		"source_url": "https://archive.ics.uci.edu/dataset/352/online+retail",
		"license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
		"citation": "Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33",
		"local_origin": "Rayen/Customer Segmentation/dataset/Online Retail.xlsx",
	},
	"store_sales": {
		"title": "Store Sales - Time Series Forecasting (Kaggle competition, Corporación Favorita)",
		"source_url": "https://www.kaggle.com/competitions/store-sales-time-series-forecasting/data",
		"license": "Kaggle competition rules: data may be used for the competition and non-commercial, academic or educational purposes; redistribution is not permitted.",
		"citation": "Alexis Cook, DanB, inversion, Ryan Holbrook. Store Sales - Time Series Forecasting. Kaggle, 2021.",
		"local_origin": "Rayen/Sales Forecasting/Dataset/",
	},
}


def dataset_version(source, paths):
	return {
		"source": source,
		"source_url": SOURCES[source]["source_url"],
		"files": {path.name: file_sha256(path)[:16] for path in paths if path.exists()},
	}


def _describe(path, frame):
	stat = path.stat()
	return {
		"file_name": path.relative_to(REPO_DIR).as_posix(),
		"size_bytes": stat.st_size,
		"sha256": file_sha256(path),
		"row_count": int(len(frame)),
		"column_names": list(map(str, frame.columns)),
		"local_copy_date": datetime.fromtimestamp(stat.st_mtime).date().isoformat(),
	}


def build_manifest():
	datasets = []
	missing = []
	if RETAIL_XLSX.exists():
		datasets.append({**SOURCES["online_retail"], "download_date": "unknown (original archive timestamp 2023-05-22; copied into the project 2026-10-17)", "files": [_describe(RETAIL_XLSX, pd.read_excel(RETAIL_XLSX))]})
	else:
		missing.append({"file": str(RETAIL_XLSX), "how_to_obtain": f"Download 'Online Retail.xlsx' from {SOURCES['online_retail']['source_url']}."})
	files = []
	for path in STORE_SALES_FILES.values():
		if path.exists():
			files.append(_describe(path, pd.read_csv(path)))
		else:
			missing.append({"file": str(path), "how_to_obtain": f"Accept the competition rules and download from {SOURCES['store_sales']['source_url']}."})
	if files:
		datasets.append({**SOURCES["store_sales"], "download_date": "unknown (original archive timestamp 2021-11-22; copied into the project 2026-10-17)", "files": files})
	return {"created_at": utc_now(), "datasets": datasets, "missing_files": missing, "policy": "Raw files are read-only inputs; pipelines write only to data/processed, data/reports, models and reports."}


if __name__ == "__main__":
	path = write_json(DATA_DIR / "dataset_manifest.json", build_manifest())
	print(f"Wrote {path}")
