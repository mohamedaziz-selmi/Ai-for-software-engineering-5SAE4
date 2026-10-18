# Sales Forecasting — evaluation report

Generated 2026-10-17T23:19:10+00:00 by `python -m src.pipeline_sales`. All numbers are measured, not estimated.

Target: Total daily unit sales across all stores and product families (sum of train.csv 'sales').

Chronological split, no shuffling. Hyperparameters chosen by rolling-origin CV inside the training period. Validation: model fit on the training period only. Test: untouched final period, model refit on training + validation. All models are scored on exactly the same dates and target. One-step-ahead rows use actual sales up to the previous day; the multi-step section forecasts recursively in 16-day blocks without any actuals after each block origin.

## Validation: 2017-03-01 → 2017-05-31 (92 days, fit on 2013-01-29 → 2017-02-28)

| Model | MAE | RMSE | WAPE % | R² |
|---|---|---|---|---|
| Historical mean (baseline) | 247,968 | 301,945 | 28.69 | -2.072 |
| Seasonal naive t-7 (baseline) | 102,681 | 152,708 | 11.88 | 0.214 |
| Random Forest | 62,170 | 93,573 | 7.19 | 0.705 |

Random Forest vs seasonal naive: MAE 40,512 (39.5 %), RMSE 59,135 (38.7 %), WAPE 4.69 points (39.5 %). Positive = lower error than baseline.

## Test (untouched): 2017-06-01 → 2017-08-15 (76 days, fit on 2013-01-29 → 2017-05-31)

| Model | MAE | RMSE | WAPE % | R² |
|---|---|---|---|---|
| Historical mean (baseline) | 226,832 | 279,306 | 26.47 | -1.909 |
| Seasonal naive t-7 (baseline) | 94,818 | 122,454 | 11.06 | 0.441 |
| Random Forest | 44,847 | 63,825 | 5.23 | 0.848 |

Random Forest vs seasonal naive: MAE 49,971 (52.7 %), RMSE 58,629 (47.9 %), WAPE 5.83 points (52.7 %). Positive = lower error than baseline.

## Multi-step (recursive, 16-day blocks) on the test period

Rolling-origin recursive forecasts in blocks of 16 days over the test period; seasonal naive repeats the last observed week.

| Model | MAE | RMSE | WAPE % |
|---|---|---|---|
| seasonal_naive | 95,496 | 126,201 | 11.14 |
| random_forest | 49,291 | 69,405 | 5.75 |

## Top features (permutation importance on validation)

- `day_of_week`: MAE increase 23,107 when shuffled
- `lag_7`: MAE increase 14,786 when shuffled
- `is_weekend`: MAE increase 10,993 when shuffled
- `lag_14`: MAE increase 10,497 when shuffled
- `lag_28`: MAE increase 8,899 when shuffled
- `lag_1`: MAE increase 8,803 when shuffled
- `day_of_month`: MAE increase 7,515 when shuffled
- `roll_std_7`: MAE increase 542 when shuffled

## Advanced store × family model

Direct multi-step: every history feature lagged >= 16 days, so forecasts up to 16 days ahead never use actuals after the origin.

| Model (daily totals, multi-step test blocks) | MAE | RMSE | WAPE % |
|---|---|---|---|
| advanced | 41,869 | 61,400 | 4.89 |
| random_forest | 49,291 | 69,405 | 5.75 |
| seasonal_naive | 95,496 | 126,201 | 11.14 |

Series level (store × family × day) test WAPE: advanced 12.96 % vs per-series seasonal naive 18.77 %.

Figures: `reports/figures/sales_validation_actual_vs_predicted.png`, `reports/figures/sales_test_actual_vs_predicted.png`, `reports/figures/sales_test_residuals_rf.png`
