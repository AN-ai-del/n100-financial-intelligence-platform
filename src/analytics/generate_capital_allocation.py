"""
Generate Capital Allocation CSV

Uses the Sprint 2 cash-flow KPI engine to classify each
company-year according to CFO / CFI / CFF patterns.

Output:
    output/capital_allocation.csv
"""

from pathlib import Path
import re
import sqlite3

import numpy as np
import pandas as pd

from src.analytics.cashflow_kpis import (
    build_capital_allocation_record,
    calculate_cfo_quality_score,
)


# =========================================================
# Paths
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "db" / "nifty100.db"

OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_FILE = (
    OUTPUT_DIR
    / "capital_allocation.csv"
)


# =========================================================
# Helpers
# =========================================================

def normalize_column_name(value):
    """Convert column names into predictable snake_case."""
    value = str(value).strip().lower()

    value = re.sub(
        r"[^\w]+",
        "_",
        value,
    )

    return value.strip("_")


def repair_header_table(df):
    """
    Some project tables were imported with metadata as the
    SQLite column names and the real headers in row zero.

    Promote row zero when necessary.
    """

    if df.empty:
        return df

    current_columns = [
        str(column).lower()
        for column in df.columns
    ]

    malformed = any(
        column.startswith("unnamed")
        for column in current_columns
    )

    # First column also contains source metadata in malformed tables.
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

        for index, value in enumerate(first_row):

            if pd.isna(value):
                new_columns.append(
                    f"column_{index}"
                )
            else:
                name = normalize_column_name(
                    value
                )

                new_columns.append(
                    name
                    if name
                    else f"column_{index}"
                )

        output = df.iloc[1:].copy()

        output.columns = new_columns

    else:

        output = df.copy()

        output.columns = [
            normalize_column_name(
                column
            )
            for column in output.columns
        ]

    return (
        output
        .dropna(how="all")
        .reset_index(drop=True)
    )


def find_column(df, candidates):
    """Find the first available candidate column."""

    for candidate in candidates:
        if candidate in df.columns:
            return candidate

    return None


def normalize_company_id(value):
    """Standard company ID normalization."""

    if value is None or pd.isna(value):
        return ""

    return (
        str(value)
        .strip()
        .upper()
    )


def extract_year(value):
    """
    Convert values such as:
        Mar 2024
        Dec 2012
        2024
    into integer year.
    """

    if value is None or pd.isna(value):
        return np.nan

    match = re.search(
        r"(19|20)\d{2}",
        str(value),
    )

    if not match:
        return np.nan

    return int(
        match.group()
    )


def numeric(value):
    """Safely convert raw values to floats."""

    if value is None or pd.isna(value):
        return np.nan

    text = (
        str(value)
        .replace(",", "")
        .replace("₹", "")
        .replace("%", "")
        .strip()
    )

    try:
        return float(text)

    except (
        TypeError,
        ValueError,
    ):
        return np.nan


# =========================================================
# Database Loading
# =========================================================

def read_table(
    connection,
    table_name,
):

    return pd.read_sql_query(
        f"SELECT * FROM {table_name}",
        connection,
    )


# =========================================================
# Main Generator
# =========================================================

def generate_capital_allocation():

    print(
        "=" * 70
    )

    print(
        "CAPITAL ALLOCATION GENERATOR"
    )

    print(
        "=" * 70
    )


    if not DB_PATH.exists():

        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )


    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    connection = sqlite3.connect(
        DB_PATH
    )


    try:

        cashflow_raw = read_table(
            connection,
            "cashflow",
        )

        pnl_raw = read_table(
            connection,
            "profitandloss",
        )

        companies_raw = read_table(
            connection,
            "companies",
        )

    finally:

        connection.close()


    # =====================================================
    # Repair source tables
    # =====================================================

    cashflow = repair_header_table(
        cashflow_raw
    )

    pnl = repair_header_table(
        pnl_raw
    )

    companies = repair_header_table(
        companies_raw
    )


    print(
        f"Cashflow rows: {len(cashflow)}"
    )

    print(
        f"P&L rows: {len(pnl)}"
    )


    # =====================================================
    # Detect Cash Flow Columns
    # =====================================================

    cf_company_col = find_column(
        cashflow,
        [
            "company_id",
            "ticker",
            "symbol",
            "company",
        ],
    )


    cf_year_col = find_column(
        cashflow,
        [
            "year",
            "financial_year",
            "fiscal_year",
        ],
    )


    cfo_col = find_column(
        cashflow,
        [
            "operating_activity",
            "operating_cash_flow",
            "cash_from_operating_activity",
            "cash_flow_from_operating_activity",
            "cfo",
            "cash_from_operations",
        ],
    )


    cfi_col = find_column(
        cashflow,
        [
            "investing_activity",
            "investing_cash_flow",
            "cash_from_investing_activity",
            "cash_flow_from_investing_activity",
            "cfi",
        ],
    )


    cff_col = find_column(
        cashflow,
        [
            "financing_activity",
            "financing_cash_flow",
            "cash_from_financing_activity",
            "cash_flow_from_financing_activity",
            "cff",
        ],
    )


    required = {
        "company": cf_company_col,
        "year": cf_year_col,
        "CFO": cfo_col,
        "CFI": cfi_col,
        "CFF": cff_col,
    }


    missing = [
        key
        for key, value
        in required.items()
        if value is None
    ]


    if missing:

        print(
            "\nCashflow columns:"
        )

        print(
            cashflow.columns.tolist()
        )

        raise ValueError(
            "Unable to identify required "
            "cashflow columns: "
            + ", ".join(missing)
        )


    print(
        "\nDetected cashflow columns:"
    )

    print(
        f"Company : {cf_company_col}"
    )

    print(
        f"Year    : {cf_year_col}"
    )

    print(
        f"CFO     : {cfo_col}"
    )

    print(
        f"CFI     : {cfi_col}"
    )

    print(
        f"CFF     : {cff_col}"
    )


    # =====================================================
    # Clean Cashflow
    # =====================================================

    cashflow[
        "company_id"
    ] = (
        cashflow[
            cf_company_col
        ]
        .apply(
            normalize_company_id
        )
    )


    cashflow[
        "year_numeric"
    ] = (
        cashflow[
            cf_year_col
        ]
        .apply(
            extract_year
        )
    )


    for source, target in [
        (cfo_col, "cfo"),
        (cfi_col, "cfi"),
        (cff_col, "cff"),
    ]:

        cashflow[
            target
        ] = (
            cashflow[source]
            .apply(numeric)
        )


    cashflow = cashflow[
        (
            cashflow[
                "company_id"
            ] != ""
        )
        &
        (
            cashflow[
                "year_numeric"
            ].notna()
        )
    ].copy()


    cashflow[
        "year"
    ] = (
        cashflow[
            "year_numeric"
        ]
        .astype(int)
    )


    # Keep best duplicate if any exist.

    cashflow[
        "_complete"
    ] = (
        cashflow[
            [
                "cfo",
                "cfi",
                "cff",
            ]
        ]
        .notna()
        .sum(axis=1)
    )


    cashflow = (
        cashflow
        .sort_values(
            "_complete",
            ascending=False,
        )
        .drop_duplicates(
            [
                "company_id",
                "year",
            ],
            keep="first",
        )
    )


    # =====================================================
    # Restrict to official company universe
    # =====================================================

    company_master_col = find_column(
        companies,
        [
            "id",
            "company_id",
            "ticker",
        ],
    )


    official_company_ids = set()


    if company_master_col:

        official_company_ids = set(
            companies[
                company_master_col
            ]
            .dropna()
            .apply(
                normalize_company_id
            )
            .tolist()
        )


    if official_company_ids:

        cashflow = cashflow[
            cashflow[
                "company_id"
            ].isin(
                official_company_ids
            )
        ].copy()


    # =====================================================
    # Prepare PAT for CFO Quality
    # =====================================================

    pnl_company_col = find_column(
        pnl,
        [
            "company_id",
            "ticker",
            "symbol",
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


    pat_col = find_column(
        pnl,
        [
            "net_profit",
            "profit_after_tax",
            "pat",
        ],
    )


    if (
        pnl_company_col
        and pnl_year_col
        and pat_col
    ):

        pnl[
            "company_id"
        ] = (
            pnl[
                pnl_company_col
            ]
            .apply(
                normalize_company_id
            )
        )


        pnl[
            "year"
        ] = (
            pnl[
                pnl_year_col
            ]
            .apply(
                extract_year
            )
        )


        pnl[
            "pat"
        ] = (
            pnl[
                pat_col
            ]
            .apply(
                numeric
            )
        )


        pnl = pnl[
            (
                pnl[
                    "company_id"
                ] != ""
            )
            &
            (
                pnl[
                    "year"
                ].notna()
            )
        ].copy()


        pnl[
            "year"
        ] = (
            pnl[
                "year"
            ]
            .astype(int)
        )


        pnl = (
            pnl[
                [
                    "company_id",
                    "year",
                    "pat",
                ]
            ]
            .drop_duplicates(
                [
                    "company_id",
                    "year",
                ],
                keep="last",
            )
        )


        cashflow = (
            cashflow.merge(
                pnl,
                on=[
                    "company_id",
                    "year",
                ],
                how="left",
            )
        )

    else:

        print(
            "\nPAT column could not be "
            "identified. CFO quality will "
            "be NOT_AVAILABLE."
        )

        cashflow[
            "pat"
        ] = np.nan


    # =====================================================
    # Build Classification Records
    # =====================================================

    records = []


    for _, row in cashflow.iterrows():

        cfo = row[
            "cfo"
        ]

        cfi = row[
            "cfi"
        ]

        cff = row[
            "cff"
        ]

        pat = row[
            "pat"
        ]


        if (
            pd.isna(cfo)
            or pd.isna(cfi)
            or pd.isna(cff)
        ):
            continue


        # -----------------------------------------------
        # CFO Quality
        # -----------------------------------------------

        if pd.notna(pat):

            (
                cfo_quality_score,
                cfo_quality_label,
            ) = calculate_cfo_quality_score(
                cfo,
                pat,
            )

        else:

            cfo_quality_score = None

            cfo_quality_label = (
                "NOT_AVAILABLE"
            )


        # -----------------------------------------------
        # Existing Sprint 2 classifier
        # -----------------------------------------------

        record = (
            build_capital_allocation_record(
                company_id=row[
                    "company_id"
                ],
                year=int(
                    row[
                        "year"
                    ]
                ),
                cfo=cfo,
                cfi=cfi,
                cff=cff,
                cfo_quality_label=(
                    cfo_quality_label
                ),
            )
        )


        record[
            "cfo"
        ] = cfo

        record[
            "cfi"
        ] = cfi

        record[
            "cff"
        ] = cff

        record[
            "pat"
        ] = pat

        record[
            "cfo_quality_score"
        ] = cfo_quality_score

        record[
            "cfo_quality_label"
        ] = cfo_quality_label


        records.append(
            record
        )


    # =====================================================
    # Output
    # =====================================================

    result = pd.DataFrame(
        records
    )
    
    # =====================================================
    # Ensure full 92-company coverage
    # =====================================================

    if official_company_ids:

        generated_ids = set(
            result["company_id"]
            .dropna()
            .astype(str)
            .str.strip()
            .str.upper()
        )

        missing_ids = sorted(
            official_company_ids - generated_ids
        )

        if missing_ids:

            print(
                "\nCompanies missing cash-flow data:"
            )

            print(
                missing_ids
            )

            fallback_rows = []

            for company_id in missing_ids:

                fallback_rows.append(
                    {
                        "company_id": company_id,
                        "year": pd.NA,
                        "cfo": pd.NA,
                        "cfi": pd.NA,
                        "cff": pd.NA,
                        "pat": pd.NA,
                        "cfo_quality_score": pd.NA,
                        "cfo_quality_label": "NOT_AVAILABLE",
                        "cfo_sign": "N/A",
                        "cfi_sign": "N/A",
                        "cff_sign": "N/A",
                        "pattern_label": "Other",
                        "data_status": "Cash-flow data unavailable",
                    }
                )

            fallback_df = pd.DataFrame(
                fallback_rows
            )

            if "data_status" not in result.columns:
                result["data_status"] = "Available"

            result = pd.concat(
                [
                    result,
                    fallback_df,
                ],
                ignore_index=True,
            )

    else:

        result["data_status"] = "Available"


    if result.empty:

        raise RuntimeError(
            "No capital-allocation "
            "records could be generated."
        )


    result = result[
        [
            "company_id",
            "year",
            "cfo",
            "cfi",
            "cff",
            "pat",
            "cfo_quality_score",
            "cfo_quality_label",
            "cfo_sign",
            "cfi_sign",
            "cff_sign",
            "pattern_label",
            "data_status",
        ]
    ]


    result = result.sort_values(
        [
            "company_id",
            "year",
        ],
        na_position="last"
    )


    result.to_csv(
        OUTPUT_FILE,
        index=False,
    )


    # =====================================================
    # Validation
    # =====================================================

    latest_year = int(
        result[
            "year"
        ].max()
    )


    latest = result[
        result[
            "year"
        ] == latest_year
    ]


    print(
        "\n"
        + "=" * 70
    )

    print(
        "GENERATION COMPLETE"
    )

    print(
        "=" * 70
    )


    print(
        f"Total rows: {len(result)}"
    )


    print(
        "Companies represented: "
        f"{result['company_id'].nunique()}"
    )


    print(
        f"Latest year: {latest_year}"
    )


    print(
        "Companies in latest year: "
        f"{latest['company_id'].nunique()}"
    )


    print(
        "\nLatest-year pattern distribution:"
    )


    print(
        latest[
            "pattern_label"
        ]
        .value_counts()
        .to_string()
    )


    print(
        f"\nSaved to: {OUTPUT_FILE}"
    )


    return result


# =========================================================
# Entry Point
# =========================================================

if __name__ == "__main__":

    generate_capital_allocation()