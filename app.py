"""
app.py — Retail Performance Dashboard (Streamlit)

Reads data/retail.db (built by src/build_db.py), lets the user filter by
region, category, and order date range, and shows KPIs plus three tabs of
Plotly charts. Insight sentences at the bottom of two tabs are computed from
the live filtered data, not hardcoded.

Run:
    streamlit run app.py
"""

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB_PATH = Path(__file__).parent / "data" / "retail.db"

# Deliberate palette (not Plotly/Streamlit defaults) — see README for the
# design rationale: confident blue for trust, teal for growth, amber for
# discount/attention, muted red for loss.
PALETTE = ["#2454A6", "#1E8A6B", "#E0912F", "#7B5EA7", "#C0392B", "#5FA8D3"]
MARGIN_SCALE = ["#C0392B", "#E0912F", "#F4D35E", "#8FBF6F", "#1E8A6B"]
BUCKET_ORDER = ["0%", "1-10%", "10-20%", "20%+"]

st.set_page_config(page_title="Retail Performance Dashboard", layout="wide", page_icon="📊")


@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT * FROM transactions", conn, parse_dates=["order_date", "ship_date"]
    )
    conn.close()
    return df


def aggregate_margin(sales, profit):
    """Correct blended margin = SUM(profit)/SUM(sales), not an average of
    row-level ratios (which is skewed by outlier low-sales/high-loss rows —
    see the note in sql/business_questions.sql)."""
    total_sales = sales.sum()
    return (profit.sum() / total_sales * 100) if total_sales else 0.0


df = load_data()

# ---------------- Sidebar filters ----------------
st.sidebar.header("Filters")

regions = sorted(df["region"].unique())
sel_regions = st.sidebar.multiselect("Region", regions, default=regions)

categories = sorted(df["category"].unique())
sel_categories = st.sidebar.multiselect("Category", categories, default=categories)

min_date = df["order_date"].min().date()
max_date = df["order_date"].max().date()
date_range = st.sidebar.date_input(
    "Order Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

mask = (
    df["region"].isin(sel_regions)
    & df["category"].isin(sel_categories)
    & (df["order_date"].dt.date >= start_date)
    & (df["order_date"].dt.date <= end_date)
)
fdf = df[mask]

st.title("📊 Retail Performance Dashboard")
st.caption(
    f"{len(fdf):,} transactions · {fdf['order_date'].min().date() if len(fdf) else '—'} "
    f"to {fdf['order_date'].max().date() if len(fdf) else '—'}"
)

if fdf.empty:
    st.warning("No data matches the current filters. Adjust the filters in the sidebar.")
    st.stop()

# ---------------- KPI row ----------------
total_revenue = fdf["sales"].sum()
total_profit = fdf["profit"].sum()
margin_pct = aggregate_margin(fdf["sales"], fdf["profit"])
total_orders = fdf["order_id"].nunique()
avg_order_value = total_revenue / total_orders if total_orders else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Revenue", f"${total_revenue:,.0f}")
k2.metric("Total Profit", f"${total_profit:,.0f}", f"{margin_pct:.1f}% margin")
k3.metric("Total Orders", f"{total_orders:,}")
k4.metric("Avg Order Value", f"${avg_order_value:,.2f}")

st.divider()

tab1, tab2, tab3 = st.tabs(["Overview", "Inventory & Products", "Discounts & Regions"])

# ================= Tab 1: Overview =================
with tab1:
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Revenue & Profit Trend")
        trend = (
            fdf.groupby(pd.Grouper(key="order_date", freq="MS"))
            .agg(revenue=("sales", "sum"), profit=("profit", "sum"))
            .reset_index()
        )
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trend["order_date"], y=trend["revenue"], name="Revenue",
            mode="lines", line=dict(color=PALETTE[0], width=2.5),
        ))
        fig.add_trace(go.Scatter(
            x=trend["order_date"], y=trend["profit"], name="Profit",
            mode="lines", line=dict(color=PALETTE[1], width=2.5),
        ))
        fig.update_layout(hovermode="x unified", margin=dict(t=10, l=0, r=0), height=380)
        st.plotly_chart(fig, width='stretch')

    with col2:
        st.subheader("Revenue by Category")
        cat_rev = fdf.groupby("category", as_index=False)["sales"].sum()
        fig2 = px.pie(
            cat_rev, names="category", values="sales", hole=0.45,
            color_discrete_sequence=PALETTE,
        )
        fig2.update_layout(margin=dict(t=10, l=0, r=0), height=380)
        st.plotly_chart(fig2, width='stretch')

    st.subheader("Orders by Customer Segment")
    seg = (
        fdf.groupby("segment", as_index=False)["order_id"]
        .nunique()
        .rename(columns={"order_id": "orders"})
        .sort_values("orders", ascending=False)
    )
    fig3 = px.bar(seg, x="segment", y="orders", color="segment", color_discrete_sequence=PALETTE)
    fig3.update_layout(margin=dict(t=10), showlegend=False, height=320)
    st.plotly_chart(fig3, width='stretch')

# ================= Tab 2: Inventory & Products =================
with tab2:
    subcat_stats = fdf.groupby("sub_category", as_index=False).agg(
        revenue=("sales", "sum"), profit=("profit", "sum"), avg_discount=("discount", "mean")
    )
    subcat_stats["margin_pct"] = subcat_stats["profit"] / subcat_stats["revenue"] * 100
    subcat_stats["avg_discount_pct"] = subcat_stats["avg_discount"] * 100
    subcat_stats = subcat_stats.sort_values("revenue", ascending=False)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Top 10 Sub-Categories by Revenue")
        top10 = subcat_stats.head(10)
        fig4 = px.bar(
            top10.sort_values("revenue"), x="revenue", y="sub_category", orientation="h",
            color_discrete_sequence=[PALETTE[0]],
        )
        fig4.update_layout(margin=dict(t=10), height=400, yaxis_title="", xaxis_title="Revenue ($)")
        st.plotly_chart(fig4, width='stretch')

    with c2:
        st.subheader("Bottom 10 Sub-Categories by Revenue")
        bottom10 = subcat_stats.tail(10)
        fig5 = px.bar(
            bottom10.sort_values("revenue"), x="revenue", y="sub_category", orientation="h",
            color_discrete_sequence=[PALETTE[4]],
        )
        fig5.update_layout(margin=dict(t=10), height=400, yaxis_title="", xaxis_title="Revenue ($)")
        st.plotly_chart(fig5, width='stretch')

    if len(subcat_stats) >= 2:
        weakest = subcat_stats.loc[subcat_stats["margin_pct"].idxmin()]
        strongest_rev = subcat_stats.iloc[0]
        insight = (
            f"💡 **Insight:** *{strongest_rev['sub_category']}* leads in revenue at "
            f"${strongest_rev['revenue']:,.0f}. *{weakest['sub_category']}* is the weakest-performing "
            f"sub-category in the current filter, at a {weakest['margin_pct']:.1f}% profit margin "
            f"with an average discount of {weakest['avg_discount_pct']:.1f}%."
        )
        st.info(insight)

# ================= Tab 3: Discounts & Regions =================
with tab3:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Discount % vs Profit Margin by Sub-Category")
        scatter_data = subcat_stats.copy()
        scatter_data = scatter_data.merge(
            fdf[["sub_category", "category"]].drop_duplicates(), on="sub_category"
        )
        fig6 = px.scatter(
            scatter_data, x="avg_discount_pct", y="margin_pct", color="category",
            size="revenue", hover_name="sub_category", color_discrete_sequence=PALETTE,
            labels={"avg_discount_pct": "Avg Discount %", "margin_pct": "Profit Margin %"},
        )
        fig6.add_hline(y=0, line_dash="dot", line_color="#999999")
        fig6.update_layout(margin=dict(t=10), height=400)
        st.plotly_chart(fig6, width='stretch')

    with c2:
        st.subheader("Profit Margin by Discount Bucket")
        bucket_margin = fdf.groupby("discount_bucket", as_index=False).agg(
            total_sales=("sales", "sum"),
            total_profit=("profit", "sum"),
            num_orders=("sales", "size"),
        )
        bucket_margin["margin_pct"] = bucket_margin["total_profit"] / bucket_margin["total_sales"] * 100
        bucket_margin["discount_bucket"] = pd.Categorical(
            bucket_margin["discount_bucket"], categories=BUCKET_ORDER, ordered=True
        )
        bucket_margin = bucket_margin.sort_values("discount_bucket")
        fig7 = px.bar(
            bucket_margin, x="discount_bucket", y="margin_pct",
            color="margin_pct", color_continuous_scale=MARGIN_SCALE,
        )
        fig7.add_hline(y=0, line_dash="dot", line_color="#999999")
        fig7.update_layout(
            margin=dict(t=10), height=400, coloraxis_showscale=False,
            xaxis_title="Discount Bucket", yaxis_title="Profit Margin %",
        )
        st.plotly_chart(fig7, width='stretch')

    st.subheader("Region Comparison")
    region_perf = fdf.groupby("region", as_index=False).agg(
        revenue=("sales", "sum"), profit=("profit", "sum")
    ).sort_values("revenue", ascending=False)
    fig8 = px.bar(
        region_perf, x="region", y=["revenue", "profit"], barmode="group",
        color_discrete_sequence=[PALETTE[0], PALETTE[1]],
    )
    fig8.update_layout(margin=dict(t=10), height=380, xaxis_title="", yaxis_title="$")
    st.plotly_chart(fig8, width='stretch')

    if len(region_perf) >= 2 and len(bucket_margin) >= 2:
        region_perf["margin_pct"] = region_perf["profit"] / region_perf["revenue"] * 100
        top_region = region_perf.iloc[0]
        weak_region = region_perf.loc[region_perf["margin_pct"].idxmin()]
        worst_bucket = bucket_margin.iloc[-1]
        insight2 = (
            f"💡 **Insight:** *{top_region['region']}* is the top region by revenue at "
            f"${top_region['revenue']:,.0f}, though *{weak_region['region']}* runs the thinnest "
            f"regional margin at {weak_region['margin_pct']:.1f}%. Orders discounted "
            f"**{worst_bucket['discount_bucket']}** average a {worst_bucket['margin_pct']:.1f}% margin "
            f"in the current filter."
        )
        st.info(insight2)

st.caption("Use the sidebar to filter by region, category, and order date range — every chart and insight above recomputes live.")
