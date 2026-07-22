"""
clean_data.py — Data cleaning and feature engineering for the retail
performance dataset.

Reads data/raw_superstore_sales.csv, detects its real encoding, parses
dates in whatever format the source uses, drops duplicate/invalid rows,
engineers analysis columns, prints a data-quality summary, and writes
data/cleaned_superstore_sales.csv.

Run from the project root:
    python src/clean_data.py
"""

import os
import pandas as pd

RAW_PATH = os.path.join("data", "raw_superstore_sales.csv")
CLEAN_PATH = os.path.join("data", "cleaned_superstore_sales.csv")

# Source columns -> clean snake_case names used from here on
COLUMN_MAP = {
    "Row ID": "row_id",
    "Order ID": "order_id",
    "Order Date": "order_date",
    "Order Priority": "order_priority",
    "Order Quantity": "quantity",
    "Sales": "sales",
    "Discount": "discount",
    "Ship Mode": "ship_mode",
    "Profit": "profit",
    "Unit Price": "unit_price",
    "Shipping Cost": "shipping_cost",
    "Customer Name": "customer_name",
    "Province": "province",
    "Region": "region",
    "Customer Segment": "segment",
    "Product Category": "category",
    "Product Sub-Category": "sub_category",
    "Product Name": "product_name",
    "Product Container": "product_container",
    "Product Base Margin": "product_base_margin",
    "Ship Date": "ship_date",
}


def detect_encoding(path, sample_size=500_000):
    """Try common encodings on a byte sample rather than assuming UTF-8."""
    candidates = ["utf-8", "utf-8-sig", "cp1252", "latin1"]
    with open(path, "rb") as f:
        raw = f.read(sample_size)
    for enc in candidates:
        try:
            raw.decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue
    return "latin1"  # permissive last resort; latin1 never raises


def discount_bucket(discount):
    if discount == 0:
        return "0%"
    elif discount <= 0.10:
        return "1-10%"
    elif discount <= 0.20:
        return "10-20%"
    else:
        return "20%+"


def main():
    encoding = detect_encoding(RAW_PATH)
    print(f"Detected encoding: {encoding}")

    df = pd.read_csv(RAW_PATH, encoding=encoding)
    rows_loaded = len(df)
    print(f"Rows loaded: {rows_loaded}")

    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns=COLUMN_MAP)

    # drop rows that are entirely blank (trailing export artifacts)
    fully_blank = df.isna().all(axis=1).sum()
    if fully_blank:
        df = df[~df.isna().all(axis=1)]
        print(f"Fully blank rows dropped: {fully_blank}")

    # ---- parse dates: source uses M/D/YYYY without zero-padding ----
    try:
        df["order_date"] = pd.to_datetime(df["order_date"], format="mixed", errors="coerce")
        df["ship_date"] = pd.to_datetime(df["ship_date"], format="mixed", errors="coerce")
    except TypeError:
        # older pandas without format="mixed" support
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
        df["ship_date"] = pd.to_datetime(df["ship_date"], errors="coerce")

    bad_dates = df["order_date"].isna().sum()
    if bad_dates:
        print(f"Rows with unparseable order_date dropped: {bad_dates}")
        df = df[df["order_date"].notna()]

    # ---- null report (informational; only order_date/sales/profit/region/category matter downstream) ----
    null_report = df.isna().sum()
    null_report = null_report[null_report > 0]
    if len(null_report):
        print("Null values by column:")
        for col, cnt in null_report.items():
            print(f"  {col}: {cnt}")
    else:
        print("Null values by column: none")

    # ---- duplicates (ignore row_id, which is a row-order artifact, not business data) ----
    dedup_cols = [c for c in df.columns if c != "row_id"]
    dupes = df.duplicated(subset=dedup_cols).sum()
    df = df.drop_duplicates(subset=dedup_cols)
    print(f"Duplicate rows dropped: {dupes}")

    # ---- invalid rows: non-positive sales ----
    invalid_sales = (df["sales"] <= 0).sum()
    df = df[df["sales"] > 0]
    print(f"Invalid rows dropped (sales <= 0): {invalid_sales}")

    # ---- feature engineering ----
    df["year"] = df["order_date"].dt.year
    df["quarter"] = df["order_date"].dt.quarter
    df["month"] = df["order_date"].dt.month
    df["profit_margin"] = df["profit"] / df["sales"]
    df["discount_bucket"] = df["discount"].apply(discount_bucket)

    df["row_id"] = range(1, len(df) + 1)

    final_rows = len(df)
    df.to_csv(CLEAN_PATH, index=False)

    print("-" * 50)
    print("DATA QUALITY SUMMARY")
    print(f"  Rows loaded:        {rows_loaded}")
    print(f"  Duplicates dropped: {dupes}")
    print(f"  Invalid dropped:    {invalid_sales}")
    print(f"  Final row count:    {final_rows}")
    print(f"Cleaned file saved to {CLEAN_PATH}")


if __name__ == "__main__":
    main()
