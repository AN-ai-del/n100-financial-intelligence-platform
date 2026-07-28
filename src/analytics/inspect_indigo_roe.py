"""
Sprint 6 — Day 36
INDIGO ROE anomaly inspection.

Checks:
- companies master ROE
- financial_ratios ROE history
- P&L net profit
- balance-sheet equity
- independently calculated ROE
"""

from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"

TICKER = "INDIGO"


def repair_embedded_header(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Promote the first data row to headers when required."""

    if df.empty:
        return df.copy()

    first_row = df.iloc[0]

    values = [
        str(value).strip().lower()
        if pd.notna(value)
        else ""
        for value in first_row
    ]

    if (
        "company_id" in values
        and "year" in values
    ):
        repaired = df.iloc[1:].copy()

        repaired.columns = [
            str(value).strip()
            if pd.notna(value)
            else f"column_{index}"
            for index, value in enumerate(first_row)
        ]

        return repaired.reset_index(drop=True)

    return df.copy()


def to_numeric(
    series: pd.Series,
) -> pd.Series:
    """Convert financial values to numeric."""

    return pd.to_numeric(
        series.astype(str).str.replace(
            ",",
            "",
            regex=False,
        ),
        errors="coerce",
    )


def main() -> None:
    """Inspect INDIGO ROE across project sources."""

    with sqlite3.connect(DB_PATH) as connection:

        companies = pd.read_sql_query(
            """
            SELECT *
            FROM companies
            WHERE id = ?
            """,
            connection,
            params=[TICKER],
        )

        ratios = pd.read_sql_query(
            """
            SELECT *
            FROM financial_ratios
            WHERE company_id = ?
            ORDER BY year
            """,
            connection,
            params=[TICKER],
        )

        pnl = pd.read_sql_query(
            "SELECT * FROM profitandloss",
            connection,
        )

        balance = pd.read_sql_query(
            "SELECT * FROM balancesheet",
            connection,
        )

    pnl = repair_embedded_header(pnl)
    balance = repair_embedded_header(balance)

    pnl = pnl[
        pnl["company_id"] == TICKER
    ].copy()

    balance = balance[
        balance["company_id"] == TICKER
    ].copy()

    # ========================================================
    # COMPANY MASTER
    # ========================================================

    print("=" * 100)
    print("1. INDIGO COMPANY MASTER")
    print("=" * 100)

    if companies.empty:
        print("No company master record found.")
    else:
        columns = [
            "id",
            "company_name",
            "roce_percentage",
            "roe_percentage",
            "book_value",
        ]

        print(
            companies[
                columns
            ].to_string(
                index=False
            )
        )

    # ========================================================
    # FINANCIAL RATIOS
    # ========================================================

    print("\n" + "=" * 100)
    print("2. INDIGO FINANCIAL RATIO HISTORY")
    print("=" * 100)

    ratio_columns = [
        "company_id",
        "year",
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "debt_to_equity",
        "book_value_per_share",
        "earnings_per_share",
    ]

    print(
        ratios[
            ratio_columns
        ].to_string(
            index=False
        )
    )

    # ========================================================
    # P&L
    # ========================================================

    print("\n" + "=" * 100)
    print("3. INDIGO P&L")
    print("=" * 100)

    for column in [
        "sales",
        "operating_profit",
        "net_profit",
        "eps",
    ]:
        pnl[column] = to_numeric(
            pnl[column]
        )

    pnl_columns = [
        "company_id",
        "year",
        "sales",
        "operating_profit",
        "net_profit",
        "eps",
    ]

    print(
        pnl[
            pnl_columns
        ].to_string(
            index=False
        )
    )

    # ========================================================
    # BALANCE SHEET
    # ========================================================

    print("\n" + "=" * 100)
    print("4. INDIGO BALANCE SHEET")
    print("=" * 100)

    for column in [
        "equity_capital",
        "reserves",
        "borrowings",
        "total_liabilities",
        "total_assets",
    ]:
        balance[column] = to_numeric(
            balance[column]
        )

    balance[
        "shareholders_equity"
    ] = (
        balance["equity_capital"]
        + balance["reserves"]
    )

    balance_columns = [
        "company_id",
        "year",
        "equity_capital",
        "reserves",
        "shareholders_equity",
        "borrowings",
        "total_liabilities",
        "total_assets",
    ]

    print(
        balance[
            balance_columns
        ].to_string(
            index=False
        )
    )

    # ========================================================
    # INDEPENDENT ROE
    # ========================================================

    print("\n" + "=" * 100)
    print("5. INDEPENDENT ROE CHECK")
    print("=" * 100)

    merged = balance.merge(
        pnl[
            [
                "company_id",
                "year",
                "net_profit",
            ]
        ],
        on=[
            "company_id",
            "year",
        ],
        how="left",
    )

    merged[
        "calculated_roe_pct"
    ] = np.where(
        merged[
            "shareholders_equity"
        ].gt(0),
        (
            merged["net_profit"]
            / merged["shareholders_equity"]
            * 100
        ),
        np.nan,
    )

    print(
        merged[
            [
                "company_id",
                "year",
                "shareholders_equity",
                "net_profit",
                "calculated_roe_pct",
            ]
        ].to_string(
            index=False,
            float_format=lambda value: f"{value:,.2f}",
        )
    )

    print("\n" + "=" * 100)
    print("INDIGO ROE INSPECTION COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()