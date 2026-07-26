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

st.title("🏭 Sector Analysis")

st.caption(
    "Compare companies within each Nifty 100 sector using "
    "revenue, profitability and market-cap metrics."
)


# =========================================================
# Helpers
# =========================================================

def find_column(df, candidates):
    """Return the first matching column."""
    for candidate in candidates:
        if candidate in df.columns:
            return candidate

    return None


def clean_id(value):
    """Normalize company identifiers."""
    if value is None or pd.isna(value):
        return ""

    return str(value).strip().upper()


def extract_year(value):
    """Extract 4-digit year from values such as Mar 2024."""
    if value is None or pd.isna(value):
        return None

    match = re.search(
        r"(19|20)\d{2}",
        str(value),
    )

    return int(match.group()) if match else None


def repair_header_table(df):
    """
    Repair tables where the actual headers are stored
    in the first data row.
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

    return (
        output
        .dropna(how="all")
        .reset_index(drop=True)
    )


# =========================================================
# Load Data
# =========================================================

try:

    companies = get_companies()

    sectors = run_query(
        "SELECT * FROM sectors"
    )

    ratios = run_query(
        "SELECT * FROM financial_ratios"
    )

    market_cap = run_query(
        "SELECT * FROM market_cap"
    )

    pnl_raw = run_query(
        "SELECT * FROM profitandloss"
    )

except Exception as exc:

    st.error(
        "Unable to load sector-analysis data."
    )

    st.exception(exc)
    st.stop()


if sectors.empty:
    st.error(
        "Sector data is unavailable."
    )
    st.stop()


# =========================================================
# Official 92-company Universe
# =========================================================

official_ids = set()


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

        official_ids = set(
            companies[
                master_id_col
            ]
            .dropna()
            .apply(clean_id)
            .tolist()
        )


# =========================================================
# Prepare Company Names
# =========================================================

company_lookup = pd.DataFrame()


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


# =========================================================
# Prepare Sector Metadata
# =========================================================

sectors = sectors.copy()

sectors[
    "company_id"
] = (
    sectors[
        "company_id"
    ]
    .apply(clean_id)
)


if official_ids:

    sectors = sectors[
        sectors[
            "company_id"
        ].isin(
            official_ids
        )
    ].copy()


sector_columns = [
    column
    for column in [
        "company_id",
        "broad_sector",
        "sub_sector",
        "index_weight_pct",
        "market_cap_category",
    ]
    if column in sectors.columns
]


sector_data = (
    sectors[
        sector_columns
    ]
    .drop_duplicates(
        "company_id"
    )
    .copy()
)


if not company_lookup.empty:

    sector_data = (
        sector_data
        .merge(
            company_lookup,
            on="company_id",
            how="left",
        )
    )


if "company_name" not in sector_data.columns:

    sector_data[
        "company_name"
    ] = sector_data[
        "company_id"
    ]


# =========================================================
# Latest Financial Ratios
# =========================================================

ratios = ratios.copy()

ratios[
    "company_id"
] = (
    ratios[
        "company_id"
    ]
    .apply(clean_id)
)


ratios[
    "_year_numeric"
] = (
    ratios[
        "year"
    ]
    .apply(extract_year)
)


ratios = ratios[
    ratios[
        "_year_numeric"
    ].notna()
].copy()


if official_ids:

    ratios = ratios[
        ratios[
            "company_id"
        ].isin(
            official_ids
        )
    ]


ratios[
    "_complete"
] = (
    ratios.notna()
    .sum(axis=1)
)


latest_ratios = (
    ratios
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
)


ratio_columns = [
    column
    for column in [
        "company_id",
        "return_on_equity_pct",
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "free_cash_flow_cr",
        "composite_quality_score",
    ]
    if column in latest_ratios.columns
]


latest_ratios = latest_ratios[
    ratio_columns
].copy()


sector_data = (
    sector_data
    .merge(
        latest_ratios,
        on="company_id",
        how="left",
    )
)


# =========================================================
# Prepare Latest Market Cap
# =========================================================

if not market_cap.empty:

    market_cap = market_cap.copy()

    market_cap[
        "company_id"
    ] = (
        market_cap[
            "company_id"
        ]
        .apply(clean_id)
    )


    market_cap[
        "year"
    ] = pd.to_numeric(
        market_cap[
            "year"
        ],
        errors="coerce",
    )


    if official_ids:

        market_cap = market_cap[
            market_cap[
                "company_id"
            ].isin(
                official_ids
            )
        ]


    latest_market_cap = (
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


    mc_columns = [
        column
        for column in [
            "company_id",
            "market_cap_crore",
            "pe_ratio",
            "pb_ratio",
            "dividend_yield_pct",
        ]
        if column in latest_market_cap.columns
    ]


    latest_market_cap = (
        latest_market_cap[
            mc_columns
        ]
    )


    sector_data = (
        sector_data
        .merge(
            latest_market_cap,
            on="company_id",
            how="left",
        )
    )


# =========================================================
# Prepare Latest Revenue
# =========================================================

pnl = repair_header_table(
    pnl_raw
)


if not pnl.empty:

    pnl_company_col = find_column(
        pnl,
        [
            "company_id",
            "ticker",
            "id",
        ],
    )

    pnl_year_col = find_column(
        pnl,
        [
            "year",
            "financial_year",
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


    if (
        pnl_company_col
        and pnl_year_col
        and sales_col
    ):

        pnl[
            pnl_company_col
        ] = (
            pnl[
                pnl_company_col
            ]
            .apply(clean_id)
        )


        pnl[
            "_year_numeric"
        ] = (
            pnl[
                pnl_year_col
            ]
            .apply(extract_year)
        )


        pnl[
            sales_col
        ] = pd.to_numeric(
            pnl[
                sales_col
            ],
            errors="coerce",
        )


        if official_ids:

            pnl = pnl[
                pnl[
                    pnl_company_col
                ].isin(
                    official_ids
                )
            ]


        latest_revenue = (
            pnl[
                pnl[
                    "_year_numeric"
                ].notna()
            ]
            .sort_values(
                [
                    pnl_company_col,
                    "_year_numeric",
                ],
                ascending=[
                    True,
                    False,
                ],
            )
            .drop_duplicates(
                pnl_company_col,
                keep="first",
            )
            [
                [
                    pnl_company_col,
                    sales_col,
                ]
            ]
            .copy()
        )


        latest_revenue.columns = [
            "company_id",
            "revenue",
        ]


        sector_data = (
            sector_data
            .merge(
                latest_revenue,
                on="company_id",
                how="left",
            )
        )


# =========================================================
# Ensure Required Columns
# =========================================================

defaults = {
    "revenue": np.nan,
    "return_on_equity_pct": np.nan,
    "market_cap_crore": np.nan,
    "net_profit_margin_pct": np.nan,
    "operating_profit_margin_pct": np.nan,
    "debt_to_equity": np.nan,
    "free_cash_flow_cr": np.nan,
    "pe_ratio": np.nan,
}


for column, default in defaults.items():

    if column not in sector_data.columns:
        sector_data[column] = default

    sector_data[
        column
    ] = pd.to_numeric(
        sector_data[
            column
        ],
        errors="coerce",
    )


if "sub_sector" not in sector_data.columns:

    sector_data[
        "sub_sector"
    ] = "Unknown"


sector_data[
    "sub_sector"
] = (
    sector_data[
        "sub_sector"
    ]
    .fillna(
        "Unknown"
    )
)


# =========================================================
# Sector Dropdown
# =========================================================

sector_options = sorted(
    sector_data[
        "broad_sector"
    ]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)


if not sector_options:

    st.error(
        "No sector values were found."
    )

    st.stop()


selected_sector = st.selectbox(
    "Select sector",
    sector_options,
)


filtered = sector_data[
    sector_data[
        "broad_sector"
    ] == selected_sector
].copy()


# =========================================================
# Sector Summary KPIs
# =========================================================

st.divider()

st.subheader(
    f"📊 {selected_sector} Overview"
)


k1, k2, k3, k4 = st.columns(4)


k1.metric(
    "Companies",
    filtered[
        "company_id"
    ].nunique(),
)


median_revenue = (
    filtered[
        "revenue"
    ].median()
)


k2.metric(
    "Median Revenue",
    (
        f"₹{median_revenue:,.0f} Cr"
        if pd.notna(
            median_revenue
        )
        else "N/A"
    ),
)


median_roe = (
    filtered[
        "return_on_equity_pct"
    ].median()
)


k3.metric(
    "Median ROE",
    (
        f"{median_roe:,.2f}%"
        if pd.notna(
            median_roe
        )
        else "N/A"
    ),
)


median_market_cap = (
    filtered[
        "market_cap_crore"
    ].median()
)


k4.metric(
    "Median Market Cap",
    (
        f"₹{median_market_cap:,.0f} Cr"
        if pd.notna(
            median_market_cap
        )
        else "N/A"
    ),
)


# =========================================================
# Bubble Chart
# =========================================================

st.divider()

st.subheader(
    "🫧 Revenue vs ROE Bubble Map"
)


bubble = filtered[
    [
        "company_id",
        "company_name",
        "sub_sector",
        "revenue",
        "return_on_equity_pct",
        "market_cap_crore",
    ]
].copy()


bubble = bubble.dropna(
    subset=[
        "revenue",
        "return_on_equity_pct",
    ]
)


# Plotly requires positive bubble sizes.
bubble[
    "bubble_size"
] = (
    bubble[
        "market_cap_crore"
    ]
    .fillna(1)
    .clip(lower=1)
)


if bubble.empty:

    st.info(
        "Insufficient data is available "
        "for this sector's bubble chart."
    )

else:

    fig = px.scatter(
        bubble,
        x="revenue",
        y="return_on_equity_pct",
        size="bubble_size",
        color="sub_sector",
        hover_name="company_name",
        hover_data={
            "company_id": True,
            "revenue": ":,.0f",
            "return_on_equity_pct": ":.2f",
            "market_cap_crore": ":,.0f",
            "bubble_size": False,
        },
        labels={
            "revenue":
                "Revenue (₹ Cr)",

            "return_on_equity_pct":
                "ROE (%)",

            "sub_sector":
                "Sub-sector",
        },

        size_max=70,
    )


    fig.update_layout(
        height=620,

        margin=dict(
            l=20,
            r=20,
            t=30,
            b=20,
        ),
    )


    st.plotly_chart(
        fig,
        use_container_width=True,
    )


    st.caption(
        "Bubble size represents market capitalization. "
        "Market-cap data is SIMULATED according to "
        "the supplied project dataset."
    )


# =========================================================
# Sector Median KPI Chart
# =========================================================

st.divider()

st.subheader(
    "📈 Sector Median KPIs"
)


median_metrics = {
    "ROE (%)":
        filtered[
            "return_on_equity_pct"
        ].median(),

    "Net Margin (%)":
        filtered[
            "net_profit_margin_pct"
        ].median(),

    "Operating Margin (%)":
        filtered[
            "operating_profit_margin_pct"
        ].median(),

    "Debt / Equity":
        filtered[
            "debt_to_equity"
        ].median(),

    "P/E":
        filtered[
            "pe_ratio"
        ].median(),
}


median_df = pd.DataFrame(
    {
        "Metric":
            list(
                median_metrics.keys()
            ),

        "Median Value":
            list(
                median_metrics.values()
            ),
    }
)


median_df[
    "Median Value"
] = pd.to_numeric(
    median_df[
        "Median Value"
    ],
    errors="coerce",
)


median_df = median_df.dropna(
    subset=[
        "Median Value",
    ]
)


if median_df.empty:

    st.info(
        "Median KPI data is unavailable "
        "for this sector."
    )

else:

    median_chart = px.bar(
        median_df,
        x="Metric",
        y="Median Value",
        text_auto=".2f",
    )


    median_chart.update_layout(
        height=480,

        xaxis_title="Metric",

        yaxis_title=(
            "Sector Median"
        ),
    )


    st.plotly_chart(
        median_chart,
        use_container_width=True,
    )


# =========================================================
# Company Table
# =========================================================

st.divider()

st.subheader(
    f"🏢 Companies in {selected_sector}"
)


company_table = filtered[
    [
        "company_id",
        "company_name",
        "sub_sector",
        "revenue",
        "return_on_equity_pct",
        "market_cap_crore",
        "net_profit_margin_pct",
        "debt_to_equity",
        "pe_ratio",
    ]
].copy()


company_table = company_table.rename(
    columns={
        "company_id":
            "Ticker",

        "company_name":
            "Company",

        "sub_sector":
            "Sub-sector",

        "revenue":
            "Revenue ₹ Cr",

        "return_on_equity_pct":
            "ROE %",

        "market_cap_crore":
            "Market Cap ₹ Cr",

        "net_profit_margin_pct":
            "Net Margin %",

        "debt_to_equity":
            "D/E",

        "pe_ratio":
            "P/E",
    }
)


numeric_columns = (
    company_table
    .select_dtypes(
        include=[
            np.number,
        ]
    )
    .columns
)


company_table[
    numeric_columns
] = (
    company_table[
        numeric_columns
    ]
    .round(2)
)


company_table = (
    company_table
    .sort_values(
        "Market Cap ₹ Cr",
        ascending=False,
    )
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
    "⬇️ Download Sector Data as CSV",
    data=csv_data,
    file_name=(
        f"{selected_sector.lower().replace(' ', '_')}"
        "_sector_analysis.csv"
    ),
    mime="text/csv",
)


st.caption(
    "Sector classification comes from the supplied "
    "Nifty 100 project dataset."
)