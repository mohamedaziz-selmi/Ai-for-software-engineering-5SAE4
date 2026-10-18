"""Loading, exploration, and cleaning of the UCI Online Retail transactions."""

import numpy as np
import pandas as pd

from .common import StepLog, describe_series, histogram, missing_summary
from .config import NON_MERCHANDISE_CODES, NON_MERCHANDISE_PREFIXES, RETAIL_XLSX
from .sales_data import MissingDatasetError, SchemaError

RETAIL_COLUMNS = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"]
RECORD_TYPES = {
	"purchase": "Positive quantity and positive unit price on a regular invoice.",
	"cancellation": "Invoice number starts with 'C'. The dataset does not separate cancellations from returns/refunds, so both are handled here.",
	"accounting_adjustment": "Invoice number starts with 'A' (bad-debt adjustments), not customer activity.",
	"non_merchandise": "Postage, carriage, fees, discounts, samples, manual lines, and gift vouchers.",
	"stock_adjustment": "Non-positive quantity on a regular invoice (damaged, lost, or stock corrections).",
	"zero_price": "Positive quantity with unit price <= 0 on a regular invoice (free items or price-less corrections).",
}


def load_raw(path=RETAIL_XLSX):
	if not path.exists():
		raise MissingDatasetError(
			f"{path} is missing. Download 'Online Retail.xlsx' from https://archive.ics.uci.edu/dataset/352/online+retail "
			"and save it as Rayen/Customer Segmentation/dataset/Online Retail.xlsx."
		)
	frame = pd.read_excel(path, dtype={"InvoiceNo": str, "StockCode": str})
	validate_schema(frame)
	return frame


def validate_schema(frame):
	missing = [column for column in RETAIL_COLUMNS if column not in frame.columns]
	if missing:
		raise SchemaError(f"Online Retail: missing required columns {missing}.")
	return True


def normalize(frame):
	"""Type conversion and identifier normalization. Returns the frame and counts of coercion failures."""
	frame = frame.copy()
	issues = {}
	frame["InvoiceNo"] = frame["InvoiceNo"].astype(str).str.strip().str.upper()
	frame["StockCode"] = frame["StockCode"].astype(str).str.strip().str.upper()
	frame["Description"] = frame["Description"].astype("string").str.strip()
	frame["Country"] = frame["Country"].astype(str).str.strip()
	for column in ("Quantity", "UnitPrice"):
		numeric = pd.to_numeric(frame[column], errors="coerce")
		issues[f"{column}_not_numeric"] = int(numeric.isna().sum() - frame[column].isna().sum())
		frame[column] = numeric
	dates = pd.to_datetime(frame["InvoiceDate"], errors="coerce")
	issues["InvoiceDate_unparseable"] = int(dates.isna().sum() - frame["InvoiceDate"].isna().sum())
	frame["InvoiceDate"] = dates
	customer = pd.to_numeric(frame["CustomerID"], errors="coerce")
	non_integer = customer.notna() & (customer % 1 != 0)
	issues["CustomerID_non_integer"] = int(non_integer.sum())
	frame["CustomerID"] = customer.where(~non_integer).astype("Int64").astype("string")
	return frame, issues


def is_non_merchandise(stock_codes):
	codes = pd.Series(stock_codes).astype(str).str.upper()
	return codes.isin(NON_MERCHANDISE_CODES) | codes.str.startswith(NON_MERCHANDISE_PREFIXES)


def classify(frame):
	"""Assign exactly one record_type per line, in a fixed priority order."""
	invoice = frame["InvoiceNo"].astype(str)
	conditions = [
		invoice.str.startswith("A"),
		is_non_merchandise(frame["StockCode"]).to_numpy(),
		invoice.str.startswith("C"),
		frame["Quantity"] <= 0,
		frame["UnitPrice"] <= 0,
	]
	choices = ["accounting_adjustment", "non_merchandise", "cancellation", "stock_adjustment", "zero_price"]
	return pd.Series(np.select(conditions, choices, default="purchase"), index=frame.index)


def explore(raw):
	frame, issues = normalize(raw)
	revenue = frame["Quantity"] * frame["UnitPrice"]
	invoice = frame["InvoiceNo"]
	invoice_revenue = revenue[~invoice.str.startswith(("C", "A"))].groupby(invoice).sum()
	return {
		"dataset": "UCI Online Retail",
		"total_transaction_lines": int(len(frame)),
		"columns": list(raw.columns),
		"dtypes": {column: str(dtype) for column, dtype in raw.dtypes.items()},
		"unique_invoices": int(invoice.nunique()),
		"unique_customers": int(frame["CustomerID"].nunique()),
		"unique_products": int(frame["StockCode"].nunique()),
		"countries": int(frame["Country"].nunique()),
		"missing_values": missing_summary(raw),
		"duplicate_transaction_lines": int(raw.duplicated().sum()),
		"coercion_issues": issues,
		"invalid_quantities": {"zero": int((frame["Quantity"] == 0).sum()), "negative": int((frame["Quantity"] < 0).sum())},
		"invalid_prices": {"zero": int((frame["UnitPrice"] == 0).sum()), "negative": int((frame["UnitPrice"] < 0).sum())},
		"cancellations": {
			"lines": int(invoice.str.startswith("C").sum()),
			"invoices": int(invoice[invoice.str.startswith("C")].nunique()),
			"lines_with_customer": int((invoice.str.startswith("C") & frame["CustomerID"].notna()).sum()),
		},
		"negative_quantity_without_cancellation": int(((frame["Quantity"] < 0) & ~invoice.str.startswith("C")).sum()),
		"accounting_adjustment_lines": int(invoice.str.startswith("A").sum()),
		"non_merchandise_lines": int(is_non_merchandise(frame["StockCode"]).sum()),
		"purchase_date_range": {"start": frame["InvoiceDate"].min().isoformat(), "end": frame["InvoiceDate"].max().isoformat()},
		"line_revenue": describe_series(revenue),
		"invoice_revenue_regular_invoices": describe_series(invoice_revenue),
		"invoice_revenue_histogram_log1p": histogram(invoice_revenue[invoice_revenue > 0], bins=30, log=True),
	}


def clean(raw):
	"""Documented cleaning policy. Every line is kept and labelled except exact duplicates."""
	log = StepLog()
	frame, issues = normalize(raw)
	log.record("normalize_types_and_identifiers", len(raw), len(frame), "Parse InvoiceDate, coerce Quantity/UnitPrice to numbers, upper-case and trim InvoiceNo/StockCode, store CustomerID as an integer string.", coercion_issues=issues)

	before = len(frame)
	unusable = frame["InvoiceDate"].isna() | frame["Quantity"].isna() | frame["UnitPrice"].isna()
	frame = frame[~unusable]
	log.record("drop_unparseable_lines", before, len(frame), "Lines without a valid date, quantity, or price cannot be used.")

	before = len(frame)
	dupes = frame.duplicated(keep="first")
	dup_revenue = float((frame.loc[dupes, "Quantity"] * frame.loc[dupes, "UnitPrice"]).sum())
	frame = frame[~dupes]
	log.record(
		"drop_exact_duplicate_lines", before, len(frame),
		"Lines identical in every column (same invoice, product, quantity, price, and timestamp) are treated as double-recorded entries; the first copy is kept.",
		duplicate_revenue=dup_revenue,
	)

	frame["record_type"] = classify(frame)
	frame["LineRevenue"] = frame["Quantity"] * frame["UnitPrice"]
	frame["has_customer"] = frame["CustomerID"].notna()
	counts = frame["record_type"].value_counts().to_dict()
	log.record("classify_records", len(frame), len(frame), "Each line labelled purchase, cancellation, accounting_adjustment, non_merchandise, stock_adjustment, or zero_price.", record_type_counts=counts)

	missing_description = frame["Description"].isna()
	log.record(
		"inspect_missing_descriptions", len(frame), len(frame),
		"Missing descriptions are not treated as invalid on their own; they are classified by quantity and price like every other line.",
		missing_description_lines=int(missing_description.sum()),
		missing_description_by_type=frame.loc[missing_description, "record_type"].value_counts().to_dict(),
	)
	log.record(
		"separate_missing_customer_id", len(frame), len(frame),
		"Lines without CustomerID stay in retail_clean.csv.gz for revenue reporting but cannot be attributed to a customer and are excluded from segmentation.",
		lines_without_customer=int((~frame["has_customer"]).sum()),
		purchase_revenue_without_customer=float(frame.loc[~frame["has_customer"] & (frame["record_type"] == "purchase"), "LineRevenue"].sum()),
	)

	report = {
		"dataset": "UCI Online Retail",
		"steps": log.steps,
		"record_types": RECORD_TYPES,
		"record_type_counts": counts,
		"revenue_policy": (
			"LineRevenue = Quantity x UnitPrice. Customer Monetary = net merchandise spending: revenue of the customer's purchase lines "
			"minus the absolute value of their cancellation lines. Non-merchandise lines (postage, fees, discounts, vouchers) and "
			"adjustments are excluded. Customers whose net spending is <= 0 (cancellations refer to purchases before the data window) "
			"are not eligible for segmentation."
		),
		"missing_values_after": missing_summary(frame[RETAIL_COLUMNS]),
		"raw_rows": int(len(raw)),
		"clean_rows": int(len(frame)),
	}
	return frame, report
