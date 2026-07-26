import sqlite3
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "db" / "nifty100.db"
CAPITAL_PATH = BASE_DIR / "output" / "capital_allocation.csv"


def normalize(value):
    if pd.isna(value):
        return ""

    return str(value).strip().upper()


def main():

    # -----------------------------------------
    # Official companies
    # -----------------------------------------

    connection = sqlite3.connect(DB_PATH)

    companies = pd.read_sql_query(
        "SELECT * FROM companies",
        connection,
    )

    connection.close()

    # Your repaired companies table uses id
    if "id" in companies.columns:
        company_col = "id"

    elif "company_id" in companies.columns:
        company_col = "company_id"

    else:
        raise ValueError(
            f"Company ID column not found. "
            f"Columns: {companies.columns.tolist()}"
        )

    official = set(
        companies[company_col]
        .dropna()
        .map(normalize)
    )

    official.discard("")

    # -----------------------------------------
    # Capital allocation
    # -----------------------------------------

    capital = pd.read_csv(CAPITAL_PATH)

    capital_ids = set(
        capital["company_id"]
        .dropna()
        .map(normalize)
    )

    capital_ids.discard("")

    # -----------------------------------------
    # Compare
    # -----------------------------------------

    missing = sorted(
        official - capital_ids
    )

    extra = sorted(
        capital_ids - official
    )

    print("=" * 60)
    print("CAPITAL ALLOCATION COVERAGE CHECK")
    print("=" * 60)

    print(f"Official companies      : {len(official)}")
    print(f"Capital CSV companies   : {len(capital_ids)}")

    print("\nMissing companies:")
    print(missing)

    print("\nUnexpected companies:")
    print(extra)

    print("=" * 60)


if __name__ == "__main__":
    main()