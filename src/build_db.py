"""
build_db.py — Loads the cleaned retail CSV into a SQLite database and
creates indexes to support the dashboard's filters and the business-question
queries in sql/business_questions.sql.

Run from the project root:
    python src/build_db.py
"""

import os
import sqlite3
import pandas as pd

CLEAN_PATH = os.path.join("data", "cleaned_superstore_sales.csv")
DB_PATH = os.path.join("data", "retail.db")
TABLE_NAME = "transactions"


def main():
    df = pd.read_csv(CLEAN_PATH, parse_dates=["order_date", "ship_date"])
    df["order_date"] = df["order_date"].dt.strftime("%Y-%m-%d")
    df["ship_date"] = df["ship_date"].dt.strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_PATH)
    df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)

    cur = conn.cursor()
    indexes = {
        "idx_region": "region",
        "idx_category": "category",
        "idx_sub_category": "sub_category",
        "idx_order_date": "order_date",
        "idx_year_month": "year, month",
    }
    for idx_name, cols in indexes.items():
        cur.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {TABLE_NAME} ({cols})")
    conn.commit()

    row_count = cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]

    print(f"Database built: {DB_PATH}")
    print(f"Table '{TABLE_NAME}' row count: {row_count}")
    print("Indexes created:")
    for idx_name, cols in indexes.items():
        print(f"  {idx_name} ON ({cols})")

    conn.close()


if __name__ == "__main__":
    main()
