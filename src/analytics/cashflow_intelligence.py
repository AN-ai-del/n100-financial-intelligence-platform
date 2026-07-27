"""
Sprint 5 — Day 31
Cash Flow Intelligence Engine

Builds company-year cash-flow intelligence by combining:

- Cash-flow statement data
- Profit & Loss data
- Existing financial-ratio data
- Company master data
- Existing Sprint 2 cash-flow KPI functions

Metrics:
- Free Cash Flow
- CFO Quality Score
- CFO Quality Label
- CapEx Intensity
- CapEx Intensity Label
- FCF Conversion Rate
- CFO / CFI / CFF sign pattern
- Capital Allocation Pattern
- Negative FCF streak
- CFO distress flag
- FCF distress flag
- Financing dependence flag
- Overall distress flag
- Cash Flow Health Score
- Cash Flow Health Label

Output:
    output/cashflow_intelligence.csv
"""

from __future__ import annotations

from pathlib import Path
import re
import sqlite3

import numpy as np
import pandas as pd

from src.analytics.cashflow_kpis import (
    calculate_free_cash_flow,
    calculate_cfo_quality_score,
    calculate_capex_intensity,
    calculate_fcf_conversion_rate,
    get_sign,
    classify_capital_allocation,
)


# ============================================================
# PATH CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = (
    PROJECT_ROOT
    / "db"
    / "nifty100.db"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "output"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "cashflow_intelligence.csv"
)


# ============================================================
# GENERAL HELPERS
# ============================================================

def normalize_column(value):
    """
    Convert a column name into a predictable snake_case form.
    """

    text = str(value).strip().lower()

    text = re.sub(
        r"[^\w]+",
        "_",
        text,
    )

    return text.strip("_")


def normalize_company_id(value):
    """
    Standardise company tickers.
    """

    if value is None or pd.isna(value):
        return ""

    return str(value).strip().upper()


def safe_numeric(value):
    """
    Convert financial values to float safely.
    """

    if value is None or pd.isna(value):
        return np.nan

    text = (
        str(value)
        .replace(",", "")
        .replace("%", "")
        .replace("₹", "")
        .strip()
    )

    if text.lower() in {
        "",
        "nan",
        "none",
        "null",
        "n/a",
        "na",
        "-",
    }:
        return np.nan

    try:
        return float(text)

    except (TypeError, ValueError):
        return np.nan


def extract_year(value):
    """
    Convert labels such as:

        Mar-13
        Mar 2014
        Dec 2012
        2024

    into integer financial years.
    """

    if value is None or pd.isna(value):
        return np.nan

    text = str(value).strip()

    four_digit = re.search(
        r"(19|20)\d{2}",
        text,
    )

    if four_digit:
        return int(
            four_digit.group()
        )

    two_digit = re.search(
        r"(?<!\d)(\d{2})(?!\d)",
        text,
    )

    if two_digit:

        year = int(
            two_digit.group(1)
        )

        if year <= 50:
            return 2000 + year

        return 1900 + year

    return np.nan


def repair_embedded_header(df):
    """
    Repair raw SQLite tables where the real header exists
    in the first data row.
    """

    if df.empty:
        return df.copy()

    first_row = df.iloc[0]

    normalized_first_row = [
        normalize_column(value)
        if pd.notna(value)
        else ""
        for value in first_row
    ]

    if (
        "company_id" in normalized_first_row
        and "year" in normalized_first_row
    ):

        repaired = (
            df.iloc[1:]
            .copy()
        )

        repaired.columns = [
            normalize_column(value)
            if pd.notna(value)
            else f"column_{index}"
            for index, value in enumerate(
                first_row
            )
        ]

        return repaired.reset_index(
            drop=True
        )

    repaired = df.copy()

    repaired.columns = [
        normalize_column(column)
        for column in repaired.columns
    ]

    return repaired


# ============================================================
# DATABASE LOADERS
# ============================================================

def load_table(
    connection,
    table_name,
):
    return pd.read_sql_query(
        f'SELECT * FROM "{table_name}"',
        connection,
    )


def load_project_data():

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    connection = sqlite3.connect(
        DB_PATH
    )

    cashflow = load_table(
        connection,
        "cashflow",
    )

    pnl = load_table(
        connection,
        "profitandloss",
    )

    ratios = load_table(
        connection,
        "financial_ratios",
    )

    companies = load_table(
        connection,
        "companies",
    )

    connection.close()

    return (
        cashflow,
        pnl,
        ratios,
        companies,
    )



# ============================================================
# DATA PREPARATION
# ============================================================

def prepare_cashflow(df):

    df = repair_embedded_header(
        df
    )

    required = {
        "company_id",
        "year",
        "operating_activity",
        "investing_activity",
        "financing_activity",
    }

    missing = (
        required
        - set(df.columns)
    )

    if missing:
        raise ValueError(
            "Missing cash-flow columns: "
            + ", ".join(
                sorted(missing)
            )
        )

    df["company_id"] = (
        df["company_id"]
        .apply(normalize_company_id)
    )

    df["year_numeric"] = (
        df["year"]
        .apply(extract_year)
    )

    numeric_columns = [
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = (
                df[column]
                .apply(safe_numeric)
            )

    df = df[
        df["company_id"] != ""
    ].copy()

    df = df[
        df["year_numeric"].notna()
    ].copy()

    df["year_numeric"] = (
        df["year_numeric"]
        .astype(int)
    )

    df["_completeness"] = (
        df[
            [
                "operating_activity",
                "investing_activity",
                "financing_activity",
            ]
        ]
        .notna()
        .sum(axis=1)
    )

    df = (
        df
        .sort_values(
            [
                "company_id",
                "year_numeric",
                "_completeness",
            ],
            ascending=[
                True,
                True,
                False,
            ],
        )
        .drop_duplicates(
            subset=[
                "company_id",
                "year_numeric",
            ],
            keep="first",
        )
        .drop(
            columns=[
                "_completeness",
            ]
        )
        .reset_index(drop=True)
    )

    return df


def prepare_pnl(df):

    df = repair_embedded_header(
        df
    )

    required = {
        "company_id",
        "year",
        "sales",
        "operating_profit",
        "net_profit",
    }

    missing = (
        required
        - set(df.columns)
    )

    if missing:
        raise ValueError(
            "Missing P&L columns: "
            + ", ".join(
                sorted(missing)
            )
        )

    df["company_id"] = (
        df["company_id"]
        .apply(normalize_company_id)
    )

    df["year_numeric"] = (
        df["year"]
        .apply(extract_year)
    )

    numeric_columns = [
        "sales",
        "operating_profit",
        "net_profit",
    ]

    for column in numeric_columns:

        df[column] = (
            df[column]
            .apply(safe_numeric)
        )

    df = df[
        df["company_id"] != ""
    ].copy()

    df = df[
        df["year_numeric"].notna()
    ].copy()

    df["year_numeric"] = (
        df["year_numeric"]
        .astype(int)
    )

    df["_completeness"] = (
        df[
            numeric_columns
        ]
        .notna()
        .sum(axis=1)
    )

    df = (
        df
        .sort_values(
            [
                "company_id",
                "year_numeric",
                "_completeness",
            ],
            ascending=[
                True,
                True,
                False,
            ],
        )
        .drop_duplicates(
            subset=[
                "company_id",
                "year_numeric",
            ],
            keep="first",
        )
        .drop(
            columns=[
                "_completeness",
            ]
        )
        .reset_index(drop=True)
    )

    return df


def prepare_ratios(df):

    df = df.copy()

    df.columns = [
        normalize_column(column)
        for column in df.columns
    ]

    df["company_id"] = (
        df["company_id"]
        .apply(normalize_company_id)
    )

    df["year_numeric"] = (
        df["year"]
        .apply(extract_year)
    )

    numeric_columns = [
        "return_on_equity_pct",
        "debt_to_equity",
        "interest_coverage",
        "free_cash_flow_cr",
        "capex_cr",
        "cash_from_operations_cr",
    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = (
                df[column]
                .apply(safe_numeric)
            )

    df = df[
        df["year_numeric"].notna()
    ].copy()

    df["year_numeric"] = (
        df["year_numeric"]
        .astype(int)
    )

    df["_completeness"] = (
        df[
            [
                column
                for column in numeric_columns
                if column in df.columns
            ]
        ]
        .notna()
        .sum(axis=1)
    )

    df = (
        df
        .sort_values(
            [
                "company_id",
                "year_numeric",
                "_completeness",
            ],
            ascending=[
                True,
                True,
                False,
            ],
        )
        .drop_duplicates(
            subset=[
                "company_id",
                "year_numeric",
            ],
            keep="first",
        )
        .drop(
            columns=[
                "_completeness",
            ]
        )
        .reset_index(drop=True)
    )

    return df


def prepare_companies(df):

    df = df.copy()

    df.columns = [
        normalize_column(column)
        for column in df.columns
    ]

    df["company_id"] = (
        df["id"]
        .apply(normalize_company_id)
    )

    df["company_name"] = (
        df["company_name"]
        .astype(str)
        .str.strip()
    )

    return df[
        [
            "company_id",
            "company_name",
        ]
    ].drop_duplicates(
        subset=[
            "company_id",
        ]
    )


# ============================================================
# KPI WRAPPERS
# ============================================================

def calculate_row_kpis(row):

    cfo = row[
        "operating_activity"
    ]

    cfi = row[
        "investing_activity"
    ]

    cff = row[
        "financing_activity"
    ]

    pat = row[
        "net_profit"
    ]

    sales = row[
        "sales"
    ]

    operating_profit = row[
        "operating_profit"
    ]

    # --------------------------------------------------------
    # Free Cash Flow
    # --------------------------------------------------------

    if (
        pd.notna(cfo)
        and pd.notna(cfi)
    ):

        free_cash_flow = (
            calculate_free_cash_flow(
                cfo,
                cfi,
            )
        )

    else:

        free_cash_flow = np.nan

    # --------------------------------------------------------
    # CFO Quality
    # --------------------------------------------------------

    if (
        pd.notna(cfo)
        and pd.notna(pat)
    ):

        (
            cfo_quality_score,
            cfo_quality_label,
        ) = calculate_cfo_quality_score(
            cfo,
            pat,
        )

    else:

        cfo_quality_score = np.nan
        cfo_quality_label = (
            "NOT_AVAILABLE"
        )

    # --------------------------------------------------------
    # CapEx Intensity
    #
    # Existing Sprint 2 logic uses abs(CFI) / Sales.
    # --------------------------------------------------------

    if (
        pd.notna(cfi)
        and pd.notna(sales)
    ):

        (
            capex_intensity_pct,
            capex_intensity_label,
        ) = calculate_capex_intensity(
            cfi,
            sales,
        )

    else:

        capex_intensity_pct = np.nan
        capex_intensity_label = (
            "NOT_AVAILABLE"
        )

    # --------------------------------------------------------
    # FCF Conversion
    # --------------------------------------------------------

    if (
        pd.notna(free_cash_flow)
        and pd.notna(operating_profit)
    ):

        fcf_conversion_rate = (
            calculate_fcf_conversion_rate(
                free_cash_flow,
                operating_profit,
            )
        )

    else:

        fcf_conversion_rate = np.nan

    # --------------------------------------------------------
    # Signs
    # --------------------------------------------------------

    cfo_sign = (
        get_sign(cfo)
        if pd.notna(cfo)
        else "NA"
    )

    cfi_sign = (
        get_sign(cfi)
        if pd.notna(cfi)
        else "NA"
    )

    cff_sign = (
        get_sign(cff)
        if pd.notna(cff)
        else "NA"
    )

    # --------------------------------------------------------
    # Capital Allocation
    # --------------------------------------------------------

    if (
        pd.notna(cfo)
        and pd.notna(cfi)
        and pd.notna(cff)
    ):

        capital_allocation = (
            classify_capital_allocation(
                cfo,
                cfi,
                cff,
                cfo_quality_label,
            )
        )

    else:

        capital_allocation = (
            "NOT_AVAILABLE"
        )

    return pd.Series(
        {
            "free_cash_flow_cr":
                free_cash_flow,

            "cfo_quality_score":
                cfo_quality_score,

            "cfo_quality_label":
                cfo_quality_label,

            "capex_intensity_pct":
                capex_intensity_pct,

            "capex_intensity_label":
                capex_intensity_label,

            "fcf_conversion_rate_pct":
                fcf_conversion_rate,

            "cfo_sign":
                cfo_sign,

            "cfi_sign":
                cfi_sign,

            "cff_sign":
                cff_sign,

            "capital_allocation_pattern":
                capital_allocation,
        }
    )


# ============================================================
# DISTRESS ENGINE
# ============================================================

def add_distress_flags(df):

    df = (
        df
        .sort_values(
            [
                "company_id",
                "year_numeric",
            ]
        )
        .reset_index(drop=True)
    )

    df[
        "negative_fcf_3yr_flag"
    ] = False

    df[
        "negative_cfo_flag"
    ] = (
        df["operating_activity"]
        < 0
    )

    df[
        "financing_dependence_flag"
    ] = (
        (
            df["operating_activity"]
            < 0
        )
        &
        (
            df["financing_activity"]
            > 0
        )
    )

    df[
        "capital_allocation_distress_flag"
    ] = (
        df[
            "capital_allocation_pattern"
        ]
        .isin(
            [
                "Distress Signal",
                "Growth Funded by Debt",
                "Pre-Revenue",
            ]
        )
    )

    # --------------------------------------------------------
    # 3-year negative FCF streak
    # --------------------------------------------------------

    for company_id, group in df.groupby(
        "company_id",
        sort=False,
    ):

        indexes = (
            group.index.tolist()
        )

        fcf_values = (
            group[
                "free_cash_flow_cr"
            ]
            .tolist()
        )

        for position in range(
            len(fcf_values)
        ):

            if position < 2:
                continue

            window = (
                fcf_values[
                    position - 2:
                    position + 1
                ]
            )

            if (
                all(
                    pd.notna(value)
                    for value in window
                )
                and all(
                    value < 0
                    for value in window
                )
            ):

                df.loc[
                    indexes[position],
                    "negative_fcf_3yr_flag",
                ] = True

    # --------------------------------------------------------
    # Overall distress flag
    # --------------------------------------------------------

    df[
        "distress_flag"
    ] = (
        df[
            [
                "negative_fcf_3yr_flag",
                "negative_cfo_flag",
                "financing_dependence_flag",
                "capital_allocation_distress_flag",
            ]
        ]
        .any(axis=1)
    )

    return df


# ============================================================
# HEALTH SCORING
# ============================================================

def calculate_health_score(row):

    score = 50

    # --------------------------------------------------------
    # CFO Quality
    # --------------------------------------------------------

    label = row[
        "cfo_quality_label"
    ]

    if label == "High Quality":
        score += 20

    elif label == "Moderate":
        score += 10

    elif label == "Accrual Risk":
        score -= 20

    # --------------------------------------------------------
    # Free Cash Flow
    # --------------------------------------------------------

    fcf = row[
        "free_cash_flow_cr"
    ]

    if pd.notna(fcf):

        if fcf > 0:
            score += 15

        elif fcf < 0:
            score -= 15

    # --------------------------------------------------------
    # Capital allocation
    # --------------------------------------------------------

    allocation = row[
        "capital_allocation_pattern"
    ]

    if allocation in {
        "Shareholder Returns",
        "Reinvestor",
    }:
        score += 10

    elif allocation in {
        "Distress Signal",
        "Growth Funded by Debt",
        "Pre-Revenue",
    }:
        score -= 15

    # --------------------------------------------------------
    # Persistent negative FCF
    # --------------------------------------------------------

    if row[
        "negative_fcf_3yr_flag"
    ]:
        score -= 20

    # --------------------------------------------------------
    # Financing dependence
    # --------------------------------------------------------

    if row[
        "financing_dependence_flag"
    ]:
        score -= 10

    return int(
        max(
            0,
            min(
                100,
                score,
            ),
        )
    )


def classify_health(score):

    if score >= 80:
        return "Strong"

    if score >= 60:
        return "Healthy"

    if score >= 40:
        return "Watch"

    return "Distress"


# ============================================================
# MAIN INTELLIGENCE ENGINE
# ============================================================

def build_cashflow_intelligence():

    print("=" * 100)
    print(
        "SPRINT 5 — DAY 31 CASH FLOW INTELLIGENCE ENGINE"
    )
    print("=" * 100)

    (
        cashflow_raw,
        pnl_raw,
        ratios_raw,
        companies_raw,
    ) = load_project_data()

    # --------------------------------------------------------
    # Prepare data
    # --------------------------------------------------------

    cashflow = prepare_cashflow(
        cashflow_raw
    )

    pnl = prepare_pnl(
        pnl_raw
    )

    ratios = prepare_ratios(
        ratios_raw
    )

    companies = prepare_companies(
        companies_raw
    )

    # --------------------------------------------------------
    # Official project universe reconciliation
    # --------------------------------------------------------

    official_company_ids = set(
        companies["company_id"]
    )

    raw_cashflow_company_ids = set(
        cashflow["company_id"]
    )

    raw_pnl_company_ids = set(
        pnl["company_id"]
    )

    raw_ratio_company_ids = set(
        ratios["company_id"]
    )

    unexpected_cashflow_companies = sorted(
        raw_cashflow_company_ids
        - official_company_ids
    )

    unexpected_pnl_companies = sorted(
        raw_pnl_company_ids
        - official_company_ids
    )

    unexpected_ratio_companies = sorted(
        raw_ratio_company_ids
        - official_company_ids
    )

    missing_cashflow_companies = sorted(
        official_company_ids
        - raw_cashflow_company_ids
    )

    missing_pnl_companies = sorted(
        official_company_ids
        - raw_pnl_company_ids
    )

    missing_ratio_companies = sorted(
        official_company_ids
        - raw_ratio_company_ids
    )

    print("\nUNIVERSE RECONCILIATION")
    print("-" * 100)

    print(
        f"Official universe              : "
        f"{len(official_company_ids)}"
    )

    print(
        f"Raw cash-flow companies        : "
        f"{len(raw_cashflow_company_ids)}"
    )

    print(
        f"Raw P&L companies              : "
        f"{len(raw_pnl_company_ids)}"
    )

    print(
        f"Raw financial-ratio companies  : "
        f"{len(raw_ratio_company_ids)}"
    )

    print(
        f"Unexpected cash-flow companies : "
        f"{len(unexpected_cashflow_companies)}"
    )

    if unexpected_cashflow_companies:
        print(
            "Excluded cash-flow companies   : "
            + ", ".join(
                unexpected_cashflow_companies
            )
        )
    else:
        print(
            "Excluded cash-flow companies   : None"
        )

    print(
        f"Unexpected P&L companies       : "
        f"{len(unexpected_pnl_companies)}"
    )

    if unexpected_pnl_companies:
        print(
            "Excluded P&L companies         : "
            + ", ".join(
                unexpected_pnl_companies
            )
        )
    else:
        print(
            "Excluded P&L companies         : None"
        )

    print(
        f"Unexpected ratio companies     : "
        f"{len(unexpected_ratio_companies)}"
    )

    if unexpected_ratio_companies:
        print(
            "Excluded ratio companies       : "
            + ", ".join(
                unexpected_ratio_companies
            )
        )
    else:
        print(
            "Excluded ratio companies       : None"
        )

    print(
        f"Official companies without CF  : "
        f"{len(missing_cashflow_companies)}"
    )

    if missing_cashflow_companies:
        print(
            "Missing cash-flow data          : "
            + ", ".join(
                missing_cashflow_companies
            )
        )
    else:
        print(
            "Missing cash-flow data          : None"
        )

    print(
        f"Official companies without P&L : "
        f"{len(missing_pnl_companies)}"
    )

    if missing_pnl_companies:
        print(
            "Missing P&L data                : "
            + ", ".join(
                missing_pnl_companies
            )
        )
    else:
        print(
            "Missing P&L data                : None"
        )

    print(
        f"Official companies without ratio: "
        f"{len(missing_ratio_companies)}"
    )

    if missing_ratio_companies:
        print(
            "Missing ratio data              : "
            + ", ".join(
                missing_ratio_companies
            )
        )
    else:
        print(
            "Missing ratio data              : None"
        )

    # --------------------------------------------------------
    # Restrict analytical datasets to official companies
    #
    # Important:
    # Unexpected raw tickers are excluded rather than renamed.
    # Missing official-company data is kept transparent.
    # No financial values are fabricated or remapped.
    # --------------------------------------------------------

    cashflow = cashflow[
        cashflow["company_id"].isin(
            official_company_ids
        )
    ].copy()

    pnl = pnl[
        pnl["company_id"].isin(
            official_company_ids
        )
    ].copy()

    ratios = ratios[
        ratios["company_id"].isin(
            official_company_ids
        )
    ].copy()

    # --------------------------------------------------------
    # Post-reconciliation coverage
    # --------------------------------------------------------

    print("\nDATA COVERAGE — OFFICIAL UNIVERSE")
    print("-" * 100)

    print(
        f"Official companies       : "
        f"{companies['company_id'].nunique()}"
    )

    print(
        f"Cash-flow companies      : "
        f"{cashflow['company_id'].nunique()}"
    )

    print(
        f"P&L companies            : "
        f"{pnl['company_id'].nunique()}"
    )

    print(
        f"Financial-ratio companies: "
        f"{ratios['company_id'].nunique()}"
    )

    print(
        f"Cash-flow records        : "
        f"{len(cashflow)}"
    )

    # --------------------------------------------------------
    # Join cash flow with P&L
    # --------------------------------------------------------

    pnl_subset = pnl[
        [
            "company_id",
            "year_numeric",
            "sales",
            "operating_profit",
            "net_profit",
        ]
    ].copy()

    intelligence = cashflow.merge(
        pnl_subset,
        on=[
            "company_id",
            "year_numeric",
        ],
        how="left",
    )

    # --------------------------------------------------------
    # Add company name
    # --------------------------------------------------------

    intelligence = intelligence.merge(
        companies,
        on="company_id",
        how="left",
    )

    # --------------------------------------------------------
    # Calculate KPI layer
    # --------------------------------------------------------

    kpis = intelligence.apply(
        calculate_row_kpis,
        axis=1,
    )

    intelligence = pd.concat(
        [
            intelligence,
            kpis,
        ],
        axis=1,
    )

    # --------------------------------------------------------
    # Add distress intelligence
    # --------------------------------------------------------

    intelligence = add_distress_flags(
        intelligence
    )

    # --------------------------------------------------------
    # Health score
    # --------------------------------------------------------

    intelligence[
        "cashflow_health_score"
    ] = intelligence.apply(
        calculate_health_score,
        axis=1,
    )

    intelligence[
        "cashflow_health_label"
    ] = intelligence[
        "cashflow_health_score"
    ].apply(
        classify_health
    )

    # --------------------------------------------------------
    # Final ordering
    # --------------------------------------------------------

    final_columns = [
        "company_id",
        "company_name",
        "year",
        "year_numeric",

        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",

        "sales",
        "operating_profit",
        "net_profit",

        "free_cash_flow_cr",

        "cfo_quality_score",
        "cfo_quality_label",

        "capex_intensity_pct",
        "capex_intensity_label",

        "fcf_conversion_rate_pct",

        "cfo_sign",
        "cfi_sign",
        "cff_sign",

        "capital_allocation_pattern",

        "negative_fcf_3yr_flag",
        "negative_cfo_flag",
        "financing_dependence_flag",
        "capital_allocation_distress_flag",
        "distress_flag",

        "cashflow_health_score",
        "cashflow_health_label",
    ]

    intelligence = intelligence[
        final_columns
    ].copy()

    intelligence = (
        intelligence
        .sort_values(
            [
                "company_id",
                "year_numeric",
            ]
        )
        .reset_index(drop=True)
    )

    return (
        intelligence,
        companies,
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_cashflow_intelligence(
    intelligence,
    companies,
):

    print("\n" + "=" * 100)
    print(
        "DAY 31 CASH FLOW INTELLIGENCE VALIDATION"
    )
    print("=" * 100)

    official = set(
        companies[
            "company_id"
        ]
    )

    covered = set(
        intelligence[
            "company_id"
        ]
    )

    missing = sorted(
        official
        - covered
    )

    print(
        f"\nIntelligence records : "
        f"{len(intelligence)}"
    )

    print(
        f"Companies covered    : "
        f"{len(covered)}"
    )

    print(
        f"Official companies   : "
        f"{len(official)}"
    )

    print("\nCompanies without cash-flow records:")

    if missing:

        for company_id in missing:
            print(
                f"  - {company_id}"
            )

    else:
        print(
            "None"
        )

    # --------------------------------------------------------
    # Missing KPI counts
    # --------------------------------------------------------

    print("\nKPI AVAILABILITY")
    print("-" * 100)

    kpi_columns = [
        "free_cash_flow_cr",
        "cfo_quality_score",
        "capex_intensity_pct",
        "fcf_conversion_rate_pct",
    ]

    for column in kpi_columns:

        available = (
            intelligence[
                column
            ]
            .notna()
            .sum()
        )

        print(
            f"{column:<30}: "
            f"{available}/{len(intelligence)}"
        )

    # --------------------------------------------------------
    # CFO quality distribution
    # --------------------------------------------------------

    print("\nCFO QUALITY DISTRIBUTION")
    print("-" * 100)

    print(
        intelligence[
            "cfo_quality_label"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    # --------------------------------------------------------
    # CapEx distribution
    # --------------------------------------------------------

    print("\nCAPEX INTENSITY DISTRIBUTION")
    print("-" * 100)

    print(
        intelligence[
            "capex_intensity_label"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    # --------------------------------------------------------
    # Capital allocation
    # --------------------------------------------------------

    print("\nCAPITAL ALLOCATION DISTRIBUTION")
    print("-" * 100)

    print(
        intelligence[
            "capital_allocation_pattern"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    # --------------------------------------------------------
    # Distress
    # --------------------------------------------------------

    print("\nDISTRESS FLAGS")
    print("-" * 100)

    print(
        "3-year negative FCF : "
        f"{intelligence['negative_fcf_3yr_flag'].sum()}"
    )

    print(
        "Negative CFO        : "
        f"{intelligence['negative_cfo_flag'].sum()}"
    )

    print(
        "Financing dependent : "
        f"{intelligence['financing_dependence_flag'].sum()}"
    )

    print(
        "Allocation distress : "
        f"{intelligence['capital_allocation_distress_flag'].sum()}"
    )

    print(
        "Overall distress    : "
        f"{intelligence['distress_flag'].sum()}"
    )

    # --------------------------------------------------------
    # Health distribution
    # --------------------------------------------------------

    print("\nCASH FLOW HEALTH DISTRIBUTION")
    print("-" * 100)

    print(
        intelligence[
            "cashflow_health_label"
        ]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # Latest company records
    # --------------------------------------------------------

    latest = (
        intelligence
        .sort_values(
            "year_numeric"
        )
        .groupby(
            "company_id",
            as_index=False,
        )
        .tail(1)
        .sort_values(
            "company_id"
        )
    )

    print("\nLATEST COMPANY SNAPSHOT")
    print("-" * 100)

    snapshot_columns = [
        "company_id",
        "year_numeric",
        "free_cash_flow_cr",
        "cfo_quality_label",
        "capex_intensity_label",
        "capital_allocation_pattern",
        "distress_flag",
        "cashflow_health_score",
        "cashflow_health_label",
    ]

    print(
        latest[
            snapshot_columns
        ]
        .head(20)
        .to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # Core validation
    # --------------------------------------------------------

    invalid_scores = intelligence[
        (
            intelligence[
                "cashflow_health_score"
            ]
            < 0
        )
        |
        (
            intelligence[
                "cashflow_health_score"
            ]
            > 100
        )
    ]

    duplicate_records = (
        intelligence
        .duplicated(
            subset=[
                "company_id",
                "year_numeric",
            ]
        )
        .sum()
    )

    print("\nVALIDATION CHECKS")
    print("-" * 100)

    print(
        f"Duplicate company-year records : "
        f"{duplicate_records}"
    )

    print(
        f"Invalid health scores          : "
        f"{len(invalid_scores)}"
    )

    passed = (
        duplicate_records == 0
        and len(invalid_scores) == 0
        and len(intelligence) > 0
    )

    if passed:

        print("\n" + "=" * 100)
        print(
            "DAY 31 VALIDATION PASSED"
        )
        print("=" * 100)

    else:

        print("\n" + "=" * 100)
        print(
            "DAY 31 VALIDATION FAILED"
        )
        print("=" * 100)

    return passed


# ============================================================
# SAVE OUTPUT
# ============================================================

def save_output(
    intelligence,
):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    intelligence.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print(
        f"\nOutput saved to:"
        f"\n{OUTPUT_PATH}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    (
        intelligence,
        companies,
    ) = build_cashflow_intelligence()

    passed = (
        validate_cashflow_intelligence(
            intelligence,
            companies,
        )
    )

    save_output(
        intelligence
    )

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()