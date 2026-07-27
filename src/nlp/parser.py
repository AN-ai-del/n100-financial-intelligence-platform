"""
Sprint 5 — Day 29
NLP Analysis Text Parser

Tasks completed:
- Parse analysis.xlsx text fields using regex
- Extract period and percentage values
- Support positive and negative percentages
- Generate output/analysis_parsed.csv
- Generate output/parse_failures.csv
- Cross-validate sales CAGR and profit CAGR against historical P&L
- Cross-validate stock-price CAGR against stock-price history
- Flag divergences greater than 5 percentage points for manual review
"""

from __future__ import annotations

from pathlib import Path
import re
import sqlite3
from typing import Optional

import numpy as np
import pandas as pd


# ============================================================
# PATH CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ANALYSIS_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "analysis.xlsx"
)

DB_PATH = (
    PROJECT_ROOT
    / "db"
    / "nifty100.db"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "output"
)

PARSED_OUTPUT_PATH = (
    OUTPUT_DIR
    / "analysis_parsed.csv"
)

FAILURE_OUTPUT_PATH = (
    OUTPUT_DIR
    / "parse_failures.csv"
)


# ============================================================
# PARSER CONFIGURATION
# ============================================================

TARGET_FIELDS = [
    "compounded_sales_growth",
    "compounded_profit_growth",
    "stock_price_cagr",
    "roe",
]


# Required project pattern:
# (\d+)\s*Years?:?\s*([\d.]+)%
#
# Extended slightly to support:
# - negative percentages
# - positive signs
# - spaces before %
#
# Examples:
# 10 Years: 21%
# 5 Years 17.4%
# 1 Year: -2%
# 3 Years: +12.5 %
CAGR_PATTERN = re.compile(
    r"(\d+)\s*Years?\s*:?\s*([-+]?\d+(?:\.\d+)?)\s*%",
    flags=re.IGNORECASE,
)


# Handle labels that do not contain a numeric year count.
TTM_PATTERN = re.compile(
    r"TTM\s*:?\s*([-+]?\d+(?:\.\d+)?)\s*%",
    flags=re.IGNORECASE,
)


LAST_YEAR_PATTERN = re.compile(
    r"Last\s+Year\s*:?\s*([-+]?\d+(?:\.\d+)?)\s*%",
    flags=re.IGNORECASE,
)


DIVERGENCE_THRESHOLD = 5.0


# ============================================================
# GENERAL HELPERS
# ============================================================

def normalize_company_id(value) -> str:
    """Normalize company identifiers before joins."""

    if value is None or pd.isna(value):
        return ""

    return (
        str(value)
        .strip()
        .upper()
    )


def normalize_column_name(value) -> str:
    """Convert raw column names to snake_case."""

    text = str(value).strip().lower()

    text = re.sub(
        r"[^\w]+",
        "_",
        text,
    )

    return text.strip("_")


def safe_numeric(value) -> float:
    """Convert raw values safely to floating-point numbers."""

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
        "na",
        "n/a",
        "-",
    }:
        return np.nan

    try:
        return float(text)

    except (TypeError, ValueError):
        return np.nan


def extract_year(value) -> float:
    """
    Extract a four-digit year.

    Supported examples:
    - Mar 2024
    - Mar-24
    - Dec 2012
    - 2024
    """

    if value is None or pd.isna(value):
        return np.nan

    text = str(value).strip()

    four_digit_match = re.search(
        r"(19|20)\d{2}",
        text,
    )

    if four_digit_match:
        return float(
            four_digit_match.group()
        )

    two_digit_match = re.search(
        r"(?<!\d)(\d{2})(?!\d)",
        text,
    )

    if two_digit_match:
        year = int(
            two_digit_match.group(1)
        )

        if year <= 50:
            return float(
                2000 + year
            )

        return float(
            1900 + year
        )

    numeric = pd.to_numeric(
        text,
        errors="coerce",
    )

    if pd.notna(numeric) and 1900 <= numeric <= 2100:
        return float(numeric)

    return np.nan


def calculate_cagr(
    start_value,
    end_value,
    years: int,
) -> float:
    """
    Calculate CAGR.

    If the base value is negative or zero, CAGR is unavailable.
    The project rule says negative base years should be treated
    as TURNAROUND rather than forcing a CAGR calculation.
    """

    start = safe_numeric(
        start_value
    )

    end = safe_numeric(
        end_value
    )

    if (
        pd.isna(start)
        or pd.isna(end)
        or years <= 0
        or start <= 0
        or end <= 0
    ):
        return np.nan

    return (
        (
            end / start
        )
        ** (
            1 / years
        )
        - 1
    ) * 100


def repair_embedded_header(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Repair SQLite tables where the actual headers were imported
    as the first data row.

    Examples include:
    - profitandloss
    - cashflow
    - documents
    """

    if df.empty:
        return df

    current_columns = [
        normalize_column_name(column)
        for column in df.columns
    ]

    malformed = any(
        column.startswith("unnamed")
        for column in current_columns
    )

    if current_columns:
        first_column = current_columns[0]

        if (
            "bluestock" in first_column
            or "records" in first_column
        ):
            malformed = True

    if malformed:

        first_row = df.iloc[0]

        new_columns = []

        for index, value in enumerate(
            first_row
        ):

            if value is None or pd.isna(value):
                new_columns.append(
                    f"column_{index}"
                )

            else:
                column_name = normalize_column_name(
                    value
                )

                new_columns.append(
                    column_name
                    if column_name
                    else f"column_{index}"
                )

        repaired = df.iloc[1:].copy()

        repaired.columns = new_columns

    else:

        repaired = df.copy()

        repaired.columns = current_columns

    return (
        repaired
        .dropna(how="all")
        .reset_index(drop=True)
    )


def find_column(
    df: pd.DataFrame,
    candidates: list[str],
) -> Optional[str]:
    """Return the first available candidate column."""

    normalized_map = {
        normalize_column_name(column): column
        for column in df.columns
    }

    for candidate in candidates:

        normalized_candidate = normalize_column_name(
            candidate
        )

        if normalized_candidate in normalized_map:
            return normalized_map[
                normalized_candidate
            ]

    return None


# ============================================================
# ANALYSIS FILE LOADER
# ============================================================

def load_analysis() -> pd.DataFrame:
    """
    Load analysis.xlsx.

    Core project files use header=1 because the first row
    contains dataset metadata.
    """

    if not ANALYSIS_PATH.exists():

        raise FileNotFoundError(
            f"analysis.xlsx was not found: {ANALYSIS_PATH}"
        )

    analysis = pd.read_excel(
        ANALYSIS_PATH,
        header=1,
    )

    analysis.columns = [
        normalize_column_name(column)
        for column in analysis.columns
    ]

    return analysis


# ============================================================
# DATABASE LOADERS
# ============================================================

def load_database_table(
    table_name: str,
) -> pd.DataFrame:
    """Load a SQLite table."""

    if not DB_PATH.exists():

        raise FileNotFoundError(
            f"Database was not found: {DB_PATH}"
        )

    with sqlite3.connect(
        DB_PATH
    ) as connection:

        return pd.read_sql_query(
            f'SELECT * FROM "{table_name}"',
            connection,
        )


def load_profit_and_loss() -> pd.DataFrame:
    """Load and repair the historical P&L table."""

    raw = load_database_table(
        "profitandloss"
    )

    return repair_embedded_header(
        raw
    )


def load_stock_prices() -> pd.DataFrame:
    """Load historical stock-price data."""

    return load_database_table(
        "stock_prices"
    )


# ============================================================
# TEXT PARSING
# ============================================================

def parse_metric_text(
    company_id: str,
    metric_type: str,
    raw_text,
) -> tuple[list[dict], Optional[dict]]:
    """
    Parse a metric text field.

    Returns:
        parsed records
        optional failure record
    """

    parsed_records = []

    if raw_text is None or pd.isna(raw_text):

        return (
            parsed_records,
            {
                "company_id": company_id,
                "metric_type": metric_type,
                "raw_text": "",
                "failure_reason": "Missing text",
            },
        )

    text = str(
        raw_text
    ).strip()

    if not text:

        return (
            parsed_records,
            {
                "company_id": company_id,
                "metric_type": metric_type,
                "raw_text": "",
                "failure_reason": "Empty text",
            },
        )

    # --------------------------------------------------------
    # Numeric periods such as 10 Years, 5 Years, 1 Year
    # --------------------------------------------------------

    cagr_matches = CAGR_PATTERN.findall(
        text
    )

    for period, value in cagr_matches:

        parsed_records.append(
            {
                "company_id": company_id,
                "metric_type": metric_type,
                "period_years": int(period),
                "period_label": f"{int(period)} Year",
                "value_pct": float(value),
                "raw_text": text,
            }
        )

    # --------------------------------------------------------
    # TTM values
    # --------------------------------------------------------

    ttm_matches = TTM_PATTERN.findall(
        text
    )

    for value in ttm_matches:

        parsed_records.append(
            {
                "company_id": company_id,
                "metric_type": metric_type,
                "period_years": 0,
                "period_label": "TTM",
                "value_pct": float(value),
                "raw_text": text,
            }
        )

    # --------------------------------------------------------
    # Last-year values
    # --------------------------------------------------------

    last_year_matches = LAST_YEAR_PATTERN.findall(
        text
    )

    for value in last_year_matches:

        parsed_records.append(
            {
                "company_id": company_id,
                "metric_type": metric_type,
                "period_years": 1,
                "period_label": "Last Year",
                "value_pct": float(value),
                "raw_text": text,
            }
        )

    if not parsed_records:

        return (
            [],
            {
                "company_id": company_id,
                "metric_type": metric_type,
                "raw_text": text,
                "failure_reason": "Regex pattern not matched",
            },
        )

    return parsed_records, None


# ============================================================
# P&L CAGR CALCULATION
# ============================================================

def prepare_profit_and_loss() -> pd.DataFrame:
    """Prepare historical revenue and profit records."""

    pnl = load_profit_and_loss()

    company_column = find_column(
        pnl,
        [
            "company_id",
            "ticker",
            "symbol",
        ],
    )

    year_column = find_column(
        pnl,
        [
            "year",
            "financial_year",
            "fiscal_year",
        ],
    )

    sales_column = find_column(
        pnl,
        [
            "sales",
            "revenue",
            "total_revenue",
        ],
    )

    profit_column = find_column(
        pnl,
        [
            "net_profit",
            "profit_after_tax",
            "pat",
        ],
    )

    if (
        company_column is None
        or year_column is None
    ):

        return pd.DataFrame()

    pnl = pnl.copy()

    pnl["company_id"] = (
        pnl[company_column]
        .apply(
            normalize_company_id
        )
    )

    pnl["year_numeric"] = (
        pnl[year_column]
        .apply(
            extract_year
        )
    )

    if sales_column is not None:

        pnl["sales_numeric"] = (
            pnl[sales_column]
            .apply(
                safe_numeric
            )
        )

    else:

        pnl["sales_numeric"] = np.nan

    if profit_column is not None:

        pnl["profit_numeric"] = (
            pnl[profit_column]
            .apply(
                safe_numeric
            )
        )

    else:

        pnl["profit_numeric"] = np.nan

    pnl = pnl[
        (
            pnl["company_id"] != ""
        )
        &
        (
            pnl["year_numeric"].notna()
        )
    ].copy()

    pnl["year_numeric"] = (
        pnl["year_numeric"]
        .astype(int)
    )

    pnl["_complete"] = (
        pnl[
            [
                "sales_numeric",
                "profit_numeric",
            ]
        ]
        .notna()
        .sum(axis=1)
    )

    pnl = (
        pnl
        .sort_values(
            [
                "company_id",
                "year_numeric",
                "_complete",
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
        .reset_index(drop=True)
    )

    return pnl


def compute_historical_cagr(
    pnl: pd.DataFrame,
    company_id: str,
    period_years: int,
    value_column: str,
) -> tuple[float, str]:
    """
    Calculate revenue or profit CAGR for a company.

    Uses the latest available year and the closest available
    historical year at or before the requested start year.
    """

    if (
        pnl.empty
        or period_years <= 0
        or value_column not in pnl.columns
    ):

        return np.nan, "Not available"

    company_history = pnl[
        pnl["company_id"] == company_id
    ].copy()

    company_history = company_history[
        company_history[value_column].notna()
    ].sort_values(
        "year_numeric"
    )

    if len(company_history) < 2:

        return np.nan, "Insufficient history"

    end_row = company_history.iloc[-1]

    end_year = int(
        end_row["year_numeric"]
    )

    target_start_year = (
        end_year - period_years
    )

    start_candidates = company_history[
        company_history["year_numeric"]
        <= target_start_year
    ]

    if start_candidates.empty:

        return np.nan, "Insufficient period coverage"

    start_row = start_candidates.iloc[-1]

    actual_years = int(
        end_row["year_numeric"]
        - start_row["year_numeric"]
    )

    start_value = safe_numeric(
        start_row[value_column]
    )

    end_value = safe_numeric(
        end_row[value_column]
    )

    if (
        pd.notna(start_value)
        and start_value <= 0
    ):

        return np.nan, "TURNAROUND"

    computed = calculate_cagr(
        start_value,
        end_value,
        actual_years,
    )

    if pd.isna(computed):

        return np.nan, "Not calculable"

    return round(
        float(computed),
        4,
    ), "Calculated"


# ============================================================
# STOCK-PRICE CAGR CALCULATION
# ============================================================

def prepare_stock_prices() -> pd.DataFrame:
    """Prepare the historical stock-price dataset."""

    stock = load_stock_prices()

    if stock.empty:
        return stock

    company_column = find_column(
        stock,
        [
            "company_id",
            "ticker",
            "symbol",
        ],
    )

    date_column = find_column(
        stock,
        [
            "date",
            "price_date",
        ],
    )

    price_column = find_column(
        stock,
        [
            "adjusted_close",
            "close_price",
            "close",
        ],
    )

    if (
        company_column is None
        or date_column is None
        or price_column is None
    ):

        return pd.DataFrame()

    stock = stock.copy()

    stock["company_id"] = (
        stock[company_column]
        .apply(
            normalize_company_id
        )
    )

    stock["date_numeric"] = pd.to_datetime(
        stock[date_column],
        errors="coerce",
    )

    stock["price_numeric"] = (
        stock[price_column]
        .apply(
            safe_numeric
        )
    )

    stock = stock[
        (
            stock["company_id"] != ""
        )
        &
        (
            stock["date_numeric"].notna()
        )
        &
        (
            stock["price_numeric"].notna()
        )
        &
        (
            stock["price_numeric"] > 0
        )
    ].copy()

    return (
        stock
        .sort_values(
            [
                "company_id",
                "date_numeric",
            ]
        )
        .reset_index(drop=True)
    )


def compute_stock_price_cagr(
    stock: pd.DataFrame,
    company_id: str,
    period_years: int,
) -> tuple[float, str]:
    """Calculate stock-price CAGR using adjusted close prices."""

    if stock.empty or period_years <= 0:

        return np.nan, "Not available"

    history = stock[
        stock["company_id"] == company_id
    ].copy()

    if len(history) < 2:

        return np.nan, "Insufficient history"

    history = history.sort_values(
        "date_numeric"
    )

    end_row = history.iloc[-1]

    end_date = end_row[
        "date_numeric"
    ]

    target_start_date = (
        end_date
        - pd.DateOffset(
            years=period_years
        )
    )

    start_candidates = history[
        history["date_numeric"]
        <= target_start_date
    ]

    if start_candidates.empty:

        return np.nan, "Insufficient period coverage"

    start_row = start_candidates.iloc[-1]

    actual_days = (
        end_date
        - start_row["date_numeric"]
    ).days

    actual_years = (
        actual_days / 365.25
    )

    calculated = calculate_cagr(
        start_row["price_numeric"],
        end_row["price_numeric"],
        actual_years,
    )

    if pd.isna(calculated):

        return np.nan, "Not calculable"

    return round(
        float(calculated),
        4,
    ), "Calculated"


# ============================================================
# CROSS-VALIDATION
# ============================================================

def cross_validate_parsed_data(
    parsed_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Cross-validate parsed CAGR values against calculated values.

    Manual review is required when absolute divergence is
    greater than 5 percentage points.
    """

    if parsed_df.empty:
        return parsed_df

    pnl = prepare_profit_and_loss()

    stock = prepare_stock_prices()

    validated_records = []

    for _, row in parsed_df.iterrows():

        record = row.to_dict()

        company_id = record[
            "company_id"
        ]

        metric_type = record[
            "metric_type"
        ]

        period_years = int(
            record[
                "period_years"
            ]
        )

        parsed_value = safe_numeric(
            record[
                "value_pct"
            ]
        )

        calculated_value = np.nan

        calculation_status = (
            "Validation not applicable"
        )

        # TTM values cannot be compared with multi-year CAGR.
        if period_years <= 0:

            calculation_status = (
                "TTM validation not applicable"
            )

        elif metric_type == "compounded_sales_growth":

            (
                calculated_value,
                calculation_status,
            ) = compute_historical_cagr(
                pnl=pnl,
                company_id=company_id,
                period_years=period_years,
                value_column="sales_numeric",
            )

        elif metric_type == "compounded_profit_growth":

            (
                calculated_value,
                calculation_status,
            ) = compute_historical_cagr(
                pnl=pnl,
                company_id=company_id,
                period_years=period_years,
                value_column="profit_numeric",
            )

        elif metric_type == "stock_price_cagr":

            (
                calculated_value,
                calculation_status,
            ) = compute_stock_price_cagr(
                stock=stock,
                company_id=company_id,
                period_years=period_years,
            )

        elif metric_type == "roe":

            calculation_status = (
                "ROE is not a CAGR metric"
            )

        if (
            pd.notna(parsed_value)
            and pd.notna(calculated_value)
        ):

            divergence = abs(
                parsed_value
                - calculated_value
            )

        else:

            divergence = np.nan

        manual_review = bool(
            pd.notna(divergence)
            and divergence
            > DIVERGENCE_THRESHOLD
        )

        if manual_review:

            validation_status = (
                "MANUAL REVIEW"
            )

            review_reason = (
                "Parsed value differs from "
                "calculated value by more than "
                f"{DIVERGENCE_THRESHOLD:.1f} percentage points"
            )

        elif pd.notna(divergence):

            validation_status = "MATCH"

            review_reason = ""

        else:

            validation_status = (
                "NOT VALIDATED"
            )

            review_reason = (
                calculation_status
            )

        record[
            "computed_value_pct"
        ] = (
            round(
                float(calculated_value),
                4,
            )
            if pd.notna(calculated_value)
            else np.nan
        )

        record[
            "divergence_pct_points"
        ] = (
            round(
                float(divergence),
                4,
            )
            if pd.notna(divergence)
            else np.nan
        )

        record[
            "calculation_status"
        ] = calculation_status

        record[
            "manual_review_flag"
        ] = manual_review

        record[
            "validation_status"
        ] = validation_status

        record[
            "review_reason"
        ] = review_reason

        validated_records.append(
            record
        )

    return pd.DataFrame(
        validated_records
    )


# ============================================================
# MAIN PARSER
# ============================================================

def parse_analysis() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run the complete Day 29 parser and validation pipeline."""

    analysis = load_analysis()

    print("=" * 80)
    print("SPRINT 5 DAY 29 — ANALYSIS TEXT PARSER")
    print("=" * 80)

    print(
        f"\nRows loaded: {len(analysis)}"
    )

    print("\nColumns:")

    print(
        analysis.columns.tolist()
    )

    company_column = find_column(
        analysis,
        [
            "company_id",
            "ticker",
            "id",
        ],
    )

    if company_column is None:

        raise ValueError(
            "Unable to identify company identifier column. "
            f"Available columns: {analysis.columns.tolist()}"
        )

    available_target_fields = [
        field
        for field in TARGET_FIELDS
        if field in analysis.columns
    ]

    missing_target_fields = [
        field
        for field in TARGET_FIELDS
        if field not in analysis.columns
    ]

    print(
        "\nAvailable parser fields:",
        available_target_fields,
    )

    if missing_target_fields:

        print(
            "Missing parser fields:",
            missing_target_fields,
        )

    parsed_records = []

    failure_records = []

    for _, row in analysis.iterrows():

        company_id = normalize_company_id(
            row[company_column]
        )

        if not company_id:
            continue

        for metric_type in available_target_fields:

            (
                parsed,
                failure,
            ) = parse_metric_text(
                company_id=company_id,
                metric_type=metric_type,
                raw_text=row[metric_type],
            )

            parsed_records.extend(
                parsed
            )

            if failure is not None:

                failure_records.append(
                    failure
                )

    parsed_df = pd.DataFrame(
        parsed_records,
        columns=[
            "company_id",
            "metric_type",
            "period_years",
            "period_label",
            "value_pct",
            "raw_text",
        ],
    )

    failures_df = pd.DataFrame(
        failure_records,
        columns=[
            "company_id",
            "metric_type",
            "raw_text",
            "failure_reason",
        ],
    )

    # Cross-validation
    parsed_df = cross_validate_parsed_data(
        parsed_df
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    parsed_df.to_csv(
        PARSED_OUTPUT_PATH,
        index=False,
    )

    failures_df.to_csv(
        FAILURE_OUTPUT_PATH,
        index=False,
    )

    # ========================================================
    # TERMINAL SUMMARY
    # ========================================================

    print("\n" + "=" * 80)
    print("PARSER RESULTS")
    print("=" * 80)

    print(
        f"Parsed records : {len(parsed_df)}"
    )

    print(
        f"Parse failures : {len(failures_df)}"
    )

    manual_review_count = 0

    if (
        not parsed_df.empty
        and "manual_review_flag"
        in parsed_df.columns
    ):

        manual_review_count = int(
            parsed_df[
                "manual_review_flag"
            ].fillna(False).sum()
        )

    print(
        "Manual-review divergences: "
        f"{manual_review_count}"
    )

    if not parsed_df.empty:

        print(
            "\nParsed metric distribution:"
        )

        print(
            parsed_df[
                "metric_type"
            ]
            .value_counts()
            .to_string()
        )

        print(
            "\nPeriod distribution:"
        )

        print(
            parsed_df[
                "period_label"
            ]
            .value_counts()
            .to_string()
        )

        print(
            "\nValidation-status distribution:"
        )

        print(
            parsed_df[
                "validation_status"
            ]
            .value_counts()
            .to_string()
        )

        print(
            "\nSample parsed records:"
        )

        sample_columns = [
            "company_id",
            "metric_type",
            "period_years",
            "period_label",
            "value_pct",
            "computed_value_pct",
            "divergence_pct_points",
            "validation_status",
        ]

        print(
            parsed_df[
                sample_columns
            ]
            .head(15)
            .to_string(
                index=False
            )
        )

        manual_review_rows = parsed_df[
            parsed_df[
                "manual_review_flag"
            ] == True
        ]

        if not manual_review_rows.empty:

            print(
                "\nRows requiring manual review:"
            )

            print(
                manual_review_rows[
                    [
                        "company_id",
                        "metric_type",
                        "period_years",
                        "value_pct",
                        "computed_value_pct",
                        "divergence_pct_points",
                        "review_reason",
                    ]
                ]
                .head(20)
                .to_string(
                    index=False
                )
            )

    if not failures_df.empty:

        print(
            "\nSample parse failures:"
        )

        print(
            failures_df
            .head(10)
            .to_string(
                index=False
            )
        )

    print(
        f"\nParsed output:"
        f"\n{PARSED_OUTPUT_PATH}"
    )

    print(
        f"\nFailure log:"
        f"\n{FAILURE_OUTPUT_PATH}"
    )

    print("=" * 80)

    return parsed_df, failures_df


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    parse_analysis()