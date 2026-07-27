"""
Sprint 5 Day 29

Compare the official company universe against the
financial_ratios company universe.

Purpose:
- identify companies missing from financial_ratios
- identify unexpected tickers in financial_ratios
- avoid fabricating or incorrectly mapping financial data
"""

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "db" / "nifty100.db"


def normalize_company_id(value):
    if value is None:
        return ""

    return str(value).strip().upper()


def main():
    print("=" * 90)
    print("SPRINT 5 — FINANCIAL RATIO COMPANY COVERAGE CHECK")
    print("=" * 90)

    conn = sqlite3.connect(DB_PATH)

    # ---------------------------------------------------------
    # Official company universe
    # ---------------------------------------------------------

    official_rows = conn.execute(
        """
        SELECT id, company_name
        FROM companies
        ORDER BY id
        """
    ).fetchall()

    official_map = {
        normalize_company_id(company_id): company_name
        for company_id, company_name in official_rows
        if normalize_company_id(company_id)
    }

    # ---------------------------------------------------------
    # Financial ratio universe
    # ---------------------------------------------------------

    ratio_rows = conn.execute(
        """
        SELECT
            company_id,
            COUNT(*) AS record_count
        FROM financial_ratios
        GROUP BY company_id
        ORDER BY company_id
        """
    ).fetchall()

    ratio_map = {
        normalize_company_id(company_id): record_count
        for company_id, record_count in ratio_rows
        if normalize_company_id(company_id)
    }

    official_ids = set(official_map)
    ratio_ids = set(ratio_map)

    # ---------------------------------------------------------
    # Compare
    # ---------------------------------------------------------

    missing = sorted(official_ids - ratio_ids)
    unexpected = sorted(ratio_ids - official_ids)

    print()
    print("COVERAGE SUMMARY")
    print("-" * 90)
    print(f"Official companies        : {len(official_ids)}")
    print(f"Financial-ratio companies : {len(ratio_ids)}")

    print()
    print("MISSING FROM FINANCIAL RATIOS")
    print("-" * 90)

    if missing:
        for company_id in missing:
            print(
                f"{company_id:<15} "
                f"{official_map.get(company_id, 'Unknown company')}"
            )
    else:
        print("None")

    print()
    print("UNEXPECTED IN FINANCIAL RATIOS")
    print("-" * 90)

    if unexpected:
        for company_id in unexpected:
            print(
                f"{company_id:<15} "
                f"records={ratio_map.get(company_id, 0)}"
            )
    else:
        print("None")

    # ---------------------------------------------------------
    # Print unexpected records
    # ---------------------------------------------------------

    if unexpected:
        print()
        print("UNEXPECTED TICKER RECORD DETAILS")
        print("-" * 90)

        for company_id in unexpected:
            rows = conn.execute(
                """
                SELECT *
                FROM financial_ratios
                WHERE UPPER(TRIM(company_id)) = ?
                ORDER BY year
                """,
                (company_id,),
            ).fetchall()

            print()
            print(
                f"{company_id} "
                f"({len(rows)} financial-ratio records)"
            )

            for row in rows[:5]:
                print(row)

            if len(rows) > 5:
                print(f"... {len(rows) - 5} additional rows")

    # ---------------------------------------------------------
    # SBIN source check
    # ---------------------------------------------------------

    print()
    print("SBIN STATUS")
    print("-" * 90)

    print(
        "Official company record :",
        "YES" if "SBIN" in official_ids else "NO",
    )

    print(
        "Financial-ratio record  :",
        "YES" if "SBIN" in ratio_ids else "NO",
    )

    conn.close()

    print()
    print("=" * 90)
    print("COVERAGE CHECK COMPLETE")
    print("=" * 90)


if __name__ == "__main__":
    main()