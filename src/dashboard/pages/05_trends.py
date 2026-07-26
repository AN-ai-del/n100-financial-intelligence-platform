import re

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import (
    get_companies,
    run_query,
)


# =========================================================
# Page Header
# =========================================================

st.title("📈 Financial Trend Analysis")

st.caption(
    "Track revenue, profitability, margins and return ratios "
    "across the Nifty 100 universe."
)


# =========================================================
# Helper Functions
# =========================================================

def find_column(df, candidates):
    for candidate in candidates:
        if candidate in df.columns:
            return candidate

    return None


def extract_year(value):
    if value is None or pd.isna(value):
        return None

    match = re.search(
        r"(19|20)\d{2}",
        str(value),
    )

    if not match:
        return None

    return int(match.group())


def clean_id(value):
    if value is None or pd.isna(value):
        return ""

    return str(value).strip().upper()


def repair_header_table(df):
    """
    Promote row 0 to column headers when SQLite contains
    metadata-style column names such as unnamed:_1.
    """

    if df.empty:
        return df

    has_unnamed = any(
        str(column)
        .lower()
        .startswith("unnamed")
        for column in df.columns
    )

    if not has_unnamed:
        output = df.copy()

        output.columns = (
            output.columns
            .astype(str)
            .str.strip()
            .str.lower()
            .str.replace(" ", "_")
            .str.replace(
                r"[^\w]+",
                "_",
                regex=True,
            )
            .str.strip("_")
        )

        return output

    first_row = df.iloc[0]

    new_columns = []

    for index, value in enumerate(first_row):

        if value is None or pd.isna(value):
            new_columns.append(
                f"column_{index}"
            )
            continue

        column = (
            str(value)
            .strip()
            .lower()
        )

        column = re.sub(
            r"[^\w]+",
            "_",
            column,
        ).strip("_")

        new_columns.append(
            column or f"column_{index}"
        )

    output = df.iloc[1:].copy()

    output.columns = new_columns

    output = (
        output
        .dropna(how="all")
        .reset_index(drop=True)
    )

    return output


def numeric_series(series):
    return pd.to_numeric(
        series,
        errors="coerce",
    )


# =========================================================
# Load Data
# =========================================================

try:
    companies = get_companies()

    pnl_raw = run_query(
        "SELECT * FROM profitandloss"
    )

    ratios = run_query(
        "SELECT * FROM financial_ratios"
    )

except Exception as exc:
    st.error(
        "Unable to load financial trend data."
    )

    st.exception(exc)
    st.stop()


if pnl_raw.empty:
    st.warning(
        "Profit-and-loss history is unavailable."
    )
    st.stop()


# =========================================================
# Repair P&L Table
# =========================================================

pnl = repair_header_table(
    pnl_raw
)


# =========================================================
# Detect Columns
# =========================================================

pnl_company_col = find_column(
    pnl,
    [
        "company_id",
        "ticker",
        "symbol",
        "id",
    ],
)

pnl_year_col = find_column(
    pnl,
    [
        "year",
        "financial_year",
        "fiscal_year",
    ],
)

sales_col = find_column(
    pnl,
    [
        "sales",
        "revenue",
        "total_revenue",
    ],
)

profit_col = find_column(
    pnl,
    [
        "net_profit",
        "profit_after_tax",
        "pat",
    ],
)

operating_profit_col = find_column(
    pnl,
    [
        "operating_profit",
        "ebit",
        "ebitda",
    ],
)

opm_col = find_column(
    pnl,
    [
        "opm_percentage",
        "opm_pct",
        "operating_profit_margin_pct",
        "operating_margin",
    ],
)


if (
    pnl_company_col is None
    or pnl_year_col is None
):
    st.error(
        "The repaired profit-and-loss table still does not "
        "contain company/year columns."
    )

    st.write(
        pnl.columns.tolist()
    )

    st.stop()


# =========================================================
# Clean P&L Data
# =========================================================

pnl[pnl_company_col] = (
    pnl[pnl_company_col]
    .apply(clean_id)
)


pnl["_year_numeric"] = (
    pnl[pnl_year_col]
    .apply(extract_year)
)


pnl = pnl[
    (
        pnl[pnl_company_col] != ""
    )
    &
    (
        pnl["_year_numeric"].notna()
    )
].copy()


for column in [
    sales_col,
    profit_col,
    operating_profit_col,
    opm_col,
]:

    if column:
        pnl[column] = numeric_series(
            pnl[column]
        )


# =========================================================
# Company Names
# =========================================================

if not companies.empty:

    company_id_col = find_column(
        companies,
        [
            "id",
            "company_id",
            "ticker",
        ],
    )

    company_name_col = find_column(
        companies,
        [
            "company_name",
            "name",
        ],
    )

    if (
        company_id_col
        and company_name_col
    ):

        company_lookup = companies[
            [
                company_id_col,
                company_name_col,
            ]
        ].copy()

        company_lookup.columns = [
            "company_id",
            "company_name",
        ]

        company_lookup[
            "company_id"
        ] = (
            company_lookup[
                "company_id"
            ]
            .apply(clean_id)
        )

        company_lookup = (
            company_lookup
            .drop_duplicates(
                "company_id"
            )
        )

        pnl = pnl.merge(
            company_lookup,
            left_on=pnl_company_col,
            right_on="company_id",
            how="left",
        )


if "company_name" not in pnl.columns:
    pnl["company_name"] = pnl[
        pnl_company_col
    ]


pnl["company_name"] = (
    pnl["company_name"]
    .fillna(
        pnl[pnl_company_col]
    )
)


pnl["Ticker"] = pnl[
    pnl_company_col
]

pnl["Company"] = pnl[
    "company_name"
]


# =========================================================
# Restrict analysis to the official 92-company universe
# =========================================================

if not companies.empty:

    master_id_col = find_column(
        companies,
        [
            "id",
            "company_id",
            "ticker",
        ],
    )

    if master_id_col:

        official_company_ids = set(
            companies[
                master_id_col
            ]
            .dropna()
            .apply(clean_id)
            .tolist()
        )

        pnl = pnl[
            pnl["Ticker"].isin(
                official_company_ids
            )
        ].copy()


# =========================================================
# Sort and Deduplicate
# =========================================================

pnl = (
    pnl
    .sort_values(
        [
            "Ticker",
            "_year_numeric",
        ]
    )
    .drop_duplicates(
        subset=[
            "Ticker",
            "_year_numeric",
        ],
        keep="last",
    )
    .reset_index(drop=True)
)


pnl[
    "Financial Year"
] = pnl[
    "_year_numeric"
].astype(int)


# =========================================================
# Calculate YoY Growth
# =========================================================

if sales_col:

    pnl[
        "Revenue Growth %"
    ] = (
        pnl
        .groupby("Ticker")[
            sales_col
        ]
        .pct_change(
            fill_method=None
        )
        * 100
    )


if profit_col:

    pnl[
        "Profit Growth %"
    ] = (
        pnl
        .groupby("Ticker")[
            profit_col
        ]
        .pct_change(
            fill_method=None
        )
        * 100
    )


# =========================================================
# Sidebar Controls
# =========================================================

st.sidebar.header(
    "Trend Controls"
)


available_years = sorted(
    pnl[
        "Financial Year"
    ]
    .dropna()
    .unique()
    .tolist(),
    reverse=True,
)


selected_year = st.sidebar.selectbox(
    "Financial Year",
    available_years,
)


metric_options = {}


if sales_col:
    metric_options[
        "Revenue"
    ] = sales_col


if profit_col:
    metric_options[
        "Net Profit"
    ] = profit_col


if operating_profit_col:
    metric_options[
        "Operating Profit"
    ] = operating_profit_col


if opm_col:
    metric_options[
        "Operating Margin"
    ] = opm_col


if not metric_options:
    st.error(
        "No supported financial metrics were found."
    )
    st.stop()


selected_metric_name = st.sidebar.selectbox(
    "Primary Metric",
    list(
        metric_options.keys()
    ),
)


selected_metric = (
    metric_options[
        selected_metric_name
    ]
)


top_n = st.sidebar.slider(
    "Number of companies",
    min_value=5,
    max_value=20,
    value=10,
)


# =========================================================
# Current Year Snapshot
# =========================================================

current = pnl[
    pnl[
        "Financial Year"
    ] == selected_year
].copy()


st.divider()

st.subheader(
    f"📊 {selected_year} Market Snapshot"
)


c1, c2, c3 = st.columns(3)


with c1:

    st.metric(
        "Companies Available",
        current[
            "Ticker"
        ].nunique(),
    )


with c2:

    metric_values = (
        current[
            selected_metric
        ]
        .replace(
            [
                np.inf,
                -np.inf,
            ],
            np.nan,
        )
        .dropna()
    )


    median_value = (
        metric_values.median()
        if not metric_values.empty
        else np.nan
    )


    if pd.isna(
        median_value
    ):

        median_display = "N/A"

    elif (
        selected_metric_name
        == "Operating Margin"
    ):

        median_display = (
            f"{median_value:,.2f}%"
        )

    else:

        median_display = (
            f"{median_value:,.2f}"
        )


    st.metric(
        f"Median {selected_metric_name}",
        median_display,
    )


with c3:

    positive_count = int(
        (
            current[
                selected_metric
            ] > 0
        ).sum()
    )


    st.metric(
        f"Positive {selected_metric_name}",
        positive_count,
    )


# =========================================================
# Top Companies
# =========================================================

st.divider()

st.subheader(
    f"🏆 Top {top_n} Companies by "
    f"{selected_metric_name}"
)


ranking = (
    current[
        [
            "Ticker",
            "Company",
            selected_metric,
        ]
    ]
    .replace(
        [
            np.inf,
            -np.inf,
        ],
        np.nan,
    )
    .dropna(
        subset=[
            selected_metric,
        ]
    )
    .sort_values(
        selected_metric,
        ascending=False,
    )
    .head(top_n)
)


if ranking.empty:

    st.info(
        "No ranking data is available."
    )

else:

    fig = px.bar(
        ranking.sort_values(
            selected_metric
        ),
        x=selected_metric,
        y="Ticker",
        orientation="h",
        hover_data=[
            "Company",
        ],
    )


    fig.update_layout(
        height=500,
        xaxis_title=(
            selected_metric_name
        ),
        yaxis_title="Ticker",
    )


    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# =========================================================
# Growth Leaders
# =========================================================

st.divider()

st.subheader(
    "🚀 Growth Leaders"
)


left, right = st.columns(2)


with left:

    st.markdown(
        "### Revenue Growth"
    )


    if (
        "Revenue Growth %"
        in current.columns
    ):

        revenue_growth = (
            current[
                [
                    "Ticker",
                    "Company",
                    "Revenue Growth %",
                ]
            ]
            .replace(
                [
                    np.inf,
                    -np.inf,
                ],
                np.nan,
            )
            .dropna(
                subset=[
                    "Revenue Growth %",
                ]
            )
            .sort_values(
                "Revenue Growth %",
                ascending=False,
            )
            .head(top_n)
        )


        st.dataframe(
            revenue_growth,
            use_container_width=True,
            hide_index=True,
        )


    else:

        st.info(
            "Revenue growth unavailable."
        )


with right:

    st.markdown(
        "### Net Profit Growth"
    )


    if (
        "Profit Growth %"
        in current.columns
    ):

        profit_growth = (
            current[
                [
                    "Ticker",
                    "Company",
                    "Profit Growth %",
                ]
            ]
            .replace(
                [
                    np.inf,
                    -np.inf,
                ],
                np.nan,
            )
            .dropna(
                subset=[
                    "Profit Growth %",
                ]
            )
            .sort_values(
                "Profit Growth %",
                ascending=False,
            )
            .head(top_n)
        )


        st.dataframe(
            profit_growth,
            use_container_width=True,
            hide_index=True,
        )


    else:

        st.info(
            "Net-profit growth unavailable."
        )


# =========================================================
# Multi-metric Company Trend
# =========================================================

st.divider()

st.subheader(
    "📉 Company Trend Explorer"
)


company_options = (
    pnl[
        [
            "Ticker",
            "Company",
        ]
    ]
    .drop_duplicates()
    .sort_values(
        "Ticker"
    )
)


labels = {
    (
        f"{row['Ticker']} — "
        f"{row['Company']}"
    ): row["Ticker"]
    for _, row
    in company_options.iterrows()
}


selected_company_label = st.selectbox(
    "Select company",
    list(
        labels.keys()
    ),
)


selected_ticker = labels[
    selected_company_label
]


trend_metric_options = {}


if sales_col:
    trend_metric_options[
        "Revenue"
    ] = sales_col


if profit_col:
    trend_metric_options[
        "Net Profit"
    ] = profit_col


if operating_profit_col:
    trend_metric_options[
        "Operating Profit"
    ] = operating_profit_col


if opm_col:
    trend_metric_options[
        "Operating Margin"
    ] = opm_col


selected_trend_metrics = (
    st.multiselect(
        "Select up to 3 metrics",
        options=list(
            trend_metric_options.keys()
        ),
        default=list(
            trend_metric_options.keys()
        )[:2],
        max_selections=3,
    )
)


company_history = pnl[
    pnl["Ticker"]
    == selected_ticker
].copy()


if (
    company_history.empty
    or not selected_trend_metrics
):

    st.info(
        "Select a company and at least "
        "one metric."
    )

else:

    chart = px.line()


    for metric_name in (
        selected_trend_metrics
    ):

        column = (
            trend_metric_options[
                metric_name
            ]
        )


        chart.add_scatter(
            x=company_history[
                "Financial Year"
            ],
            y=company_history[
                column
            ],
            mode=(
                "lines+markers+text"
            ),
            name=metric_name,
        )


    chart.update_layout(
        height=520,
        xaxis_title=(
            "Financial Year"
        ),
        yaxis_title=(
            "Metric Value"
        ),
    )


    st.plotly_chart(
        chart,
        use_container_width=True,
    )


# =========================================================
# YoY Change Table / Annotations
# =========================================================

st.subheader(
    "Year-over-Year Changes"
)


change_columns = [
    "Financial Year",
]


if (
    "Revenue Growth %"
    in company_history.columns
):

    change_columns.append(
        "Revenue Growth %"
    )


if (
    "Profit Growth %"
    in company_history.columns
):

    change_columns.append(
        "Profit Growth %"
    )


changes = (
    company_history[
        change_columns
    ]
    .tail(10)
    .copy()
)


for column in changes.columns:

    if column.endswith("%"):

        changes[column] = (
            pd.to_numeric(
                changes[column],
                errors="coerce",
            )
            .round(2)
        )


st.dataframe(
    changes,
    use_container_width=True,
    hide_index=True,
)


# =========================================================
# Latest Improvers / Deteriorators
# =========================================================

st.divider()

st.subheader(
    "🔥 Latest Financial Momentum"
)


momentum_column = None


if (
    selected_metric
    == sales_col
):

    momentum_column = (
        "Revenue Growth %"
    )


elif (
    selected_metric
    == profit_col
):

    momentum_column = (
        "Profit Growth %"
    )


if (
    momentum_column
    and momentum_column
    in current.columns
):

    momentum = (
        current[
            [
                "Ticker",
                "Company",
                momentum_column,
            ]
        ]
        .replace(
            [
                np.inf,
                -np.inf,
            ],
            np.nan,
        )
        .dropna(
            subset=[
                momentum_column,
            ]
        )
    )


    improving = (
        momentum
        .sort_values(
            momentum_column,
            ascending=False,
        )
        .head(5)
    )


    deteriorating = (
        momentum
        .sort_values(
            momentum_column,
            ascending=True,
        )
        .head(5)
    )


    c1, c2 = st.columns(2)


    with c1:

        st.markdown(
            "### 🟢 Top Improvers"
        )

        st.dataframe(
            improving,
            use_container_width=True,
            hide_index=True,
        )


    with c2:

        st.markdown(
            "### 🔴 Top Deteriorators"
        )

        st.dataframe(
            deteriorating,
            use_container_width=True,
            hide_index=True,
        )


else:

    st.info(
        "Momentum ranking is available "
        "for Revenue and Net Profit."
    )


# =========================================================
# CSV Download
# =========================================================

st.divider()


export_columns = [
    "Ticker",
    "Company",
    "Financial Year",
]


for column in [
    sales_col,
    profit_col,
    operating_profit_col,
    opm_col,
    "Revenue Growth %",
    "Profit Growth %",
]:

    if (
        column
        and column in pnl.columns
    ):

        export_columns.append(
            column
        )


export_columns = list(
    dict.fromkeys(
        export_columns
    )
)


export_data = pnl[
    export_columns
].copy()


csv_data = (
    export_data
    .to_csv(
        index=False
    )
    .encode(
        "utf-8"
    )
)


st.download_button(
    "⬇️ Download Trend Data as CSV",
    data=csv_data,
    file_name=(
        "nifty100_financial_trends.csv"
    ),
    mime="text/csv",
)


st.caption(
    "Trend calculations use the historical financial records "
    "available in the supplied project dataset."
)