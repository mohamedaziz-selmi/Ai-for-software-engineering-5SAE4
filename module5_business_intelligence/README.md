# Module 5 — Business Intelligence

Two independent AI works, served to the Cerebro dashboard (third triangle → **Business Intelligence Workspace**):

1. **Sales Forecasting**: total daily unit sales from the Kaggle *Store Sales* dataset. The baselines (seasonal naive t−7 and historical mean) are scored before a scikit-learn `RandomForestRegressor`. An optional advanced store × family `HistGradientBoostingRegressor` is also trained.
2. **Customer Segmentation**: RFM features from the UCI *Online Retail* dataset. A raw-feature reference K-means is compared with K-means after log1p and `StandardScaler` preprocessing. Segment labels come from configurable rules.

Every number in `models/*.json` and `reports/*.md` comes from running the pipelines on the real datasets.

## Layout

```
../Rayen/                     raw datasets, read in place and never modified (no duplicate copy)
data/processed/               retail_clean.csv.gz, customer_rfm.csv, customer_segments.csv, customer_features_processed.csv,
                              daily_sales.csv, sales_calendar.csv (store_sales_features.csv.gz only with --export-features)
data/reports/                 cleaning_report.json, data_quality_report.json, transformation_report.json,
                              sales_exploration_report.json, retail_exploration_report.json
data/dataset_manifest.json    source URL, files, row counts, columns, SHA-256, licence, download date
models/                       *.joblib artifacts + *_feature_config.json, *_evaluation.json, *_training_metadata.json
reports/                      sales_evaluation_report.md, segmentation_evaluation_report.md, figures/*.png
src/                          reusable cleaning / feature / model / inference code
api.py                        FastAPI service (port 8002, prefix /api/module5)
tests/                        pytest suite (synthetic fixtures for unit tests + checks against the real artifacts)
```

## Commands (PowerShell, from `module5_business_intelligence/`)

```powershell
# Uses the shared environment in rag_service/.venv (same as the sentiment classifier).
..\rag_service\.venv\Scripts\python.exe -m pip install -r requirements.txt

..\rag_service\.venv\Scripts\python.exe -m src.manifest                 # dataset manifest
..\rag_service\.venv\Scripts\python.exe -m src.pipeline_sales           # explore, clean, features, tune, train, evaluate (~3.5 min)
..\rag_service\.venv\Scripts\python.exe -m src.pipeline_sales --skip-advanced   # basic model only (~1.5 min)
..\rag_service\.venv\Scripts\python.exe -m src.pipeline_sales --export-features # also write the store x family feature panel (~30 MB gz)
..\rag_service\.venv\Scripts\python.exe -m src.pipeline_segmentation    # explore, clean, RFM, reference + final K-means (~1 min)

..\rag_service\.venv\Scripts\python.exe -m pytest -q                    # tests
..\rag_service\.venv\Scripts\python.exe -m uvicorn api:app --port 8002  # backend
```

Frontend, from the repository root: `npm.cmd run dev`, then open http://localhost:8766/ and click the third triangle. Vite proxies `/api/module5` to `127.0.0.1:8002`.

The pipelines read `Rayen/Customer Segmentation/dataset/Online Retail.xlsx` and `Rayen/Sales Forecasting/Dataset/*.csv` directly (paths in `src/config.py`). The pipelines stop with a message naming the missing file; they never substitute synthetic data.

## Key decisions

**Sales**
- **Target**: sum of `sales` over all stores and families per date. There are no negative sales. Policy: clip any negatives to 0 and report them.
- **Missing dates**: the only dates missing are 25 December each year, and they are missing for every store. They are inserted as closure days (sales 0, `is_closure_day` = 1) and are not interpolated.
- **Splits** (chronological, no shuffling): train 2013-01-29 → 2017-02-28 (after a 28-day lag warm-up), validation 2017-03-01 → 2017-05-31, test 2017-06-01 → 2017-08-15 (untouched).
- **Tuning**: rolling-origin `TimeSeriesSplit` (5 folds) on the training period only. The final model is refit on train + validation and scored once on test.
- **Leakage controls**: lags use `shift(k ≥ 1)` and rolling statistics use `shift(1)`. `transactions` and `id` are excluded. Multi-step forecasts are recursive. The advanced model only uses lags of 16 days or more, so it never needs future actuals.
- **Oil prices**: forward-filled only, and used only in the advanced model, lagged by 16 days.

**Segmentation**
- **Line types**: lines are labelled purchase, cancellation (C invoices; returns are not distinguishable from cancellations), accounting adjustment (A invoices), non-merchandise (POST, DOT, M, fees, vouchers…), stock adjustment, and zero price.
- **Monetary**: net merchandise spend, i.e. purchases minus cancellations. Customers with net spend ≤ 0 are excluded.
- **Reference date**: 2011-12-10, the day after the last invoice.
- **Choosing K**: K is searched over 2–10. Among K = 3–6 with every cluster holding at least 2% of customers, the largest K within 0.01 silhouette of the best is chosen (settings in `src/config.py`).

## Measured results

| Sales, test 2017-06-01 → 2017-08-15 (76 days) | MAE | RMSE | WAPE |
|---|---|---|---|
| Historical mean | 226,832 | 279,306 | 26.47% |
| Seasonal naive t−7 | 94,818 | 122,454 | 11.06% |
| **Random Forest** (one step ahead) | **44,847** | **63,825** | **5.23%** |
| Seasonal naive, 16-day blocks | 95,496 | 126,201 | 11.14% |
| Random Forest, recursive 16-day blocks | 49,291 | 69,405 | 5.75% |
| Advanced store × family, summed per day | 41,869 | 61,400 | 4.89% |

On validation (2017-03-01 → 05-31), Random Forest WAPE is 7.19% against 11.88% for seasonal naive.

| Segmentation (4,322 customers, K = 4) | Silhouette | Cluster sizes |
|---|---|---|
| Raw R, F, M (reference) | 0.885 | 4198 / 3 / 15 / 106 |
| log1p + StandardScaler | 0.334 | 1183 / 887 / 1546 / 706 |

Silhouette is **lower** after preprocessing. On raw features, Monetary dominates the distance, so K-means just splits off a few extreme spenders. That gives a high score but useless segments. The full explanation is in `reports/segmentation_evaluation_report.md`. Stability (Adjusted Rand Index) across 10 seeds is ≈ 0.99.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/module5/health`, `/training-status` | Artifact presence, training metadata (never trains) |
| GET | `/api/module5/overview?start=&end=&forecast_days=` | Headline KPIs |
| GET | `/api/module5/data-quality` | Manifest plus cleaning, quality, and transformation reports |
| GET | `/api/module5/sales/evaluation` | Baseline vs Random Forest, residuals, error breakdown, importances, advanced model |
| GET | `/api/module5/sales/history?start=&end=` | Daily history |
| GET/POST | `/api/module5/sales/forecast` | `horizon` 1–28, optional `origin` (backtest), `history_days`, `model`, `store_nbr`, `family` |
| GET | `/api/module5/sales/options` | Stores and families for the advanced model |
| GET | `/api/module5/segmentation/evaluation`, `/segmentation/clusters` | Before/after metrics, profiles, labels, distributions |
| GET | `/api/module5/segmentation/customers?search=&segment=&cluster=&sort=&order=&page=&page_size=` | Paginated customer table (pseudonymous IDs only) |
| POST | `/api/module5/segmentation/assign` | Score one `{recency_days, frequency, monetary}` profile |

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8002/api/module5/sales/forecast -ContentType 'application/json' -Body '{"horizon":14}'
Invoke-RestMethod "http://127.0.0.1:8002/api/module5/segmentation/customers?segment=High-value%20customers&page_size=10"
```

When artifacts are missing, the API returns 503 with the command to run. Invalid inputs return 422.

## Known limitations

- The dataset download dates are unknown. The manifest records the archive timestamps and the date the files were copied into the project.
- The Store Sales `test.csv` has no labels, so the "test" period used here is the last 76 labelled days. Future forecasts (after 2017-08-15) cannot be scored.
- Recursive forecasts are capped at 28 days and the advanced model at 16 days. The holiday calendar ends on 2017-12-26.
- One-step-ahead metrics use actual sales from the previous day. The 16-day block metrics are the realistic multi-day figures.
- K-means assigns customers by distance to cluster centres. A few customers sit near a boundary; for example, a frequent big spender who has been inactive for a year can fall in "High-value". Segment labels describe each cluster's median, not every member.
