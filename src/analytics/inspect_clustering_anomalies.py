"""
Sprint 6 — Day 36
Clustering anomaly inspection.

Inspects BEL, HAL and CIPLA across:
- financial_ratios
- profitandloss
- balancesheet

Also recalculates:
- OPM = Operating Profit / Sales * 100
- approximate ROE = Net Profit / (Equity Capital + Reserves) * 100
"""

from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"

COMPANIES = [
    "BEL",
    "HAL",
    "CIPLA",
]


def load_table(
    connection: sqlite3.Connection,
    table_name: str,
) -> pd.DataFrame:
    """Load a database table."""

    return pd.read_sql_query(
        f'SELECT * FROM "{table_name}"',
        connection,
    )


def repair_embedded_header(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Repair tables whose true headers are stored in row 1."""

    if df.empty:
        return df.copy()

    first_row = df.iloc[0]

    first_values = [
        str(value).strip().lower()
        if pd.notna(value)
        else ""
        for value in first_row
    ]

    if (
        "company_id" in first_values
        and "year" in first_values
    ):
        repaired = df.iloc[1:].copy()

        repaired.columns = [
            str(value)
            .strip()
            .lower()
            .replace(" ", "_")
            if pd.notna(value)
            else f"column_{index}"
            for index, value in enumerate(first_row)
        ]

        return repaired.reset_index(drop=True)

    return df.copy()


def safe_numeric(
    series: pd.Series,
) -> pd.Series:
    """Convert a Series to numeric values."""

    return pd.to_numeric(
        series.astype(str).str.replace(
            ",",
            "",
            regex=False,
        ),
        errors="coerce",
    )


def inspect_financial_ratios(
    ratios: pd.DataFrame,
) -> None:
    """Inspect anomalous ratio records."""

    print("\n" + "=" * 100)
    print("1. FINANCIAL RATIOS")
    print("=" * 100)

    selected = ratios[
        ratios["company_id"].isin(COMPANIES)
    ].copy()

    columns = [
        "company_id",
        "year",
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "debt_to_equity",
        "free_cash_flow_cr",
        "earnings_per_share",
        "book_value_per_share",
    ]

    print(
        selected[columns]
        .sort_values(
            [
                "company_id",
                "year",
            ]
        )
        .to_string(index=False)
    )


def inspect_pnl(
    pnl: pd.DataFrame,
) -> pd.DataFrame:
    """Inspect and independently recompute OPM."""

    print("\n" + "=" * 100)
    print("2. PROFIT & LOSS + RECOMPUTED OPM")
    print("=" * 100)

    selected = pnl[
        pnl["company_id"].isin(COMPANIES)
    ].copy()

    for column in [
        "sales",
        "operating_profit",
        "opm_percentage",
        "net_profit",
    ]:
        selected[column] = safe_numeric(
            selected[column]
        )

    selected[
        "recomputed_opm_pct"
    ] = np.where(
        selected["sales"].ne(0),
        (
            selected["operating_profit"]
            / selected["sales"]
            * 100
        ),
        np.nan,
    )

    selected[
        "opm_divergence"
    ] = (
        selected["opm_percentage"]
        - selected["recomputed_opm_pct"]
    ).abs()

    columns = [
        "company_id",
        "year",
        "sales",
        "operating_profit",
        "opm_percentage",
        "recomputed_opm_pct",
        "opm_divergence",
        "net_profit",
    ]

    print(
        selected[columns]
        .sort_values(
            [
                "company_id",
                "year",
            ]
        )
        .to_string(
            index=False,
            float_format=lambda x: f"{x:,.2f}",
        )
    )

    return selected


def inspect_balance_sheet(
    balance: pd.DataFrame,
    pnl: pd.DataFrame,
) -> None:
    """Inspect shareholder equity and independently estimate ROE."""

    print("\n" + "=" * 100)
    print("3. BALANCE SHEET + APPROXIMATE ROE")
    print("=" * 100)

    balance = balance[
        balance["company_id"].isin(
            [
                "BEL",
                "HAL",
            ]
        )
    ].copy()

    pnl = pnl[
        pnl["company_id"].isin(
            [
                "BEL",
                "HAL",
            ]
        )
    ].copy()

    for column in [
        "equity_capital",
        "reserves",
        "borrowings",
        "total_liabilities",
        "total_assets",
    ]:
        balance[column] = safe_numeric(
            balance[column]
        )

    pnl["net_profit"] = safe_numeric(
        pnl["net_profit"]
    )

    balance[
        "shareholders_equity"
    ] = (
        balance["equity_capital"]
        + balance["reserves"]
    )

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
        "approx_roe_pct"
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

    columns = [
        "company_id",
        "year",
        "equity_capital",
        "reserves",
        "shareholders_equity",
        "net_profit",
        "approx_roe_pct",
        "borrowings",
        "total_assets",
    ]

    print(
        merged[columns]
        .sort_values(
            [
                "company_id",
                "year",
            ]
        )
        .to_string(
            index=False,
            float_format=lambda x: f"{x:,.2f}",
        )
    )


def main() -> None:
    """Run the clustering anomaly inspection."""

    print("=" * 100)
    print("SPRINT 6 — DAY 36 CLUSTERING ANOMALY INSPECTION")
    print("=" * 100)

    with sqlite3.connect(DB_PATH) as connection:

        ratios = load_table(
            connection,
            "financial_ratios",
        )

        pnl = repair_embedded_header(
            load_table(
                connection,
                "profitandloss",
            )
        )

        balance = repair_embedded_header(
            load_table(
                connection,
                "balancesheet",
            )
        )

    inspect_financial_ratios(
        ratios
    )

    pnl_checked = inspect_pnl(
        pnl
    )

    inspect_balance_sheet(
        balance,
        pnl_checked,
    )

    print("\n" + "=" * 100)
    print("ANOMALY INSPECTION COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()
    
    