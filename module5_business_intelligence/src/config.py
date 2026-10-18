"""Paths, seeds, and experiment settings shared by every Module 5 pipeline."""

from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = MODULE_DIR.parent
DATA_DIR = MODULE_DIR / "data"
# Raw datasets are read in place from the Rayen/ folder (read-only); no duplicate copy is kept.
RAW_DIR = REPO_DIR / "Rayen"
STORE_SALES_DIR = RAW_DIR / "Sales Forecasting" / "Dataset"
PROCESSED_DIR = DATA_DIR / "processed"
DATA_REPORTS_DIR = DATA_DIR / "reports"
MODELS_DIR = MODULE_DIR / "models"
REPORTS_DIR = MODULE_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

RETAIL_XLSX = RAW_DIR / "Customer Segmentation" / "dataset" / "Online Retail.xlsx"
PYTHON = "..\\rag_service\\.venv\\Scripts\\python.exe"
STORE_SALES_FILES = {
	"train": STORE_SALES_DIR / "train.csv",
	"test": STORE_SALES_DIR / "test.csv",
	"stores": STORE_SALES_DIR / "stores.csv",
	"transactions": STORE_SALES_DIR / "transactions.csv",
	"oil": STORE_SALES_DIR / "oil.csv",
	"holidays_events": STORE_SALES_DIR / "holidays_events.csv",
}

RANDOM_SEED = 42

# Sales forecasting: chronological periods (inclusive). The test period is the
# latest labelled history and is never used for tuning or model selection.
SALES_SPLITS = {
	"train": ("2013-01-01", "2017-02-28"),
	"validation": ("2017-03-01", "2017-05-31"),
	"test": ("2017-06-01", "2017-08-15"),
}
SALES_LAGS = [1, 7, 14, 28]
SALES_ROLLING_WINDOWS = [7, 14, 28]
SALES_MAX_HORIZON = 28
MULTISTEP_BLOCK_DAYS = 16

# Advanced store x family model: direct multi-step strategy, every lag is at
# least the maximum horizon so no future actuals are ever required.
ADVANCED_MIN_LAG = 16
ADVANCED_TRAIN_START = "2015-08-01"

# Customer segmentation.
SEGMENT_K_RANGE = list(range(2, 11))
SEGMENT_BUSINESS_K_RANGE = (3, 6)
SEGMENT_MIN_CLUSTER_SHARE = 0.02
SEGMENT_SILHOUETTE_TOLERANCE = 0.01
SEGMENT_N_INIT = 20
SEGMENT_FEATURES = ["recency_days", "frequency", "monetary"]

# Stock codes that are services, fees, or bookkeeping rather than merchandise.
NON_MERCHANDISE_CODES = {
	"POST", "DOT", "M", "C2", "D", "S", "BANK CHARGES", "AMAZONFEE", "CRUK", "PADS", "B",
}
NON_MERCHANDISE_PREFIXES = ("GIFT_0001",)


def ensure_dirs():
	for directory in (PROCESSED_DIR, DATA_REPORTS_DIR, MODELS_DIR, REPORTS_DIR, FIGURES_DIR):
		directory.mkdir(parents=True, exist_ok=True)
