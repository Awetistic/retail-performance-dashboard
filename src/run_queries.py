"""
run_queries.py — Executes every query in sql/business_questions.sql against
data/retail.db and prints row counts + a preview of each result. Useful both
as a validation check and as a quick way to eyeball the business answers.

Run from the project root:
    python src/run_queries.py
"""

import os
import re
import sqlite3
import pandas as pd

DB_PATH = os.path.join("data", "retail.db")
SQL_PATH = os.path.join("sql", "business_questions.sql")


def split_statements(sql_text):
    """Split on ';' but keep named blocks by grabbing the preceding comment as a label."""
    # Strip a leading run of comment lines as the label for each statement
    chunks = [c.strip() for c in sql_text.split(";") if c.strip()]
    labeled = []
    for chunk in chunks:
        lines = chunk.splitlines()
        label_lines = [l.strip("- ").strip() for l in lines if l.strip().startswith("--")]
        numbered = [l for l in label_lines if re.match(r"^\d+\.", l)]
        label = numbered[0] if numbered else (label_lines[0] if label_lines else "query")
        labeled.append((label, chunk))
    return labeled


def main():
    with open(SQL_PATH, "r") as f:
        sql_text = f.read()

    statements = split_statements(sql_text)
    conn = sqlite3.connect(DB_PATH)

    for i, (label, stmt) in enumerate(statements, start=1):
        try:
            result = pd.read_sql_query(stmt, conn)
            print(f"[{i}] {label}")
            print(f"    -> OK, {len(result)} row(s) returned")
            print(result.head(3).to_string(index=False).replace("\n", "\n    "))
            print()
        except Exception as e:
            print(f"[{i}] {label}")
            print(f"    -> FAILED: {type(e).__name__}: {e}")
            print()

    conn.close()


if __name__ == "__main__":
    main()
