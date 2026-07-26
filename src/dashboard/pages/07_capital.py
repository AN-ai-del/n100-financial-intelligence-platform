import os

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import get_companies


# =========================================================
# Page Header
# =========================================================

st.title("🧭 Capital Allocation Map")

st.caption(
    "Explore how Nifty 100 companies allocate capital across "
    "reinvestment, dividends, deleveraging and distress patterns."
)


# =========================================================
# Helpers
# =========================================================

def clean_id(value):
    if value is None or pd.isna(value):
        return ""

    return str(value).strip().upper()


def find_column(df, candidates):
    for candidate in candidates:
        if candidate in df.columns:
            return candidate

    return None


# =========================================================
# Locate Capital Allocation File
# =========================================================

candidate_paths = [
    "output/capital_allocation.csv",
    "capital_allocation.csv",
]


capital_path = None


for path in candidate_paths:
    if os.path.exists(path):
        capital_path = path
        break


if capital_path is None:
    st.error(
        "capital_allocation.csv could not be found. "
        "Expected location: output/capital_allocation.csv"
    )
    st.stop()


# =========================================================
# Load Data
# =========================================================

try:
    capital = pd.read_csv(
        capital_path
    )

    companies = get_companies()

except Exception as exc:
    st.error(
        "Unable to load capital-allocation data."
    )
    st.exception(exc)
    st.stop()


if capital.empty:
    st.error(
        "Capital-allocation data is empty."
    )
    st.stop()


# =========================================================
# Detect Columns
# =========================================================

company_col = find_column(
    capital,
    [
        "company_id",
        "ticker",
        "id",
        "symbol",
    ],
)


year_col = find_column(
    capital,
    [
        "year",
        "financial_year",
        "fiscal_year",
    ],
)


pattern_col = find_column(
    capital,
    [
        "pattern_label",
        "capital_allocation_label",
        "capital_allocation_pattern",
        "allocation_pattern",
        "pattern",
        "label",
        "capital_allocation",
    ],
)


if company_col is None:
    st.error(
        "Could not identify the company column "
        "in capital_allocation.csv."
    )

    st.write(
        "Available columns:",
        capital.columns.tolist(),
    )

    st.stop()


if pattern_col is None:
    st.error(
        "Could not identify the capital-allocation "
        "pattern column."
    )

    st.write(
        "Available columns:",
        capital.columns.tolist(),
    )

    st.stop()


# =========================================================
# Normalize IDs
# =========================================================

capital[company_col] = (
    capital[company_col]
    .apply(clean_id)
)


# =========================================================
# Official 92-company Universe
# =========================================================

official_ids = set()

company_lookup = pd.DataFrame()


if not companies.empty:

    master_id_col = find_column(
        companies,
        [
            "id",
            "company_id",
            "ticker",
        ],
    )

    name_col = find_column(
        companies,
        [
            "company_name",
            "name",
        ],
    )

    if master_id_col:

        official_ids = set(
            companies[
                master_id_col
            ]
            .dropna()
            .apply(clean_id)
            .tolist()
        )

    if (
        master_id_col
        and name_col
    ):

        company_lookup = companies[
            [
                master_id_col,
                name_col,
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


if official_ids:

    capital = capital[
        capital[
            company_col
        ].isin(
            official_ids
        )
    ].copy()


# =========================================================
# Latest Available Record Per Company
# =========================================================

if year_col:

    # Extract a numeric year safely.
    capital["_year_numeric"] = pd.to_numeric(
        capital[year_col],
        errors="coerce",
    )

    # If year values contain text such as "Mar 2024",
    # extract the four-digit year.
    missing_numeric = capital["_year_numeric"].isna()

    if missing_numeric.any():

        extracted_years = (
            capital.loc[
                missing_numeric,
                year_col,
            ]
            .astype(str)
            .str.extract(r"((?:19|20)\d{2})")[0]
        )

        capital.loc[
            missing_numeric,
            "_year_numeric",
        ] = pd.to_numeric(
            extracted_years,
            errors="coerce",
        )

    # -----------------------------------------------------
    # Keep each company's latest available classification.
    #
    # This is intentionally different from filtering every
    # company to one global year because a company may have
    # partial historical cash-flow data.
    # -----------------------------------------------------

    latest = (
        capital
        .sort_values(
            [
                company_col,
                "_year_numeric",
            ],
            ascending=[
                True,
                False,
            ],
        )
        .drop_duplicates(
            subset=[
                company_col,
            ],
            keep="first",
        )
        .copy()
    )

    available_years = (
        latest[
            "_year_numeric"
        ]
        .dropna()
        .astype(int)
    )

    latest_year = (
        int(
            available_years.max()
        )
        if not available_years.empty
        else None
    )

else:

    latest_year = None

    latest = (
        capital
        .drop_duplicates(
            subset=[
                company_col,
            ],
            keep="last",
        )
        .copy()
    )

# =========================================================
# Add Company Names
# =========================================================

latest = latest.rename(
    columns={
        company_col: "company_id",
        pattern_col: "capital_allocation_pattern",
    }
)


if not company_lookup.empty:

    latest = latest.merge(
        company_lookup,
        on="company_id",
        how="left",
    )


if "company_name" not in latest.columns:

    latest[
        "company_name"
    ] = latest[
        "company_id"
    ]


latest[
    "company_name"
] = latest[
    "company_name"
].fillna(
    latest[
        "company_id"
    ]
)


latest[
    "capital_allocation_pattern"
] = (
    latest[
        "capital_allocation_pattern"
    ]
    .fillna(
        "Unknown"
    )
    .astype(str)
    .str.strip()
)


# =========================================================
# Summary
# =========================================================

st.divider()

title = "Latest Available Capital Allocation Distribution"

st.subheader(
    f"📊 {title}"
)


c1, c2, c3 = st.columns(3)


c1.metric(
    "Companies Classified",
    latest[
        "company_id"
    ].nunique(),
)


c2.metric(
    "Allocation Patterns",
    latest[
        "capital_allocation_pattern"
    ].nunique(),
)


largest_pattern = (
    latest[
        "capital_allocation_pattern"
    ]
    .value_counts()
)


c3.metric(
    "Most Common Pattern",
    (
        largest_pattern.index[0]
        if not largest_pattern.empty
        else "N/A"
    ),
)


# =========================================================
# Pattern Counts
# =========================================================

pattern_counts = (
    latest
    .groupby(
        "capital_allocation_pattern"
    )
    .agg(
        company_count=(
            "company_id",
            "nunique",
        )
    )
    .reset_index()
    .sort_values(
        "company_count",
        ascending=False,
    )
)


# =========================================================
# Treemap
# =========================================================

st.divider()

st.subheader(
    "🌳 Capital Allocation Treemap"
)


treemap = px.treemap(
    latest,
    path=[
        "capital_allocation_pattern",
        "company_id",
    ],
    values=None,
    hover_name="company_name",
)


treemap.update_layout(
    height=650,
    margin=dict(
        l=10,
        r=10,
        t=30,
        b=10,
    ),
)


st.plotly_chart(
    treemap,
    use_container_width=True,
)


st.caption(
    "Each company is grouped according to its latest "
    "capital-allocation pattern."
)


# =========================================================
# Distribution Chart
# =========================================================

st.divider()

st.subheader(
    "📈 Allocation Pattern Distribution"
)


distribution_chart = px.bar(
    pattern_counts,
    x="capital_allocation_pattern",
    y="company_count",
    text_auto=True,
    labels={
        "capital_allocation_pattern":
            "Capital Allocation Pattern",

        "company_count":
            "Companies",
    },
)


distribution_chart.update_layout(
    height=500,
    xaxis_title=(
        "Capital Allocation Pattern"
    ),
    yaxis_title=(
        "Number of Companies"
    ),
)


st.plotly_chart(
    distribution_chart,
    use_container_width=True,
)


# =========================================================
# Pattern Selector
# =========================================================

st.divider()

st.subheader(
    "🔎 Companies by Allocation Pattern"
)


pattern_options = sorted(
    latest[
        "capital_allocation_pattern"
    ]
    .dropna()
    .unique()
    .tolist()
)


selected_pattern = st.selectbox(
    "Select capital allocation pattern",
    pattern_options,
)


selected_companies = latest[
    latest[
        "capital_allocation_pattern"
    ] == selected_pattern
].copy()


# =========================================================
# Selected Pattern Metrics
# =========================================================

m1, m2 = st.columns(2)


m1.metric(
    "Selected Pattern",
    selected_pattern,
)


m2.metric(
    "Companies",
    selected_companies[
        "company_id"
    ].nunique(),
)


# =========================================================
# Company List
# =========================================================

company_table = selected_companies[
    [
        "company_id",
        "company_name",
        "capital_allocation_pattern",
    ]
].copy()


company_table = company_table.rename(
    columns={
        "company_id":
            "Ticker",

        "company_name":
            "Company",

        "capital_allocation_pattern":
            "Capital Allocation Pattern",
    }
)


company_table = company_table.sort_values(
    "Ticker"
)


st.dataframe(
    company_table,
    use_container_width=True,
    hide_index=True,
)


# =========================================================
# Download
# =========================================================

csv_data = (
    company_table
    .to_csv(
        index=False
    )
    .encode(
        "utf-8"
    )
)


st.download_button(
    "⬇️ Download Pattern Companies as CSV",
    data=csv_data,
    file_name=(
        selected_pattern
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        + "_companies.csv"
    ),
    mime="text/csv",
)


# =========================================================
# Full Distribution Table
# =========================================================

st.divider()

st.subheader(
    "Capital Allocation Summary"
)


summary_display = pattern_counts.rename(
    columns={
        "capital_allocation_pattern":
            "Pattern",

        "company_count":
            "Companies",
    }
)


st.dataframe(
    summary_display,
    use_container_width=True,
    hide_index=True,
)


st.caption(
    "Capital-allocation classifications come from "
    "the Sprint 2 capital-allocation engine."
)