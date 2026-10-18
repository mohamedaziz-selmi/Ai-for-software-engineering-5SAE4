# Customer Segmentation — evaluation report

Generated 2026-10-17T23:17:45+00:00 by `python -m src.pipeline_segmentation`. All values are measured.

Unsupervised clustering: there are no ground-truth labels, so accuracy, precision, recall, and F1 are not applicable. Silhouette, inertia, cluster sizes, and stability are reported instead.

Population: 4322 eligible customers, reference date 2011-12-10, features recency_days, frequency, monetary, K = 4.

| Experiment | Silhouette | Inertia | Cluster sizes |
|---|---|---|---|
| Before preprocessing (raw R, F, M) | 0.885 | 29,741,389,963 | [4198, 3, 15, 106] |
| After preprocessing (log1p + StandardScaler) | 0.334 | 3,919.18 | [1183, 887, 1546, 706] |

The silhouette is lower after preprocessing (0.885 -> 0.334). On raw features Monetary (std 8,302 GBP, skewness 21.5) dominates Euclidean distance, so K-means mostly isolates a few extreme spenders (raw cluster sizes [4198, 3, 15, 106]). Such a split of one huge group plus tiny outlier groups can score a high silhouette while saying almost nothing about recency or frequency. After log1p and standardization all three features contribute equally (cluster sizes [1183, 887, 1546, 706]), producing balanced, interpretable segments whose boundaries run through dense regions, which naturally lowers silhouette. Silhouette values are computed in each model's own feature space and are not directly comparable; cross-space scores are reported alongside.

Cross-space check: raw-model labels score 0.429 in the processed space; final labels score -0.010 in the raw space.

## K search (processed features)

| K | Silhouette | Inertia | Smallest cluster |
|---|---|---|---|
| 2 | 0.432 | 6,466 | 38.3% |
| 3 | 0.338 | 4,848 | 17.3% |
| 4 | 0.334 | 3,919 | 16.3% |
| 5 | 0.317 | 3,269 | 8.3% |
| 6 | 0.313 | 2,844 | 7.6% |
| 7 | 0.303 | 2,537 | 4.6% |
| 8 | 0.301 | 2,331 | 4.9% |
| 9 | 0.281 | 2,150 | 4.8% |
| 10 | 0.278 | 1,992 | 2.3% |

Selection rule: Among K in [3, 6] whose smallest cluster holds >= 2% of customers, take the largest K whose silhouette is within 0.010 of the best candidate (more actionable segments at an equivalent separation). Selected K = 4 (global best K = 2, silhouette 0.432).

Stability: Adjusted Rand Index vs the final labels: 10 different seeds, and 10 fits on random 80% subsamples predicted on all customers. Seed ARI mean 0.997 (min 0.990); subsample ARI mean 0.922 (min 0.852).

## Segments

| Cluster | Label | Customers | Share | Median recency (days) | Median frequency | Median monetary (GBP) | Revenue share |
|---|---|---|---|---|---|---|---|
| 3 | High-value customers | 706 | 16.3% | 9 | 10 | 3,540 | 64.4% |
| 0 | Regular customers | 1183 | 27.4% | 52 | 4 | 1,314 | 24.0% |
| 1 | Recent occasional customers | 887 | 20.5% | 20 | 2 | 401 | 5.1% |
| 2 | Inactive customers | 1546 | 35.8% | 186 | 1 | 294 | 6.6% |

- **Regular customers**: Maintain: standard newsletters and periodic offers; test upsell to higher order values.
- **Recent occasional customers**: Nurture: onboarding sequence and a second-purchase incentive to build frequency.
- **Inactive customers**: Reactivate cheaply: low-cost reminder campaigns; suppress from expensive channels if they stay inactive.
- **High-value customers**: Protect: VIP loyalty rewards, early access, and account management; monitor for any drop in order frequency.

Figures: `reports/figures/segmentation_k_search.png`, `reports/figures/segmentation_recency_days_distribution.png`, `reports/figures/segmentation_frequency_distribution.png`, `reports/figures/segmentation_monetary_distribution.png`
