"""
Inspect suspected source-column alignment problems for
BEL, HAL and CIPLA before repairing derived financial ratios.
"""

from pathlib import Path
import sqlite3

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"

TARGETS = ["BEL", "HAL", "CIPLA"]


def repair_header(df: pd.DataFrame) -> pd.DataFrame:
    """Promote the embedded first row to column headers."""

    if df.empty:
        return df

    header = df.iloc[0].tolist()

    repaired = df.iloc[1:].copy()

    repaired.columns = [
        str(value).strip()
        if pd.notna(value)
        else f"column_{i}"
        for i, value in enumerate(header)
    ]

    return repaired.reset_index(drop=True)


def main() -> None:
    """Inspect full raw P&L and balance-sheet rows."""

    with sqlite3.connect(DB_PATH) as connection:

        pnl = pd.read_sql_query(
            "SELECT * FROM profitandloss",
            connection,
        )

        bs = pd.read_sql_query(
            "SELECT * FROM balancesheet",
            connection,
        )

    pnl = repair_header(pnl)
    bs = repair_header(bs)

    print("=" * 120)
    print("FULL P&L ROWS")
    print("=" * 120)

    pnl_target = pnl[
        pnl["company_id"].isin(TARGETS)
    ].copy()

    print(
        pnl_target.to_string(
            index=False
        )
    )

    print("\n" + "=" * 120)
    print("FULL BALANCE-SHEET ROWS")
    print("=" * 120)

    bs_target = bs[
        bs["company_id"].isin(TARGETS)
    ].copy()

    print(
        bs_target.to_string(
            index=False
        )
    )

    print("\n" + "=" * 120)
    print("COLUMN NAMES")
    print("=" * 120)

    print("\nP&L:")
    for index, column in enumerate(pnl.columns):
        print(index, column)

    print("\nBalance Sheet:")
    for index, column in enumerate(bs.columns):
        print(index, column)


if __name__ == "__main__":
    main()
    