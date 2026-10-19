# Cerebro synthetic sales history examples

All ten files are generated simulations for trying the app. They are not real sales records and must not be used to claim real-world forecast accuracy.

Each file has 180 consecutive daily observations (2026-04-22 through 2026-10-18), one named demo product, and one demo store. Sales are whole units. Prices are illustrative currency units. Visitors are counts. Promotion and stockout flags use 1/0. A stockout flags constrained sales; ordinary zero sales remain unflagged.

## Try them

Open Sales & inventory, upload one CSV, keep the detected column mapping, click Validate and use history, then Forecast and plan inventory. Try a 14-day horizon, 7-day lead time, and stock of 30 to begin. Stock and lead time are separate user assumptions; they are not inferred from these files.

The product column fills the product name automatically. The synthetic and location columns provide context; the app ignores them during feature mapping. No future observations or expected model scores are included.

## Scenarios

- 01_synthetic_stable_groceries.csv: Steady everyday sales with modest random variation.
- 02_synthetic_weekend_headphones.csv: Recurring weekly pattern with higher Friday and weekend sales.
- 03_synthetic_growing_protein_powder.csv: Gradually rising sales plus weekly variation.
- 04_synthetic_declining_phone_cases.csv: Gradually declining sales without reaching a forced zero.
- 05_synthetic_promotional_coffee.csv: Repeated five-day promotions with lower prices and higher sales.
- 06_synthetic_intermittent_spare_parts.csv: Many genuine zero-sales days interspersed with small orders.
- 07_synthetic_stockout_sneakers.csv: Weekly demand interrupted by flagged stockout periods; sales are constrained observations.
- 08_synthetic_traffic_driven_skincare.csv: Changing visitor traffic drives simulated purchases at a stable conversion rate.
- 09_synthetic_price_sensitive_speakers.csv: Several observed prices with a simulated inverse price-demand relationship.
- 10_synthetic_sudden_shift_pet_food.csv: A persistent increase in daily sales after day 115; tests adaptation to a level shift.

The CSV with intermittent orders and the sudden-shift file are deliberately challenging. High WAPE can occur for low-volume or unpredictable series; these examples do not promise a particular score.
