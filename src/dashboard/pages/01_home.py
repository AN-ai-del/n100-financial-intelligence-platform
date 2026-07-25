import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import (
    get_all_pl,
    get_companies,
    get_market_cap,
    get_ratios,
    get_sectors,
)


st.title("🏠 Nifty 100 Analytics")

st.caption(
    "Portfolio-level financial intelligence across "
    "the Nifty 100 universe."
)


# =========================================================
# Load Data
# =========================================================

companies = get_companies()
ratios = get_ratios()
sectors = get_sectors()
market_cap = get_market_cap()
pl = get_all_pl()


if ratios.empty:

    st.error(
        "Financial ratio data could not be loaded."
    )

    st.stop()


# =========================================================
# Year Selector
# =========================================================

available_years = sorted(
    ratios[
        "year_numeric"
    ]
    .dropna()
    .astype(int)
    .unique()
    .tolist()
)


dashboard_years = [
    year
    for year in range(
        2019,
        2025,
    )
    if year in available_years
]


if not dashboard_years:

    dashboard_years = (
        available_years
    )


selected_year = st.sidebar.selectbox(
    "Financial Year",
    dashboard_years,
    index=len(
        dashboard_years
    ) - 1,
)


current = ratios[
    ratios["year_numeric"]
    == selected_year
].copy()


# Remove accidental duplicate company/year rows.
current = (
    current
    .sort_values("id")
    .drop_duplicates(
        "company_id",
        keep="last",
    )
)


# =========================================================
# Merge Sectors
# =========================================================

if not sectors.empty:

    sector_metadata = (
        sectors[
            [
                "company_id",
                "broad_sector",
                "sub_sector",
            ]
        ]
        .drop_duplicates(
            "company_id"
        )
    )

    current = current.drop(
        columns=[
            "broad_sector",
            "sub_sector",
        ],
        errors="ignore",
    )

    current = current.merge(
        sector_metadata,
        on="company_id",
        how="left",
    )


# =========================================================
# Merge Company Names
# =========================================================

if not companies.empty:

    company_metadata = companies[
        [
            "id",
            "company_name",
        ]
    ].copy()

    company_metadata = (
        company_metadata
        .rename(
            columns={
                "id": "company_id"
            }
        )
    )

    company_metadata[
        "company_id"
    ] = (
        company_metadata[
            "company_id"
        ]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    current = current.merge(
        company_metadata,
        on="company_id",
        how="left",
    )


# =========================================================
# Valuation Data
# =========================================================

valuation_year = min(
    selected_year,
    2024,
)


year_valuation = market_cap[
    pd.to_numeric(
        market_cap["year"],
        errors="coerce",
    )
    == valuation_year
].copy()


year_valuation = (
    year_valuation
    .drop_duplicates(
        "company_id",
        keep="last",
    )
)


current = current.merge(
    year_valuation[
        [
            "company_id",
            "pe_ratio",
        ]
    ],
    on="company_id",
    how="left",
)


# =========================================================
# Revenue CAGR Function
# =========================================================

def calculate_revenue_cagr(
    company_id,
    selected_year,
):
    """Calculate approximately 5-year sales CAGR."""

    company_pl = pl[
        pl["company_id"]
        == company_id
    ].copy()

    if company_pl.empty:
        return np.nan

    if (
        "sales"
        not in company_pl.columns
    ):
        return np.nan

    company_pl["sales"] = (
        pd.to_numeric(
            company_pl["sales"],
            errors="coerce",
        )
    )

    company_pl = company_pl[
        company_pl[
            "year_numeric"
        ].notna()
    ]

    company_pl = company_pl[
        company_pl[
            "year_numeric"
        ]
        <= selected_year
    ]

    company_pl = (
        company_pl
        .sort_values(
            "year_numeric"
        )
        .drop_duplicates(
            "year_numeric",
            keep="last",
        )
    )

    if len(company_pl) < 2:
        return np.nan

    end_row = company_pl.iloc[-1]

    target_start_year = (
        int(
            end_row[
                "year_numeric"
            ]
        )
        - 5
    )

    candidates = company_pl[
        company_pl[
            "year_numeric"
        ]
        <= target_start_year
    ]

    if candidates.empty:
        start_row = (
            company_pl.iloc[0]
        )
    else:
        start_row = (
            candidates.iloc[-1]
        )

    start_sales = (
        start_row["sales"]
    )

    end_sales = (
        end_row["sales"]
    )

    start_year = int(
        start_row[
            "year_numeric"
        ]
    )

    end_year = int(
        end_row[
            "year_numeric"
        ]
    )

    years = (
        end_year
        - start_year
    )

    if (
        pd.isna(start_sales)
        or pd.isna(end_sales)
        or start_sales <= 0
        or end_sales <= 0
        or years <= 0
    ):
        return np.nan

    return (
        (
            end_sales
            / start_sales
        )
        ** (
            1
            / years
        )
        - 1
    ) * 100


current[
    "revenue_cagr_5yr"
] = current[
    "company_id"
].apply(
    lambda ticker:
    calculate_revenue_cagr(
        ticker,
        selected_year,
    )
)


# =========================================================
# KPI Values
# =========================================================

roe = pd.to_numeric(
    current[
        "return_on_equity_pct"
    ],
    errors="coerce",
)


pe = pd.to_numeric(
    current[
        "pe_ratio"
    ],
    errors="coerce",
)


de = pd.to_numeric(
    current[
        "debt_to_equity"
    ],
    errors="coerce",
)


revenue_cagr = pd.to_numeric(
    current[
        "revenue_cagr_5yr"
    ],
    errors="coerce",
)


average_roe = roe.mean()

median_pe = pe.median()

median_de = de.median()

median_rev_cagr = (
    revenue_cagr.median()
)


total_companies = (
    current[
        "company_id"
    ].nunique()
)


debt_free_companies = int(
    (
        de.fillna(
            float("inf")
        )
        == 0
    ).sum()
)


def fmt(
    value,
    suffix="",
):
    if pd.isna(value):
        return "N/A"

    return (
        f"{value:,.1f}"
        f"{suffix}"
    )


# =========================================================
# KPI Tiles
# =========================================================

row1 = st.columns(3)


row1[0].metric(
    "Average ROE",
    fmt(
        average_roe,
        "%",
    ),
)


row1[1].metric(
    "Median P/E",
    fmt(
        median_pe,
        "x",
    ),
)


row1[2].metric(
    "Median D/E",
    fmt(
        median_de,
        "x",
    ),
)


row2 = st.columns(3)


row2[0].metric(
    "Total Companies",
    total_companies,
)


row2[1].metric(
    "Median Revenue CAGR (5Y)",
    fmt(
        median_rev_cagr,
        "%",
    ),
)


row2[2].metric(
    "Debt-Free Companies",
    debt_free_companies,
)


st.divider()


# =========================================================
# Sector Donut
# =========================================================

st.subheader(
    "Sector Distribution"
)


if (
    "broad_sector"
    in current.columns
):

    sector_distribution = (
        current
        .dropna(
            subset=[
                "broad_sector"
            ]
        )
        .groupby(
            "broad_sector"
        )["company_id"]
        .nunique()
        .reset_index(
            name="Companies"
        )
    )


    fig = px.pie(
        sector_distribution,
        names="broad_sector",
        values="Companies",
        hole=0.55,
    )


    fig.update_layout(
        height=500,
    )


    st.plotly_chart(
        fig,
        use_container_width=True,
    )

else:

    st.info(
        "Sector information unavailable."
    )


# =========================================================
# Top Five
# =========================================================

st.subheader(
    "Top 5 Companies by Composite Quality Score"
)


score_data = current.copy()


score_data[
    "composite_quality_score"
] = pd.to_numeric(
    score_data[
        "composite_quality_score"
    ],
    errors="coerce",
)


top5 = (
    score_data
    .sort_values(
        "composite_quality_score",
        ascending=False,
    )
    .head(5)
)


display_columns = [
    "company_id",
    "company_name",
    "broad_sector",
    "composite_quality_score",
]


display_columns = [
    column
    for column
    in display_columns
    if column
    in top5.columns
]


top5 = top5[
    display_columns
].rename(
    columns={
        "company_id":
            "Ticker",

        "company_name":
            "Company",

        "broad_sector":
            "Sector",

        "composite_quality_score":
            "Composite Quality Score",
    }
)


st.dataframe(
    top5,
    use_container_width=True,
    hide_index=True,
)


st.caption(
    "Market-cap and valuation data are "
    "SIMULATED according to the project dataset."
)