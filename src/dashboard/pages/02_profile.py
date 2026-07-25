import re

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import (
    find_column,
    get_companies,
    get_ratios,
    run_query,
    safe_value,
)


# =========================================================
# Page Header
# =========================================================

st.title("🏢 Company Profile")

st.caption(
    "Search a company to explore financial performance, "
    "profitability and business quality."
)


# =========================================================
# General Helpers
# =========================================================

def extract_year(value):
    """Extract a four-digit year from a financial-year value."""
    if value is None or pd.isna(value):
        return None

    match = re.search(r"(19|20)\d{2}", str(value))

    if not match:
        return None

    return int(match.group())


def to_numeric_value(value):
    """Convert a value to float while handling malformed strings."""
    if value is None or pd.isna(value):
        return None

    text = str(value).strip()

    if not text or text.lower() in {"nan", "none", "na", "n/a", "-"}:
        return None

    text = (
        text.replace(",", "")
        .replace("₹", "")
        .replace("%", "")
        .strip()
    )

    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def display_metric(value, suffix="", decimals=1):
    """Format a metric for Streamlit KPI cards."""
    numeric = to_numeric_value(value)

    if numeric is None:
        return "N/A"

    return f"{numeric:,.{decimals}f}{suffix}"


def is_valid_url(value):
    """Return True when the value looks like an HTTP image URL."""
    if value is None or pd.isna(value):
        return False

    text = str(value).strip()

    return text.startswith("http://") or text.startswith("https://")


def calculate_cagr(start_value, end_value, years):
    """Calculate CAGR for positive start and end values."""
    start_value = to_numeric_value(start_value)
    end_value = to_numeric_value(end_value)

    if (
        start_value is None
        or end_value is None
        or start_value <= 0
        or end_value <= 0
        or years <= 0
    ):
        return None

    return ((end_value / start_value) ** (1 / years) - 1) * 100


def normalise_promoted_header_table(df):
    """
    Repair a table where the real headers were inserted as the first row.

    This is required for the current profitandloss SQLite table.
    """
    if df.empty:
        return df

    existing_columns = [
        str(column).strip().lower()
        for column in df.columns
    ]

    has_unnamed_columns = any(
        column.startswith("unnamed")
        for column in existing_columns
    )

    if not has_unnamed_columns:
        clean = df.copy()

        clean.columns = (
            clean.columns.astype(str)
            .str.strip()
            .str.lower()
            .str.replace(" ", "_")
            .str.replace(r"[^\w]+", "_", regex=True)
            .str.strip("_")
        )

        return clean

    first_row = df.iloc[0].tolist()

    promoted_columns = []

    for index, value in enumerate(first_row):
        if value is None or pd.isna(value):
            promoted_columns.append(f"column_{index}")
        else:
            name = str(value).strip().lower()
            name = re.sub(r"[^\w]+", "_", name).strip("_")

            promoted_columns.append(
                name if name else f"column_{index}"
            )

    repaired = df.iloc[1:].copy()
    repaired.columns = promoted_columns
    repaired = repaired.dropna(how="all").reset_index(drop=True)

    return repaired


def load_profit_and_loss(ticker):
    """Load and repair P&L history for the selected ticker."""
    try:
        raw = run_query(
            "SELECT * FROM profitandloss"
        )
    except Exception:
        return pd.DataFrame()

    if raw.empty:
        return pd.DataFrame()

    pl = normalise_promoted_header_table(raw)

    company_col = find_column(
        pl,
        [
            "company_id",
            "id",
            "ticker",
            "symbol",
        ],
    )

    if company_col is None:
        return pd.DataFrame()

    pl[company_col] = (
        pl[company_col]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return pl[
        pl[company_col] == ticker.strip().upper()
    ].copy()


def load_sector_record(ticker):
    """Load sector and sub-sector information."""
    try:
        sectors = run_query(
            """
            SELECT *
            FROM sectors
            WHERE UPPER(TRIM(company_id)) = UPPER(TRIM(?))
            LIMIT 1
            """,
            (ticker,),
        )
    except Exception:
        return pd.DataFrame()

    return sectors


# =========================================================
# Load Company Master
# =========================================================

companies = get_companies()

if companies.empty:
    st.error("Company master data could not be loaded.")
    st.stop()


company_id_col = find_column(
    companies,
    [
        "id",
        "company_id",
        "ticker",
        "symbol",
        "nse_ticker",
    ],
)

name_col = find_column(
    companies,
    [
        "company_name",
        "name",
    ],
)


if company_id_col is None:
    st.error("A company identifier column could not be found.")

    st.write(
        "Available columns:",
        companies.columns.tolist(),
    )

    st.stop()


# =========================================================
# Build Searchable Labels
# =========================================================

def build_label(row):
    """Build a searchable ticker and company-name label."""
    ticker_value = str(
        row.get(company_id_col, "")
    ).strip()

    name_value = (
        str(row.get(name_col, "")).strip()
        if name_col
        else ""
    )

    if name_value and name_value.lower() != "nan":
        return f"{ticker_value} — {name_value}"

    return ticker_value


companies = companies.copy()

companies[company_id_col] = (
    companies[company_id_col]
    .astype(str)
    .str.strip()
    .str.upper()
)

companies["search_label"] = companies.apply(
    build_label,
    axis=1,
)


# =========================================================
# Search and Selection
# =========================================================

search_text = st.text_input(
    "Search by company name or ticker",
    placeholder="Example: TCS, RELIANCE, HDFCBANK...",
)


filtered = companies.copy()

if search_text.strip():
    filtered = filtered[
        filtered["search_label"].str.contains(
            search_text.strip(),
            case=False,
            na=False,
        )
    ]


if filtered.empty:
    st.warning(
        "Ticker not found — please try another."
    )
    st.stop()


selected_label = st.selectbox(
    "Select company",
    filtered["search_label"].tolist(),
)


company = filtered[
    filtered["search_label"] == selected_label
].iloc[0]


ticker = str(
    company[company_id_col]
).strip().upper()


# =========================================================
# Load Supporting Data
# =========================================================

ratios = get_ratios(ticker)
pl = load_profit_and_loss(ticker)
sector_record = load_sector_record(ticker)


# =========================================================
# Company Information
# =========================================================

company_name = safe_value(
    company,
    [
        "company_name",
        "name",
    ],
    ticker,
)


about = safe_value(
    company,
    [
        "about_company",
        "about",
        "description",
        "company_description",
        "business_description",
    ],
    "Description unavailable.",
)


website = safe_value(
    company,
    [
        "website",
        "company_website",
    ],
    None,
)


company_logo = safe_value(
    company,
    [
        "company_logo",
        "logo",
    ],
    None,
)


sector = "N/A"
sub_sector = "N/A"


if not sector_record.empty:
    sector = safe_value(
        sector_record.iloc[0],
        [
            "broad_sector",
            "sector",
        ],
        "N/A",
    )

    sub_sector = safe_value(
        sector_record.iloc[0],
        [
            "sub_sector",
            "subsector",
        ],
        "N/A",
    )


if sector == "N/A" and not ratios.empty:
    sector = safe_value(
        ratios.iloc[-1],
        [
            "broad_sector",
            "sector",
        ],
        "N/A",
    )


if sub_sector == "N/A" and not ratios.empty:
    sub_sector = safe_value(
        ratios.iloc[-1],
        [
            "sub_sector",
            "subsector",
        ],
        "N/A",
    )


# =========================================================
# Company Card
# =========================================================

info_col, logo_col = st.columns(
    [5, 1],
    vertical_alignment="top",
)


with info_col:
    st.markdown(
        f"""
### {company_name}

**NSE Ticker:** `{ticker}`  
**Sector:** {sector}  
**Sub-sector:** {sub_sector}
"""
    )

    if about and str(about).lower() != "nan":
        st.write(about)

    if is_valid_url(website):
        st.markdown(
            f"🌐 **Website:** [{website}]({website})"
        )


with logo_col:
    if is_valid_url(company_logo):
        try:
            st.image(
                company_logo,
                width=100,
            )
        except Exception:
            pass


st.divider()


# =========================================================
# Prepare Ratio History
# =========================================================

roe = None
roce = None
npm = None
debt_equity = None
revenue_cagr = None
fcf = None


company_roe = safe_value(
    company,
    ["roe_percentage"],
    None,
)

company_roce = safe_value(
    company,
    ["roce_percentage"],
    None,
)


if not ratios.empty:
    ratios = ratios.copy()

    ratio_year_col = find_column(
        ratios,
        [
            "year",
            "financial_year",
        ],
    )

    if ratio_year_col:
        ratios["_year_numeric"] = (
            ratios[ratio_year_col]
            .apply(extract_year)
        )

        ratios = ratios.sort_values(
            "_year_numeric",
            na_position="last",
        )

    valid_rows = ratios.copy()

    if "_year_numeric" in valid_rows.columns:
        valid_rows = valid_rows[
            valid_rows["_year_numeric"].notna()
        ]

    latest_ratio = (
        valid_rows.iloc[-1]
        if not valid_rows.empty
        else ratios.iloc[-1]
    )


    def latest_ratio_metric(candidates):
        column = find_column(
            ratios,
            candidates,
        )

        if column is None:
            return None

        return to_numeric_value(
            latest_ratio[column]
        )


    roe = latest_ratio_metric(
        [
            "return_on_equity_pct",
            "roe_pct",
            "roe_percentage",
            "roe",
        ]
    )

    roce = latest_ratio_metric(
        [
            "return_on_capital_employed_pct",
            "roce_pct",
            "roce_percentage",
            "roce",
        ]
    )

    npm = latest_ratio_metric(
        [
            "net_profit_margin_pct",
            "npm_pct",
            "net_profit_margin",
        ]
    )

    debt_equity = latest_ratio_metric(
        [
            "debt_to_equity",
            "de_ratio",
            "debt_equity_ratio",
        ]
    )

    fcf = latest_ratio_metric(
        [
            "free_cash_flow_cr",
            "free_cash_flow",
            "fcf",
        ]
    )


# Use company master as a fallback for latest ROE and ROCE
if roe is None:
    roe = to_numeric_value(company_roe)

if roce is None:
    roce = to_numeric_value(company_roce)


# =========================================================
# Prepare P&L History and Revenue CAGR
# =========================================================

pl_year_col = None
sales_col = None
net_profit_col = None


if not pl.empty:
    pl_year_col = find_column(
        pl,
        [
            "year",
            "financial_year",
        ],
    )

    sales_col = find_column(
        pl,
        [
            "sales",
            "revenue",
            "total_revenue",
            "revenue_cr",
        ],
    )

    net_profit_col = find_column(
        pl,
        [
            "net_profit",
            "profit_after_tax",
            "pat",
            "net_profit_cr",
        ],
    )

    if pl_year_col:
        pl["_year_numeric"] = (
            pl[pl_year_col]
            .apply(extract_year)
        )

        pl = pl.sort_values(
            "_year_numeric",
            na_position="last",
        )

    if sales_col:
        pl[sales_col] = pd.to_numeric(
            pl[sales_col],
            errors="coerce",
        )

    if net_profit_col:
        pl[net_profit_col] = pd.to_numeric(
            pl[net_profit_col],
            errors="coerce",
        )


    # Calculate 5-year revenue CAGR from the latest six observations
    if (
        sales_col
        and "_year_numeric" in pl.columns
    ):
        sales_history = pl[
            ["_year_numeric", sales_col]
        ].dropna()

        sales_history = (
            sales_history
            .drop_duplicates(
                subset="_year_numeric",
                keep="last",
            )
            .sort_values("_year_numeric")
        )

        if len(sales_history) >= 2:
            latest_year = int(
                sales_history["_year_numeric"].max()
            )

            target_start_year = latest_year - 5

            eligible_start = sales_history[
                sales_history["_year_numeric"]
                <= target_start_year
            ]

            if not eligible_start.empty:
                start_row = eligible_start.iloc[-1]
                end_row = sales_history.iloc[-1]

                elapsed_years = int(
                    end_row["_year_numeric"]
                    - start_row["_year_numeric"]
                )

                revenue_cagr = calculate_cagr(
                    start_row[sales_col],
                    end_row[sales_col],
                    elapsed_years,
                )


# =========================================================
# KPI Tiles
# =========================================================

st.subheader("Latest Financial KPIs")


row1 = st.columns(3)

row1[0].metric(
    "ROE",
    display_metric(roe, "%"),
)

row1[1].metric(
    "ROCE",
    display_metric(roce, "%"),
)

row1[2].metric(
    "Net Profit Margin",
    display_metric(npm, "%"),
)


row2 = st.columns(3)

row2[0].metric(
    "Debt / Equity",
    display_metric(debt_equity, "x"),
)

row2[1].metric(
    "Revenue CAGR (5Y)",
    display_metric(revenue_cagr, "%"),
)

row2[2].metric(
    "Free Cash Flow",
    (
        f"₹{fcf:,.2f} Cr"
        if fcf is not None
        else "N/A"
    ),
)


# =========================================================
# Revenue and Net Profit Trend
# =========================================================

st.divider()

st.subheader(
    "Revenue & Net Profit Trend"
)


if (
    not pl.empty
    and pl_year_col
    and (
        sales_col
        or net_profit_col
    )
):
    chart_columns = [
        column
        for column in [
            sales_col,
            net_profit_col,
        ]
        if column
    ]

    pl_chart = pl.copy()

    if "_year_numeric" in pl_chart.columns:
        pl_chart = (
            pl_chart[
                pl_chart["_year_numeric"].notna()
            ]
            .drop_duplicates(
                subset="_year_numeric",
                keep="last",
            )
            .sort_values("_year_numeric")
            .tail(10)
        )
    else:
        pl_chart = pl_chart.tail(10)

    chart_data = pl_chart[
        [pl_year_col] + chart_columns
    ].copy()

    chart_data = chart_data.melt(
        id_vars=pl_year_col,
        var_name="Metric",
        value_name="INR Crore",
    )

    rename_metrics = {}

    if sales_col:
        rename_metrics[sales_col] = "Revenue"

    if net_profit_col:
        rename_metrics[net_profit_col] = "Net Profit"

    chart_data["Metric"] = (
        chart_data["Metric"]
        .replace(rename_metrics)
    )

    figure = px.bar(
        chart_data,
        x=pl_year_col,
        y="INR Crore",
        color="Metric",
        barmode="group",
        labels={
            pl_year_col: "Financial Year",
            "INR Crore": "₹ Crore",
        },
    )

    figure.update_layout(
        height=500,
        margin=dict(
            l=20,
            r=20,
            t=30,
            b=20,
        ),
        legend_title="Metric",
    )

    st.plotly_chart(
        figure,
        use_container_width=True,
    )

else:
    st.info(
        "Historical P&L data is unavailable for this company."
    )


# =========================================================
# ROE and ROCE Trend
# =========================================================

st.subheader("ROE & ROCE Trend")


if not ratios.empty:
    ratio_year_col = find_column(
        ratios,
        [
            "year",
            "financial_year",
        ],
    )

    roe_col = find_column(
        ratios,
        [
            "return_on_equity_pct",
            "roe_pct",
            "roe_percentage",
            "roe",
        ],
    )

    roce_col = find_column(
        ratios,
        [
            "return_on_capital_employed_pct",
            "roce_pct",
            "roce_percentage",
            "roce",
        ],
    )

    if ratio_year_col and roe_col:
        trend = ratios.copy()

        if "_year_numeric" in trend.columns:
            trend = (
                trend[
                    trend["_year_numeric"].notna()
                ]
                .drop_duplicates(
                    subset="_year_numeric",
                    keep="last",
                )
                .sort_values("_year_numeric")
                .tail(10)
            )
        else:
            trend = trend.tail(10)

        trend_roe = pd.to_numeric(
            trend[roe_col],
            errors="coerce",
        )

        figure = go.Figure()

        figure.add_trace(
            go.Scatter(
                x=trend[ratio_year_col],
                y=trend_roe,
                mode="lines+markers",
                name="ROE",
                yaxis="y",
            )
        )

        if roce_col:
            trend_roce = pd.to_numeric(
                trend[roce_col],
                errors="coerce",
            )

            figure.add_trace(
                go.Scatter(
                    x=trend[ratio_year_col],
                    y=trend_roce,
                    mode="lines+markers",
                    name="ROCE",
                    yaxis="y2",
                )
            )

        elif roce is not None:
            # Historical ROCE is not stored in the current ratio table.
            # Display the latest available company-master ROCE as a
            # reference line rather than inventing historical values.
            figure.add_trace(
                go.Scatter(
                    x=trend[ratio_year_col],
                    y=[roce] * len(trend),
                    mode="lines",
                    name="Latest ROCE reference",
                    line=dict(dash="dash"),
                    yaxis="y2",
                )
            )

        figure.update_layout(
            height=500,
            margin=dict(
                l=20,
                r=20,
                t=40,
                b=20,
            ),
            xaxis=dict(
                title="Financial Year",
            ),
            yaxis=dict(
                title="ROE (%)",
            ),
            yaxis2=dict(
                title="ROCE (%)",
                overlaying="y",
                side="right",
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
            ),
        )

        st.plotly_chart(
            figure,
            use_container_width=True,
        )

        if not roce_col:
            st.caption(
                "Historical ROCE is unavailable in the current "
                "financial-ratios table. The dashed line represents "
                "the latest available ROCE from the company master."
            )

    else:
        st.info(
            "ROE and ROCE history is unavailable."
        )

else:
    st.info(
        "ROE and ROCE history is unavailable."
    )


# =========================================================
# Financial Strengths and Risks
# =========================================================

st.divider()

st.subheader(
    "Financial Strengths & Risks"
)


pros = []
cons = []


if roe is not None:
    if roe >= 20:
        pros.append(
            "High return on equity indicates strong capital efficiency."
        )
    elif roe < 10:
        cons.append(
            "ROE below 10% indicates relatively weak equity returns."
        )


if roce is not None:
    if roce >= 15:
        pros.append(
            "Strong ROCE indicates efficient deployment of invested capital."
        )
    elif roce < 10:
        cons.append(
            "ROCE below 10% suggests weak returns on invested capital."
        )


if debt_equity is not None:
    if debt_equity == 0:
        pros.append(
            "Debt-free balance sheet provides financial flexibility."
        )
    elif debt_equity > 2:
        cons.append(
            "Elevated debt-to-equity ratio increases financial risk."
        )


if revenue_cagr is not None:
    if revenue_cagr >= 15:
        pros.append(
            "Five-year revenue CAGR above 15% shows strong business momentum."
        )
    elif revenue_cagr < 5:
        cons.append(
            "Five-year revenue growth below 5% indicates limited momentum."
        )


if fcf is not None:
    if fcf > 0:
        pros.append(
            "Positive free cash flow supports healthy internal cash generation."
        )
    elif fcf < 0:
        cons.append(
            "Negative free cash flow requires closer monitoring."
        )


pros_column, cons_column = st.columns(2)


with pros_column:
    st.markdown("### ✅ Pros")

    if pros:
        for item in pros:
            st.success(item)
    else:
        st.info(
            "No strong positive signals detected "
            "from currently available metrics."
        )


with cons_column:
    st.markdown("### ❌ Cons")

    if cons:
        for item in cons:
            st.error(item)
    else:
        st.info(
            "No major risk signals detected "
            "from currently available metrics."
        )


st.caption(
    "Pros and cons currently use financial KPI rules. "
    "Sprint 5 will replace or extend these with the "
    "dedicated NLP pros-cons engine."
)