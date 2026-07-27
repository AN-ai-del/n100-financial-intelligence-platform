"""
Sprint 5 Day 29
Inspect missing SBIN financial-ratio records.
"""

import sqlite3
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "db" / "nifty100.db"


def main():
    print("=" * 90)
    print("SBIN FINANCIAL RATIO INSPECTION")
    print("=" * 90)

    conn = sqlite3.connect(DB_PATH)

    # ---------------------------------------------------------
    # 1. Exact SBIN search
    # ---------------------------------------------------------

    exact = pd.read_sql_query(
        """
        SELECT *
        FROM financial_ratios
        WHERE UPPER(TRIM(company_id)) = 'SBIN'
        ORDER BY year
        """,
        conn,
    )

    print("\n1. EXACT SBIN RECORDS")
    print("-" * 90)

    print(f"Rows found: {len(exact)}")

    if not exact.empty:
        print(exact.to_string(index=False))
    else:
        print("No exact SBIN records found.")

    # ---------------------------------------------------------
    # 2. Similar company IDs
    # ---------------------------------------------------------

    similar_ids = pd.read_sql_query(
        """
        SELECT DISTINCT company_id
        FROM financial_ratios
        WHERE
            UPPER(company_id) LIKE '%SBI%'
            OR UPPER(company_id) LIKE '%STATE%'
            OR UPPER(company_id) LIKE '%BANK%'
        ORDER BY company_id
        """,
        conn,
    )

    print("\n2. POSSIBLE RELATED TICKERS")
    print("-" * 90)

    if similar_ids.empty:
        print("No possible matching IDs found.")
    else:
        print(similar_ids.to_string(index=False))

    # ---------------------------------------------------------
    # 3. Check official company record
    # ---------------------------------------------------------

    company = pd.read_sql_query(
        """
        SELECT *
        FROM companies
        WHERE UPPER(TRIM(id)) = 'SBIN'
        """,
        conn,
    )

    print("\n3. SBIN COMPANY MASTER RECORD")
    print("-" * 90)

    if company.empty:
        print("SBIN does not exist in companies table.")
    else:
        print(company.to_string(index=False))

    # ---------------------------------------------------------
    # 4. Check raw financial ratio IDs
    # ---------------------------------------------------------

    all_ids = pd.read_sql_query(
        """
        SELECT
            company_id,
            COUNT(*) AS record_count
        FROM financial_ratios
        GROUP BY company_id
        ORDER BY company_id
        """,
        conn,
    )

    print("\n4. FINANCIAL-RATIO TICKERS AROUND 'S'")
    print("-" * 90)

    s_ids = all_ids[
        all_ids["company_id"]
        .astype(str)
        .str.upper()
        .str.startswith("S")
    ]

    print(s_ids.to_string(index=False))

    # ---------------------------------------------------------
    # 5. Coverage numbers
    # ---------------------------------------------------------

    print("\n5. TABLE COVERAGE")
    print("-" * 90)

    total_records = conn.execute(
        "SELECT COUNT(*) FROM financial_ratios"
    ).fetchone()[0]

    unique_companies = conn.execute(
        """
        SELECT COUNT(DISTINCT company_id)
        FROM financial_ratios
        """
    ).fetchone()[0]

    print(f"Financial-ratio rows      : {total_records}")
    print(f"Financial-ratio companies : {unique_companies}")

    conn.close()

    print("\n" + "=" * 90)
    print("INSPECTION COMPLETE")
    print("=" * 90)


if __name__ == "__main__":
    main()