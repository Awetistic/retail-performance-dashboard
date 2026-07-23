# Retail Performance Dashboard

An interactive, filterable dashboard for retail transaction data — built to
replace static, slow-to-update spreadsheets with a live, drillable view of
revenue, profit, inventory, and discount performance across regions and
categories.

## About the data

This project uses a **real** (not synthetic) order-level retail transactions
dataset — 8,399 orders from 2009–2012, across 8 Canadian regions/provinces,
3 product categories, and 17 sub-categories — fetched directly from a public
GitHub mirror:
`https://raw.githubusercontent.com/curran/data/gh-pages/superstoreSales/superstoreSales.csv`

It's part of the same "Superstore Sales" dataset lineage widely used in
Tableau/BI training material. The raw file ships with genuine real-world
messiness that `src/clean_data.py` handles explicitly: it's `cp1252`-encoded
(not UTF-8), and dates are `M/D/YYYY` without zero-padding.

**If you'd rather use a different or more current dataset** (e.g. the
classic US-regions "Sample Superstore" from Kaggle, which needs a Kaggle
login this environment doesn't have), drop a CSV with the same core columns
(order date, region, category, sub-category, sales, discount, profit,
quantity) into `data/`, adjust the `COLUMN_MAP` at the top of
`src/clean_data.py` to match its headers, and everything downstream
(`build_db.py`, the SQL, `app.py`) works unchanged.

## Tech stack

| Layer           | Tool                |
|------------------|----------------------|
| Data storage     | SQLite               |
| Data processing  | pandas, numpy        |
| Dashboard        | Streamlit            |
| Charts           | Plotly               |
| Language         | Python 3.10+         |

## File structure

```
retail-performance-dashboard/
├── app.py                            # Streamlit dashboard
├── requirements.txt
├── .gitignore
├── README.md
├── .streamlit/
│   └── config.toml                   # dashboard color theme
├── data/
│   ├── raw_superstore_sales.csv      # raw data, as fetched
│   ├── cleaned_superstore_sales.csv  # cleaned + feature-engineered
│   └── retail.db                     # SQLite database used by app.py
├── src/
│   ├── clean_data.py                 # encoding/date parsing, cleaning, feature engineering
│   ├── build_db.py                   # loads cleaned CSV into SQLite + indexes
│   └── run_queries.py                # runs & validates every query in sql/business_questions.sql
└── sql/
    └── business_questions.sql        # inventory / discount / regional business questions
```

## Running locally

```bash
git clone <your-repo-url>
cd retail-performance-dashboard
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# data/ already ships pre-built — only re-run these if you swap in new source data
python src/clean_data.py
python src/build_db.py
python src/run_queries.py       # optional: prints all 7 business-question results

streamlit run app.py
```

The app opens at `http://localhost:8501`.

## A data-quality note worth knowing

While validating `sql/business_questions.sql`, two of the original queries
computed profit margin as `AVG(profit_margin)` — a simple average of each
row's own profit/sales ratio. That's a real pitfall: a handful of orders
with small sales but a large dollar loss (e.g. $188 in sales against a
$2,150 loss — a -1144% row) skew a simple average heavily even though
they barely register in total dollars. Every margin figure in the SQL and
in `app.py` now uses the aggregate ("blended") margin, `SUM(profit) /
SUM(sales)`, which is what "our profit margin" means in a business context.
