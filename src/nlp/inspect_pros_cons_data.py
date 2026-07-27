"""
Sprint 5 — Day 30

Inspect all database tables and columns required by the
Auto Pros/Cons Generator.

This is a development/diagnostic utility only.
"""

from pathlib import Path
import sqlite3

import pandas as pd


# ============================================================
# PATH CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = (
    PROJECT_ROOT
    / "db"
    / "nifty100.db"
)


# ============================================================
# RULE REQUIREMENTS
# ============================================================

RULE_REQUIREMENTS = {
    "ROE": [
        "roe",
        "return_on_equity",
        "return_on_equity_pct",
    ],

    "ROCE": [
        "roce",
        "return_on_capital_employed",
        "roce_percentage",
    ],

    "Debt / Equity": [
        "debt_to_equity",
        "de_ratio",
    ],

    "Free Cash Flow": [
        "free_cash_flow",
        "free_cash_flow_cr",
        "fcf",
    ],

    "Revenue / Sales": [
        "revenue",
        "sales",
        "total_revenue",
    ],

    "Net Profit / PAT": [
        "net_profit",
        "pat",
        "profit_after_tax",
    ],

    "Operating Margin": [
        "operating_profit_margin_pct",
        "opm",
        "operating_margin",
    ],

    "Interest Coverage": [
        "interest_coverage",
        "icr",
    ],

    "Dividend Yield": [
        "dividend_yield_pct",
        "dividend_yield",
    ],

    "Dividend Payout": [
        "dividend_payout_ratio_pct",
        "dividend_payout",
    ],

    "EPS": [
        "earnings_per_share",
        "eps",
    ],

    "Assets": [
        "total_assets",
        "assets",
    ],

    "Debt / Borrowings": [
        "total_debt_cr",
        "borrowings",
        "total_debt",
    ],

    "EBITDA": [
        "ebitda",
        "ebitda_cr",
    ],
}


# ============================================================
# HELPERS
# ============================================================

def normalize(value):
    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )


def get_tables(connection):
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()

    return [
        row[0]
        for row in rows
    ]


def get_columns(connection, table_name):
    rows = connection.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return [
        row[1]
        for row in rows
    ]


# ============================================================
# INSPECTION
# ============================================================

def inspect_rule_data():
    print("=" * 100)
    print("SPRINT 5 — DAY 30 PROS/CONS DATA INSPECTION")
    print("=" * 100)

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    connection = sqlite3.connect(
        DB_PATH
    )

    tables = get_tables(
        connection
    )

    print("\nDATABASE TABLES")
    print("-" * 100)

    for table in tables:
        print(table)

    # --------------------------------------------------------
    # Build column map
    # --------------------------------------------------------

    table_columns = {}

    for table in tables:
        table_columns[table] = get_columns(
            connection,
            table,
        )

    # --------------------------------------------------------
    # Print schemas for important tables
    # --------------------------------------------------------

    important_tables = [
        "companies",
        "financial_ratios",
        "market_cap",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "stock_prices",
        "sectors",
    ]

    print("\n" + "=" * 100)
    print("IMPORTANT TABLE SCHEMAS")
    print("=" * 100)

    for table in important_tables:

        if table not in tables:
            print(
                f"\n{table.upper()}: TABLE NOT FOUND"
            )
            continue

        print("\n" + table.upper())
        print("-" * 100)

        for column in table_columns[table]:
            print(column)

    # --------------------------------------------------------
    # Search database for rule inputs
    # --------------------------------------------------------

    print("\n" + "=" * 100)
    print("RULE INPUT SEARCH")
    print("=" * 100)

    for requirement, candidates in RULE_REQUIREMENTS.items():

        print(
            f"\n{requirement}"
        )

        print("-" * 100)

        matches = []

        for table, columns in table_columns.items():

            for column in columns:

                normalized_column = normalize(
                    column
                )

                for candidate in candidates:

                    normalized_candidate = normalize(
                        candidate
                    )

                    if (
                        normalized_candidate
                        == normalized_column
                        or normalized_candidate
                        in normalized_column
                    ):

                        matches.append(
                            (
                                table,
                                column,
                            )
                        )

        if matches:

            seen = set()

            for table, column in matches:

                key = (
                    table,
                    column,
                )

                if key in seen:
                    continue

                seen.add(
                    key
                )

                print(
                    f"FOUND: {table}.{column}"
                )

        else:

            print(
                "NOT FOUND AS DIRECT DATABASE COLUMN"
            )

    # --------------------------------------------------------
    # Financial ratios sample
    # --------------------------------------------------------

    if "financial_ratios" in tables:

        print("\n" + "=" * 100)
        print("FINANCIAL RATIOS SAMPLE")
        print("=" * 100)

        ratios = pd.read_sql_query(
            """
            SELECT *
            FROM financial_ratios
            LIMIT 5
            """,
            connection,
        )

        print(
            ratios.to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # P&L raw sample
    # --------------------------------------------------------

    if "profitandloss" in tables:

        print("\n" + "=" * 100)
        print("PROFIT & LOSS RAW SAMPLE")
        print("=" * 100)

        pnl = pd.read_sql_query(
            """
            SELECT *
            FROM profitandloss
            LIMIT 5
            """,
            connection,
        )

        print(
            pnl.to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # Balance sheet raw sample
    # --------------------------------------------------------

    if "balancesheet" in tables:

        print("\n" + "=" * 100)
        print("BALANCE SHEET RAW SAMPLE")
        print("=" * 100)

        balance = pd.read_sql_query(
            """
            SELECT *
            FROM balancesheet
            LIMIT 5
            """,
            connection,
        )

        print(
            balance.to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # Cash-flow raw sample
    # --------------------------------------------------------

    if "cashflow" in tables:

        print("\n" + "=" * 100)
        print("CASH FLOW RAW SAMPLE")
        print("=" * 100)

        cashflow = pd.read_sql_query(
            """
            SELECT *
            FROM cashflow
            LIMIT 5
            """,
            connection,
        )

        print(
            cashflow.to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # Analysis parser output
    # --------------------------------------------------------

    parsed_path = (
        PROJECT_ROOT
        / "output"
        / "analysis_parsed.csv"
    )

    print("\n" + "=" * 100)
    print("DAY 29 PARSER OUTPUT")
    print("=" * 100)

    if parsed_path.exists():

        parsed = pd.read_csv(
            parsed_path
        )

        print(
            f"Rows: {len(parsed)}"
        )

        print(
            f"Companies: "
            f"{parsed['company_id'].nunique()}"
        )

        print("\nColumns:")

        print(
            parsed.columns.tolist()
        )

        print("\nMetric distribution:")

        print(
            parsed[
                "metric_type"
            ]
            .value_counts()
            .to_string()
        )

    else:

        print(
            "analysis_parsed.csv not found."
        )

    connection.close()

    print("\n" + "=" * 100)
    print("DAY 30 DATA INSPECTION COMPLETE")
    print("=" * 100)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    inspect_rule_data()