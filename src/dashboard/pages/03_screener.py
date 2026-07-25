import re

import numpy as np
import pandas as pd
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

st.title("🔎 Financial Screener")

st.caption(
    "Filter Nifty 100 companies using profitability, growth, "
    "cash flow, leverage and valuation metrics."
)


# =========================================================
# Helper Functions
# =========================================================

def extract_year(value):
    """Extract a four-digit year from a year-like value."""
    if value is None or pd.isna(value):
        return None

    match = re.search(
        r"(19|20)\d{2}",
        str(value),
    )

    return int(match.group()) if match else None


def numeric(value):
    """Convert values safely to floating-point numbers."""
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


def calculate_cagr(start, end, years):
    """Calculate CAGR for positive start/end values."""
    start = numeric(start)
    end = numeric(end)

    if (
        pd.isna(start)
        or pd.isna(end)
        or start <= 0
        or end <= 0
        or years <= 0
    ):
        return np.nan

    return (
        (end / start) ** (1 / years)
        - 1
    ) * 100


def repair_header_table(df):
    """Repair tables whose real headers appear in the first data row."""
    if df.empty:
        return df

    unnamed = any(
        str(column).lower().startswith("unnamed")
        for column in df.columns
    )

    if not unnamed:
        output = df.copy()

        output.columns = (
            output.columns.astype(str)
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

    columns = []

    for index, value in enumerate(first_row):
        if pd.isna(value):
            columns.append(
                f"column_{index}"
            )
        else:
            name = (
                str(value)
                .strip()
                .lower()
            )

            name = re.sub(
                r"[^\w]+",
                "_",
                name,
            ).strip("_")

            columns.append(
                name or f"column_{index}"
            )

    output = df.iloc[1:].copy()
    output.columns = columns

    return (
        output
        .dropna(how="all")
        .reset_index(drop=True)
    )


# =========================================================
# Load Base Data
# =========================================================

ratios = get_ratios()

companies = get_companies()

try:
    sectors = run_query(
        "SELECT * FROM sectors"
    )
except Exception:
    sectors = pd.DataFrame()

try:
    market_cap = run_query(
        "SELECT * FROM market_cap"
    )
except Exception:
    market_cap = pd.DataFrame()

try:
    pl_raw = run_query(
        "SELECT * FROM profitandloss"
    )
except Exception:
    pl_raw = pd.DataFrame()


if ratios.empty:
    st.error(
        "Financial ratio data could not be loaded."
    )
    st.stop()


# =========================================================
# Prepare Latest Ratio Data
# =========================================================

ratios = ratios.copy()

ratios["_year_numeric"] = (
    ratios["year"]
    .apply(extract_year)
)


ratios = ratios[
    ratios["_year_numeric"].notna()
].copy()


latest_year = int(
    ratios["_year_numeric"].max()
)


latest_ratios = (
    ratios[
        ratios["_year_numeric"]
        == latest_year
    ]
    .copy()
)


# Some companies contain duplicate rows for the same FY.
# Keep the most complete row.

latest_ratios["_non_null_count"] = (
    latest_ratios.notna().sum(axis=1)
)


latest_ratios = (
    latest_ratios
    .sort_values(
        "_non_null_count",
        ascending=False,
    )
    .drop_duplicates(
        "company_id",
        keep="first",
    )
    .drop(
        columns=[
            "_non_null_count",
        ]
    )
)


# =========================================================
# Company Names
# =========================================================

if not companies.empty:

    company_id_column = find_column(
        companies,
        [
            "id",
            "company_id",
            "ticker",
        ],
    )

    company_name_column = find_column(
        companies,
        [
            "company_name",
            "name",
        ],
    )

    if (
        company_id_column
        and company_name_column
    ):

        names = companies[
            [
                company_id_column,
                company_name_column,
            ]
        ].copy()

        names.columns = [
            "company_id",
            "company_name",
        ]

        names["company_id"] = (
            names["company_id"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        names = names.drop_duplicates(
            "company_id"
        )

        latest_ratios = (
            latest_ratios
            .merge(
                names,
                on="company_id",
                how="left",
            )
        )


# =========================================================
# Sector Metadata
# =========================================================

if not sectors.empty:

    sector_columns = [
        column
        for column in [
            "company_id",
            "broad_sector",
            "sub_sector",
            "market_cap_category",
        ]
        if column in sectors.columns
    ]

    sector_info = (
        sectors[sector_columns]
        .drop_duplicates(
            "company_id"
        )
    )

    duplicate_columns = [
        column
        for column in [
            "broad_sector",
            "sub_sector",
        ]
        if column in latest_ratios.columns
        and column in sector_info.columns
    ]

    sector_info = sector_info.drop(
        columns=duplicate_columns,
        errors="ignore",
    )

    latest_ratios = (
        latest_ratios.merge(
            sector_info,
            on="company_id",
            how="left",
        )
    )


# =========================================================
# Latest Valuation
# =========================================================

if not market_cap.empty:

    market_cap = market_cap.copy()

    market_cap["year"] = pd.to_numeric(
        market_cap["year"],
        errors="coerce",
    )

    valuation_latest_year = (
        market_cap["year"].max()
    )

    latest_valuation = (
        market_cap[
            market_cap["year"]
            == valuation_latest_year
        ]
        .copy()
    )

    valuation_columns = [
        column
        for column in [
            "company_id",
            "pe_ratio",
            "pb_ratio",
            "ev_ebitda",
            "dividend_yield_pct",
            "market_cap_crore",
        ]
        if column in latest_valuation.columns
    ]

    latest_valuation = (
        latest_valuation[
            valuation_columns
        ]
        .drop_duplicates(
            "company_id"
        )
    )

    latest_ratios = (
        latest_ratios.merge(
            latest_valuation,
            on="company_id",
            how="left",
        )
    )


# =========================================================
# Calculate Revenue/PAT CAGR
# =========================================================

pl = repair_header_table(
    pl_raw
)


growth_records = []


if not pl.empty:

    pl_company = find_column(
        pl,
        [
            "company_id",
            "id",
        ],
    )

    pl_year = find_column(
        pl,
        ["year"],
    )

    sales_column = find_column(
        pl,
        [
            "sales",
            "revenue",
        ],
    )

    profit_column = find_column(
        pl,
        [
            "net_profit",
            "profit_after_tax",
            "pat",
        ],
    )


    if (
        pl_company
        and pl_year
    ):

        pl["_year_numeric"] = (
            pl[pl_year]
            .apply(extract_year)
        )

        if sales_column:
            pl[sales_column] = pd.to_numeric(
                pl[sales_column],
                errors="coerce",
            )

        if profit_column:
            pl[profit_column] = pd.to_numeric(
                pl[profit_column],
                errors="coerce",
            )


        for company_id, group in pl.groupby(
            pl_company
        ):

            group = (
                group[
                    group["_year_numeric"]
                    .notna()
                ]
                .sort_values(
                    "_year_numeric"
                )
                .drop_duplicates(
                    "_year_numeric",
                    keep="last",
                )
            )

            if group.empty:
                continue

            end = group.iloc[-1]

            end_year = int(
                end["_year_numeric"]
            )

            target_year = (
                end_year - 5
            )

            starts = group[
                group["_year_numeric"]
                <= target_year
            ]

            revenue_cagr = np.nan
            pat_cagr = np.nan


            if not starts.empty:

                start = starts.iloc[-1]

                years = int(
                    end["_year_numeric"]
                    - start["_year_numeric"]
                )

                if sales_column:
                    revenue_cagr = calculate_cagr(
                        start[sales_column],
                        end[sales_column],
                        years,
                    )

                if profit_column:
                    pat_cagr = calculate_cagr(
                        start[profit_column],
                        end[profit_column],
                        years,
                    )


            growth_records.append(
                {
                    "company_id": (
                        str(company_id)
                        .strip()
                        .upper()
                    ),
                    "revenue_cagr_5yr": (
                        revenue_cagr
                    ),
                    "pat_cagr_5yr": (
                        pat_cagr
                    ),
                }
            )


if growth_records:

    growth = pd.DataFrame(
        growth_records
    )

    latest_ratios = (
        latest_ratios.merge(
            growth,
            on="company_id",
            how="left",
        )
    )

else:

    latest_ratios[
        "revenue_cagr_5yr"
    ] = np.nan

    latest_ratios[
        "pat_cagr_5yr"
    ] = np.nan


# =========================================================
# Normalise Required Metrics
# =========================================================

column_defaults = {
    "return_on_equity_pct": np.nan,
    "debt_to_equity": np.nan,
    "free_cash_flow_cr": np.nan,
    "revenue_cagr_5yr": np.nan,
    "pat_cagr_5yr": np.nan,
    "operating_profit_margin_pct": np.nan,
    "pe_ratio": np.nan,
    "pb_ratio": np.nan,
    "dividend_yield_pct": np.nan,
    "interest_coverage": np.nan,
    "composite_quality_score": np.nan,
}


for column, default in column_defaults.items():

    if column not in latest_ratios.columns:
        latest_ratios[column] = default

    latest_ratios[column] = pd.to_numeric(
        latest_ratios[column],
        errors="coerce",
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


if "broad_sector" not in latest_ratios.columns:
    latest_ratios[
        "broad_sector"
    ] = "Unknown"


latest_ratios[
    "broad_sector"
] = latest_ratios[
    "broad_sector"
].fillna(
    "Unknown"
)


# =========================================================
# Presets
# =========================================================

PRESETS = {
    "Quality": {
        "roe": 15.0,
        "de": 1.0,
        "fcf": 0.0,
        "rev": 8.0,
        "pat": 8.0,
        "opm": 15.0,
        "pe": 100.0,
        "pb": 20.0,
        "dividend": 0.0,
        "icr": 3.0,
    },

    "Value": {
        "roe": 10.0,
        "de": 1.5,
        "fcf": 0.0,
        "rev": 0.0,
        "pat": 0.0,
        "opm": 8.0,
        "pe": 25.0,
        "pb": 4.0,
        "dividend": 0.0,
        "icr": 2.0,
    },

    "Growth": {
        "roe": 12.0,
        "de": 2.0,
        "fcf": -5000.0,
        "rev": 15.0,
        "pat": 15.0,
        "opm": 10.0,
        "pe": 150.0,
        "pb": 30.0,
        "dividend": 0.0,
        "icr": 1.5,
    },

    "Dividend": {
        "roe": 8.0,
        "de": 1.5,
        "fcf": 0.0,
        "rev": 0.0,
        "pat": 0.0,
        "opm": 5.0,
        "pe": 100.0,
        "pb": 20.0,
        "dividend": 2.0,
        "icr": 2.0,
    },

    "Debt-Free": {
        "roe": 0.0,
        "de": 0.0,
        "fcf": -10000.0,
        "rev": -100.0,
        "pat": -100.0,
        "opm": -100.0,
        "pe": 500.0,
        "pb": 100.0,
        "dividend": 0.0,
        "icr": 0.0,
    },

    "Turnaround": {
        "roe": 0.0,
        "de": 3.0,
        "fcf": -10000.0,
        "rev": 0.0,
        "pat": 10.0,
        "opm": 0.0,
        "pe": 500.0,
        "pb": 100.0,
        "dividend": 0.0,
        "icr": 1.0,
    },
}


DEFAULTS = {
    "roe": 0.0,
    "de": 10.0,
    "fcf": -10000.0,
    "rev": -100.0,
    "pat": -100.0,
    "opm": -100.0,
    "pe": 500.0,
    "pb": 100.0,
    "dividend": 0.0,
    "icr": 0.0,
}


for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# Preset Buttons
# =========================================================

st.subheader(
    "Screener Presets"
)


preset_columns = st.columns(6)


for column, preset_name in zip(
    preset_columns,
    PRESETS.keys(),
):

    if column.button(
        preset_name,
        use_container_width=True,
    ):

        preset = PRESETS[
            preset_name
        ]

        for key, value in preset.items():
            st.session_state[key] = value

        st.rerun()


# =========================================================
# Sidebar Filters
# =========================================================

st.sidebar.header(
    "Screener Filters"
)


roe_min = st.sidebar.slider(
    "ROE minimum (%)",
    min_value=-100.0,
    max_value=200.0,
    value=float(
        st.session_state["roe"]
    ),
    step=1.0,
    key="roe",
)


de_max = st.sidebar.slider(
    "D/E maximum",
    min_value=0.0,
    max_value=10.0,
    value=float(
        st.session_state["de"]
    ),
    step=0.1,
    key="de",
)


fcf_min = st.sidebar.number_input(
    "FCF minimum (₹ Cr)",
    value=float(
        st.session_state["fcf"]
    ),
    step=100.0,
    key="fcf",
)


revenue_cagr_min = st.sidebar.slider(
    "Revenue CAGR 5Y minimum (%)",
    min_value=-100.0,
    max_value=100.0,
    value=float(
        st.session_state["rev"]
    ),
    step=1.0,
    key="rev",
)


pat_cagr_min = st.sidebar.slider(
    "PAT CAGR 5Y minimum (%)",
    min_value=-100.0,
    max_value=100.0,
    value=float(
        st.session_state["pat"]
    ),
    step=1.0,
    key="pat",
)


opm_min = st.sidebar.slider(
    "OPM minimum (%)",
    min_value=-100.0,
    max_value=100.0,
    value=float(
        st.session_state["opm"]
    ),
    step=1.0,
    key="opm",
)


pe_max = st.sidebar.slider(
    "P/E maximum",
    min_value=0.0,
    max_value=500.0,
    value=float(
        st.session_state["pe"]
    ),
    step=5.0,
    key="pe",
)


pb_max = st.sidebar.slider(
    "P/B maximum",
    min_value=0.0,
    max_value=100.0,
    value=float(
        st.session_state["pb"]
    ),
    step=1.0,
    key="pb",
)


dividend_min = st.sidebar.slider(
    "Dividend Yield minimum (%)",
    min_value=0.0,
    max_value=20.0,
    value=float(
        st.session_state["dividend"]
    ),
    step=0.1,
    key="dividend",
)


icr_min = st.sidebar.slider(
    "Interest Coverage minimum",
    min_value=0.0,
    max_value=100.0,
    value=float(
        st.session_state["icr"]
    ),
    step=0.5,
    key="icr",
)


# =========================================================
# Sector Filter
# =========================================================

sector_options = (
    latest_ratios[
        "broad_sector"
    ]
    .dropna()
    .astype(str)
    .sort_values()
    .unique()
    .tolist()
)


selected_sectors = st.sidebar.multiselect(
    "Sector",
    options=sector_options,
)


# =========================================================
# Apply Filters
# =========================================================

results = latest_ratios.copy()


if selected_sectors:

    results = results[
        results[
            "broad_sector"
        ].isin(
            selected_sectors
        )
    ]


# ROE
results = results[
    (
        results[
            "return_on_equity_pct"
        ].isna()
    )
    |
    (
        results[
            "return_on_equity_pct"
        ] >= roe_min
    )
]


# D/E
#
# IMPORTANT PROJECT RULE:
# Skip Financials when applying D/E filter.

financial_mask = (
    results[
        "broad_sector"
    ]
    .astype(str)
    .str.lower()
    .eq("financials")
)


debt_mask = (
    results[
        "debt_to_equity"
    ].isna()
    |
    (
        results[
            "debt_to_equity"
        ] <= de_max
    )
)


results = results[
    financial_mask
    | debt_mask
]


# FCF
results = results[
    results[
        "free_cash_flow_cr"
    ].isna()
    |
    (
        results[
            "free_cash_flow_cr"
        ] >= fcf_min
    )
]


# Revenue CAGR
results = results[
    results[
        "revenue_cagr_5yr"
    ].isna()
    |
    (
        results[
            "revenue_cagr_5yr"
        ] >= revenue_cagr_min
    )
]


# PAT CAGR
results = results[
    results[
        "pat_cagr_5yr"
    ].isna()
    |
    (
        results[
            "pat_cagr_5yr"
        ] >= pat_cagr_min
    )
]


# OPM
results = results[
    results[
        "operating_profit_margin_pct"
    ].isna()
    |
    (
        results[
            "operating_profit_margin_pct"
        ] >= opm_min
    )
]


# P/E
results = results[
    results[
        "pe_ratio"
    ].isna()
    |
    (
        results[
            "pe_ratio"
        ] <= pe_max
    )
]


# P/B
results = results[
    results[
        "pb_ratio"
    ].isna()
    |
    (
        results[
            "pb_ratio"
        ] <= pb_max
    )
]


# Dividend Yield
results = results[
    results[
        "dividend_yield_pct"
    ].isna()
    |
    (
        results[
            "dividend_yield_pct"
        ] >= dividend_min
    )
]


# Interest Coverage
results = results[
    results[
        "interest_coverage"
    ].isna()
    |
    (
        results[
            "interest_coverage"
        ] >= icr_min
    )
]


# =========================================================
# Sort Results
# =========================================================

results = results.sort_values(
    [
        "composite_quality_score",
        "return_on_equity_pct",
    ],
    ascending=[
        False,
        False,
    ],
)


# =========================================================
# Results
# =========================================================

st.divider()


count = len(results)


if count == 1:
    st.subheader(
        "1 company matches your filters"
    )
else:
    st.subheader(
        f"{count} companies match your filters"
    )


# =========================================================
# Display Table
# =========================================================

display_columns = [
    "company_id",
    "company_name",
    "broad_sector",
    "composite_quality_score",
    "return_on_equity_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "operating_profit_margin_pct",
    "pe_ratio",
    "pb_ratio",
    "dividend_yield_pct",
    "interest_coverage",
]


display_columns = [
    column
    for column in display_columns
    if column in results.columns
]


display = results[
    display_columns
].copy()


display = display.rename(
    columns={
        "company_id": "Ticker",
        "company_name": "Company",
        "broad_sector": "Sector",
        "composite_quality_score": "Composite Score",
        "return_on_equity_pct": "ROE %",
        "debt_to_equity": "D/E",
        "free_cash_flow_cr": "FCF ₹ Cr",
        "revenue_cagr_5yr": "Revenue CAGR 5Y %",
        "pat_cagr_5yr": "PAT CAGR 5Y %",
        "operating_profit_margin_pct": "OPM %",
        "pe_ratio": "P/E",
        "pb_ratio": "P/B",
        "dividend_yield_pct": "Dividend Yield %",
        "interest_coverage": "ICR",
    }
)


numeric_columns = display.select_dtypes(
    include=[
        np.number,
    ]
).columns


display[
    numeric_columns
] = display[
    numeric_columns
].round(2)


st.dataframe(
    display,
    use_container_width=True,
    hide_index=True,
)


# =========================================================
# CSV Export
# =========================================================

csv_data = display.to_csv(
    index=False
).encode(
    "utf-8"
)


st.download_button(
    label="⬇️ Download Screener Results as CSV",
    data=csv_data,
    file_name=(
        f"nifty100_screener_{latest_year}.csv"
    ),
    mime="text/csv",
)


st.caption(
    "D/E filtering is intentionally skipped for Financials "
    "according to the project requirements."
)


st.caption(
    "Market-cap and valuation data are SIMULATED according "
    "to the supplied project dataset."
)