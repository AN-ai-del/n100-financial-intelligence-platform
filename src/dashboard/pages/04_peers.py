import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import (
    find_column,
    get_companies,
    get_ratios,
    run_query,
)


# =========================================================
# Page Header
# =========================================================

st.title("👥 Peer Comparison")

st.caption(
    "Compare companies within their peer groups using "
    "profitability, cash flow, efficiency and valuation metrics."
)


# =========================================================
# Helper Functions
# =========================================================

def extract_year(value):
    """Extract a four-digit year from financial-year values."""
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
    """Normalise company identifiers."""
    if value is None or pd.isna(value):
        return ""

    return str(value).strip().upper()


def numeric(value):
    """Convert values safely to numeric."""
    if value is None or pd.isna(value):
        return np.nan

    text = (
        str(value)
        .replace(",", "")
        .replace("%", "")
        .replace("₹", "")
        .strip()
    )

    try:
        return float(text)
    except (TypeError, ValueError):
        return np.nan


def repair_header_table(df):
    """Repair tables whose actual headers are stored in row zero."""
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

        if pd.isna(value):
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

    return (
        output
        .dropna(how="all")
        .reset_index(drop=True)
    )


def percentile_score(series, lower_is_better=False):
    """Calculate 0-100 peer percentile scores."""
    values = pd.to_numeric(
        series,
        errors="coerce",
    )

    if values.notna().sum() <= 1:
        return pd.Series(
            50.0,
            index=series.index,
        )

    if lower_is_better:
        ranks = values.rank(
            pct=True,
            ascending=False,
        )
    else:
        ranks = values.rank(
            pct=True,
            ascending=True,
        )

    return (
        ranks * 100
    ).fillna(50.0)


# =========================================================
# Load Tables
# =========================================================

companies = get_companies()
ratios = get_ratios()


try:
    peer_groups = run_query(
        "SELECT * FROM peer_groups"
    )
except Exception:
    peer_groups = pd.DataFrame()


try:
    peer_percentiles = run_query(
        "SELECT * FROM peer_percentiles"
    )
except Exception:
    peer_percentiles = pd.DataFrame()


try:
    market_cap = run_query(
        "SELECT * FROM market_cap"
    )
except Exception:
    market_cap = pd.DataFrame()


if ratios.empty:
    st.error(
        "Financial ratio data could not be loaded."
    )
    st.stop()


if peer_groups.empty and peer_percentiles.empty:
    st.error(
        "Peer-group data could not be loaded."
    )
    st.stop()


# =========================================================
# Clean Peer Group Table
# =========================================================

peer_groups = repair_header_table(
    peer_groups
)


peer_company_col = find_column(
    peer_groups,
    [
        "company_id",
        "id",
        "ticker",
        "symbol",
    ],
)


peer_group_col = find_column(
    peer_groups,
    [
        "peer_group_name",
        "group_name",
        "peer_group",
        "peer_group_id",
        "group",
    ],
)


# Fallback to peer_percentiles if required
if (
    peer_company_col is None
    or peer_group_col is None
):

    peer_fallback = repair_header_table(
        peer_percentiles
    )

    fallback_company_col = find_column(
        peer_fallback,
        [
            "company_id",
            "id",
            "ticker",
        ],
    )

    fallback_group_col = find_column(
        peer_fallback,
        [
            "peer_group_name",
            "group_name",
            "peer_group",
        ],
    )

    if (
        fallback_company_col
        and fallback_group_col
    ):

        peer_groups = (
            peer_fallback[
                [
                    fallback_company_col,
                    fallback_group_col,
                ]
            ]
            .drop_duplicates()
            .copy()
        )

        peer_groups.columns = [
            "company_id",
            "peer_group_name",
        ]

        peer_company_col = "company_id"
        peer_group_col = "peer_group_name"


if (
    peer_company_col is None
    or peer_group_col is None
):

    st.error(
        "The peer-group company/group columns "
        "could not be identified."
    )

    st.write(
        "Peer-group columns:",
        peer_groups.columns.tolist(),
    )

    st.stop()


peer_groups = peer_groups.copy()


peer_groups[peer_company_col] = (
    peer_groups[peer_company_col]
    .apply(clean_id)
)


peer_groups[peer_group_col] = (
    peer_groups[peer_group_col]
    .astype(str)
    .str.strip()
)


peer_groups = peer_groups[
    (
        peer_groups[peer_company_col] != ""
    )
    &
    (
        peer_groups[peer_group_col]
        .str.lower()
        .ne("nan")
    )
].copy()


# =========================================================
# Identify Benchmark Information
# =========================================================

benchmark_company_column = find_column(
    peer_groups,
    [
        "benchmark_company_id",
        "benchmark_company",
        "benchmark_ticker",
        "benchmark_id",
    ],
)


benchmark_flag_column = find_column(
    peer_groups,
    [
        "is_benchmark",
        "benchmark_flag",
    ],
)


# =========================================================
# Prepare Latest Financial Ratios
# =========================================================

ratios = ratios.copy()


ratios["company_id"] = (
    ratios["company_id"]
    .apply(clean_id)
)


ratios["_year_numeric"] = (
    ratios["year"]
    .apply(extract_year)
)


ratios["_complete"] = (
    ratios.notna()
    .sum(axis=1)
)


latest_ratios = (
    ratios[
        ratios["_year_numeric"]
        .notna()
    ]
    .sort_values(
        [
            "company_id",
            "_year_numeric",
            "_complete",
        ],
        ascending=[
            True,
            False,
            False,
        ],
    )
    .drop_duplicates(
        "company_id",
        keep="first",
    )
    .copy()
)


# =========================================================
# Add Company Names
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

        company_names = companies[
            [
                company_id_col,
                company_name_col,
            ]
        ].copy()


        company_names.columns = [
            "company_id",
            "company_name",
        ]


        company_names["company_id"] = (
            company_names[
                "company_id"
            ]
            .apply(clean_id)
        )


        company_names = (
            company_names
            .drop_duplicates(
                "company_id"
            )
        )


        latest_ratios = (
            latest_ratios.merge(
                company_names,
                on="company_id",
                how="left",
            )
        )


if "company_name" not in latest_ratios.columns:
    latest_ratios[
        "company_name"
    ] = latest_ratios[
        "company_id"
    ]


latest_ratios[
    "company_name"
] = latest_ratios[
    "company_name"
].fillna(
    latest_ratios["company_id"]
)


# =========================================================
# Add Latest Valuation Data
# =========================================================

if not market_cap.empty:

    market_cap = market_cap.copy()


    market_cap[
        "company_id"
    ] = (
        market_cap[
            "company_id"
        ].apply(clean_id)
    )


    market_cap["year"] = pd.to_numeric(
        market_cap["year"],
        errors="coerce",
    )


    market_cap = (
        market_cap
        .sort_values(
            [
                "company_id",
                "year",
            ],
            ascending=[
                True,
                False,
            ],
        )
        .drop_duplicates(
            "company_id",
            keep="first",
        )
    )


    valuation_columns = [
        column
        for column in [
            "company_id",
            "pe_ratio",
            "pb_ratio",
            "market_cap_crore",
            "dividend_yield_pct",
        ]
        if column in market_cap.columns
    ]


    valuation_data = (
        market_cap[
            valuation_columns
        ].copy()
    )


    latest_ratios = (
        latest_ratios.merge(
            valuation_data,
            on="company_id",
            how="left",
        )
    )


# =========================================================
# Peer Group Dropdown
# =========================================================

group_names = sorted(
    peer_groups[
        peer_group_col
    ]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)


if not group_names:
    st.error(
        "No peer groups are available."
    )
    st.stop()


selected_group = st.selectbox(
    "Select peer group",
    group_names,
)


# =========================================================
# Companies in Selected Group
# =========================================================

membership = peer_groups[
    peer_groups[
        peer_group_col
    ] == selected_group
].copy()


member_ids = (
    membership[
        peer_company_col
    ]
    .dropna()
    .apply(clean_id)
    .unique()
    .tolist()
)


peer_data = latest_ratios[
    latest_ratios[
        "company_id"
    ].isin(
        member_ids
    )
].copy()


if peer_data.empty:
    st.warning(
        "No financial data is available "
        "for this peer group."
    )
    st.stop()


# =========================================================
# Company Selector
# =========================================================

peer_data[
    "selection_label"
] = (
    peer_data["company_id"]
    + " — "
    + peer_data["company_name"]
)


selected_company_label = st.selectbox(
    "Select company",
    peer_data[
        "selection_label"
    ].sort_values().tolist(),
)


selected_company_id = (
    peer_data.loc[
        peer_data[
            "selection_label"
        ] == selected_company_label,
        "company_id",
    ]
    .iloc[0]
)


# =========================================================
# Determine Benchmark Company
# =========================================================

benchmark_id = None


if benchmark_company_column:

    benchmark_values = (
        membership[
            benchmark_company_column
        ]
        .dropna()
    )


    if not benchmark_values.empty:

        benchmark_id = clean_id(
            benchmark_values.iloc[0]
        )


elif benchmark_flag_column:

    flags = (
        membership[
            benchmark_flag_column
        ]
        .astype(str)
        .str.strip()
        .str.lower()
    )


    benchmark_rows = membership[
        flags.isin(
            [
                "1",
                "true",
                "yes",
                "y",
                "benchmark",
            ]
        )
    ]


    if not benchmark_rows.empty:

        benchmark_id = clean_id(
            benchmark_rows.iloc[0][
                peer_company_col
            ]
        )


# Fallback:
# If no benchmark metadata exists, use the highest
# composite quality score as an inferred benchmark.

benchmark_inferred = False


if (
    not benchmark_id
    or benchmark_id
    not in peer_data[
        "company_id"
    ].values
):

    if (
        "composite_quality_score"
        in peer_data.columns
        and pd.to_numeric(
            peer_data[
                "composite_quality_score"
            ],
            errors="coerce",
        ).notna().any()
    ):

        benchmark_series = (
            pd.to_numeric(
                peer_data[
                    "composite_quality_score"
                ],
                errors="coerce",
            )
        )

        benchmark_index = (
            benchmark_series.idxmax()
        )

        benchmark_id = (
            peer_data.loc[
                benchmark_index,
                "company_id",
            ]
        )

        benchmark_inferred = True

    else:

        benchmark_id = (
            peer_data[
                "company_id"
            ].iloc[0]
        )

        benchmark_inferred = True


# =========================================================
# Basic Peer Information
# =========================================================

info1, info2, info3 = st.columns(3)


info1.metric(
    "Peer Group",
    selected_group,
)


info2.metric(
    "Companies in Group",
    len(peer_data),
)


info3.metric(
    "Benchmark",
    benchmark_id,
)


if benchmark_inferred:

    st.caption(
        "Benchmark metadata was not available in the "
        "peer-group table, so the benchmark is inferred "
        "from the available quality-score data."
    )


# =========================================================
# Radar Metrics
# =========================================================

metric_definitions = {
    "ROE": (
        "return_on_equity_pct",
        False,
    ),

    "Net Margin": (
        "net_profit_margin_pct",
        False,
    ),

    "Operating Margin": (
        "operating_profit_margin_pct",
        False,
    ),

    "Free Cash Flow": (
        "free_cash_flow_cr",
        False,
    ),

    "Interest Coverage": (
        "interest_coverage",
        False,
    ),

    "Asset Turnover": (
        "asset_turnover",
        False,
    ),

    "Debt / Equity": (
        "debt_to_equity",
        True,
    ),

    "P/E": (
        "pe_ratio",
        True,
    ),
}


available_metrics = {}


for label, (
    column,
    lower_is_better,
) in metric_definitions.items():

    if column not in peer_data.columns:
        continue

    peer_data[column] = pd.to_numeric(
        peer_data[column],
        errors="coerce",
    )


    if peer_data[column].notna().any():

        score_column = (
            f"_radar_{column}"
        )


        peer_data[
            score_column
        ] = percentile_score(
            peer_data[column],
            lower_is_better,
        )


        available_metrics[
            label
        ] = (
            column,
            score_column,
        )


# =========================================================
# Radar Chart
# =========================================================

st.divider()

st.subheader(
    "Company vs Peer Group"
)


if len(available_metrics) >= 3:

    selected_row = (
        peer_data[
            peer_data[
                "company_id"
            ] == selected_company_id
        ]
        .iloc[0]
    )


    radar_labels = list(
        available_metrics.keys()
    )


    selected_scores = []

    peer_average_scores = []


    for label in radar_labels:

        _, score_column = (
            available_metrics[label]
        )


        selected_scores.append(
            float(
                selected_row[
                    score_column
                ]
            )
        )


        peer_average_scores.append(
            float(
                peer_data[
                    score_column
                ].mean()
            )
        )


    # Close radar polygon
    radar_labels_closed = (
        radar_labels
        + [radar_labels[0]]
    )


    selected_scores_closed = (
        selected_scores
        + [selected_scores[0]]
    )


    peer_average_closed = (
        peer_average_scores
        + [peer_average_scores[0]]
    )


    radar = go.Figure()


    radar.add_trace(
        go.Scatterpolar(
            r=selected_scores_closed,
            theta=radar_labels_closed,
            fill="toself",
            name=selected_company_id,
        )
    )


    radar.add_trace(
        go.Scatterpolar(
            r=peer_average_closed,
            theta=radar_labels_closed,
            fill="toself",
            name="Peer Group Average",
        )
    )


    radar.update_layout(
        height=600,

        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[
                    0,
                    100,
                ],
            )
        ),

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
        ),

        margin=dict(
            l=50,
            r=50,
            t=80,
            b=40,
        ),
    )


    st.plotly_chart(
        radar,
        width="stretch",
    )


    st.caption(
        "Radar values represent peer-relative percentile scores "
        "from 0 to 100. Lower D/E and P/E values receive higher "
        "peer-quality percentile scores."
    )


else:

    st.info(
        "Not enough financial metrics are available "
        "to create the radar chart."
    )


# =========================================================
# Peer KPI Table
# =========================================================

st.subheader(
    "Peer Group KPI Comparison"
)


table_columns = [
    "company_id",
    "company_name",
    "return_on_equity_pct",
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "debt_to_equity",
    "interest_coverage",
    "asset_turnover",
    "free_cash_flow_cr",
    "pe_ratio",
    "pb_ratio",
    "composite_quality_score",
]


table_columns = [
    column
    for column in table_columns
    if column in peer_data.columns
]


comparison = peer_data[
    table_columns
].copy()


# =========================================================
# Role / Benchmark Highlight
# =========================================================

comparison.insert(
    0,
    "Role",
    "",
)


comparison.loc[
    comparison[
        "company_id"
    ] == benchmark_id,
    "Role",
] = "⭐ Benchmark"


comparison.loc[
    comparison[
        "company_id"
    ] == selected_company_id,
    "Role",
] = "🔹 Selected"


if (
    selected_company_id
    == benchmark_id
):

    comparison.loc[
        comparison[
            "company_id"
        ] == selected_company_id,
        "Role",
    ] = "⭐ Benchmark • Selected"


# =========================================================
# Friendly Column Names
# =========================================================

comparison = comparison.rename(
    columns={
        "company_id": "Ticker",
        "company_name": "Company",
        "return_on_equity_pct": "ROE %",
        "net_profit_margin_pct": "Net Margin %",
        "operating_profit_margin_pct": "OPM %",
        "debt_to_equity": "D/E",
        "interest_coverage": "ICR",
        "asset_turnover": "Asset Turnover",
        "free_cash_flow_cr": "FCF ₹ Cr",
        "pe_ratio": "P/E",
        "pb_ratio": "P/B",
        "composite_quality_score": "Composite Score",
    }
)


# Round numerics
numeric_columns = comparison.select_dtypes(
    include=[
        np.number,
    ]
).columns


comparison[
    numeric_columns
] = comparison[
    numeric_columns
].round(2)


# =========================================================
# Highlight Benchmark
# =========================================================

def highlight_rows(row):
    """Highlight benchmark and selected rows."""

    role = str(
        row.get(
            "Role",
            "",
        )
    )

    if "Benchmark" in role:

        return [
            "font-weight: 700; "
            "background-color: rgba(255, 215, 0, 0.12)"
            for _ in row
        ]

    if "Selected" in role:

        return [
            "font-weight: 700"
            for _ in row
        ]

    return [
        ""
        for _ in row
    ]


styled_comparison = (
    comparison.style
    .apply(
        highlight_rows,
        axis=1,
    )
)


st.dataframe(
    styled_comparison,
    width="stretch",
    hide_index=True,
)


# =========================================================
# Selected Company Snapshot
# =========================================================

st.subheader(
    f"{selected_company_id} Peer Snapshot"
)


selected_data = peer_data[
    peer_data[
        "company_id"
    ] == selected_company_id
].iloc[0]


snapshot1, snapshot2, snapshot3, snapshot4 = (
    st.columns(4)
)


def metric_text(column, suffix=""):

    if column not in selected_data.index:
        return "N/A"

    value = numeric(
        selected_data[column]
    )

    if pd.isna(value):
        return "N/A"

    return (
        f"{value:,.2f}"
        f"{suffix}"
    )


snapshot1.metric(
    "ROE",
    metric_text(
        "return_on_equity_pct",
        "%",
    ),
)


snapshot2.metric(
    "Net Margin",
    metric_text(
        "net_profit_margin_pct",
        "%",
    ),
)


snapshot3.metric(
    "Debt / Equity",
    metric_text(
        "debt_to_equity",
        "x",
    ),
)


snapshot4.metric(
    "P/E",
    metric_text(
        "pe_ratio",
        "x",
    ),
)


st.caption(
    "Market-cap and valuation information shown here comes "
    "from the SIMULATED project dataset."
)