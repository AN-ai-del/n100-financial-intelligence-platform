"""
Sprint 4 - Day 27
Final Integration QA & Validation

Validates:
- Core database tables
- Company coverage
- Sprint analytical outputs
- Valuation outputs
- Dashboard pages
- Capital allocation output
- Annual-report data
"""

from pathlib import Path
import sqlite3

import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"
DASHBOARD_DIR = PROJECT_ROOT / "src" / "dashboard"


# ============================================================
# VALIDATION TRACKER
# ============================================================

checks = []


def record_check(category, check, passed, details=""):
    """
    Store a validation result.
    """

    checks.append(
        {
            "category": category,
            "check": check,
            "status": "PASS" if passed else "FAIL",
            "details": str(details),
        }
    )


# ============================================================
# 1. DATABASE VALIDATION
# ============================================================

def validate_database():

    print("\n" + "=" * 72)
    print("1. DATABASE VALIDATION")
    print("=" * 72)

    exists = DB_PATH.exists()

    record_check(
        "Database",
        "Database file exists",
        exists,
        DB_PATH,
    )

    print(
        f"{'PASS' if exists else 'FAIL'} "
        f"Database file exists"
    )

    if not exists:
        print(f"Database path: {DB_PATH}")
        return

    connection = sqlite3.connect(DB_PATH)

    try:

        tables = pd.read_sql_query(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """,
            connection,
        )["name"].tolist()

        print(f"\nTables found: {len(tables)}")
        print(tables)

        required_tables = [
            "companies",
            "financial_ratios",
            "market_cap",
        ]

        for table in required_tables:

            passed = table in tables

            record_check(
                "Database",
                f"Required table: {table}",
                passed,
            )

            print(
                f"{'PASS' if passed else 'FAIL'} "
                f"Required table: {table}"
            )

        # ----------------------------------------------------
        # Company coverage
        # ----------------------------------------------------

        if "companies" in tables:

            company_count = pd.read_sql_query(
                """
                SELECT COUNT(DISTINCT id) AS n
                FROM companies
                """,
                connection,
            )["n"].iloc[0]

            print(
                f"\nOfficial companies: {company_count}"
            )

            record_check(
                "Coverage",
                "Official company universe loaded",
                company_count > 0,
                f"{company_count} companies",
            )

        # ----------------------------------------------------
        # Financial ratios coverage
        # ----------------------------------------------------

        if "financial_ratios" in tables:

            ratio_count = pd.read_sql_query(
                """
                SELECT COUNT(DISTINCT company_id) AS n
                FROM financial_ratios
                """,
                connection,
            )["n"].iloc[0]

            print(
                f"Financial ratio companies: {ratio_count}"
            )

            record_check(
                "Coverage",
                "Financial-ratio company coverage",
                ratio_count > 0,
                f"{ratio_count} companies",
            )

        # ----------------------------------------------------
        # Market-cap coverage
        # ----------------------------------------------------

        if "market_cap" in tables:

            market_count = pd.read_sql_query(
                """
                SELECT COUNT(DISTINCT company_id) AS n
                FROM market_cap
                """,
                connection,
            )["n"].iloc[0]

            print(
                f"Market-cap companies: {market_count}"
            )

            record_check(
                "Coverage",
                "Market-cap company coverage",
                market_count > 0,
                f"{market_count} companies",
            )

    except Exception as exc:

        record_check(
            "Database",
            "Database readable",
            False,
            exc,
        )

        print(f"FAIL: Database validation error: {exc}")

    finally:

        connection.close()


# ============================================================
# 2. ANALYTICAL OUTPUT VALIDATION
# ============================================================

def validate_outputs():

    print("\n" + "=" * 72)
    print("2. ANALYTICAL OUTPUT VALIDATION")
    print("=" * 72)

    expected_outputs = [
        "capital_allocation.csv",
        "valuation_summary.xlsx",
        "valuation_flags.csv",
    ]

    for filename in expected_outputs:

        path = OUTPUT_DIR / filename

        exists = path.exists()

        size = (
            path.stat().st_size
            if exists
            else 0
        )

        passed = exists and size > 0

        record_check(
            "Output",
            filename,
            passed,
            f"{size:,} bytes" if exists else "Missing",
        )

        print(
            f"{'PASS' if passed else 'FAIL'} "
            f"{filename}"
        )


# ============================================================
# 3. VALUATION VALIDATION
# ============================================================

def validate_valuation():

    print("\n" + "=" * 72)
    print("3. VALUATION VALIDATION")
    print("=" * 72)

    path = OUTPUT_DIR / "valuation_summary.xlsx"

    if not path.exists():

        record_check(
            "Valuation",
            "Valuation workbook readable",
            False,
            "Workbook missing",
        )

        print("FAIL: valuation_summary.xlsx is missing.")

        return

    try:

        excel = pd.ExcelFile(path)

        sheets = excel.sheet_names

        print(f"\nSheets: {sheets}")

        required_sheets = [
            "Company Valuation",
            "Sector Summary",
            "Valuation Categories",
        ]

        for sheet in required_sheets:

            passed = sheet in sheets

            record_check(
                "Valuation",
                f"Sheet exists: {sheet}",
                passed,
            )

            print(
                f"{'PASS' if passed else 'FAIL'} "
                f"Sheet exists: {sheet}"
            )

        if "Company Valuation" in sheets:

            df = pd.read_excel(
                path,
                sheet_name="Company Valuation",
            )

            print(
                f"\nCompany valuation rows: {len(df)}"
            )

            required_columns = [
                "company_id",
                "company_name",
                "pe_ratio",
                "pb_ratio",
                "ev_ebitda",
                "valuation_score",
                "valuation_category",
            ]

            for column in required_columns:

                passed = column in df.columns

                record_check(
                    "Valuation",
                    f"Column exists: {column}",
                    passed,
                )

                print(
                    f"{'PASS' if passed else 'FAIL'} "
                    f"Column exists: {column}"
                )

            if "company_id" in df.columns:

                company_count = (
                    df["company_id"]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .replace("", pd.NA)
                    .dropna()
                    .nunique()
                )

                record_check(
                    "Valuation",
                    "Valuation company coverage",
                    company_count > 0,
                    f"{company_count} companies",
                )

                print(
                    f"Valuation companies: {company_count}"
                )

            if "valuation_score" in df.columns:

                numeric_scores = pd.to_numeric(
                    df["valuation_score"],
                    errors="coerce",
                )

                non_null = numeric_scores.notna()

                valid_scores = numeric_scores.between(
                    0,
                    100,
                )

                passed = (
                    valid_scores[non_null].all()
                    if non_null.any()
                    else False
                )

                record_check(
                    "Valuation",
                    "Valuation scores within 0-100",
                    passed,
                )

                print(
                    f"{'PASS' if passed else 'FAIL'} "
                    "Valuation scores within 0-100"
                )

    except Exception as exc:

        record_check(
            "Valuation",
            "Valuation workbook readable",
            False,
            exc,
        )

        print(
            f"FAIL: Valuation workbook error: {exc}"
        )


# ============================================================
# 4. CAPITAL ALLOCATION VALIDATION
# ============================================================

def validate_capital_allocation():

    print("\n" + "=" * 72)
    print("4. CAPITAL ALLOCATION VALIDATION")
    print("=" * 72)

    path = OUTPUT_DIR / "capital_allocation.csv"

    if not path.exists():

        record_check(
            "Capital Allocation",
            "Capital allocation file readable",
            False,
            "File missing",
        )

        print(
            "FAIL: capital_allocation.csv is missing."
        )

        return

    try:

        df = pd.read_csv(path)

        print(f"\nRows: {len(df)}")

        # ----------------------------------------------------
        # Company identifier
        # ----------------------------------------------------

        company_column = None

        for candidate in [
            "company_id",
            "ticker",
        ]:

            if candidate in df.columns:
                company_column = candidate
                break

        if company_column is not None:

            companies = (
                df[company_column]
                .dropna()
                .astype(str)
                .str.strip()
            )

            companies = companies[
                companies != ""
            ].nunique()

            print(
                f"Companies represented: {companies}"
            )

            record_check(
                "Capital Allocation",
                "Company coverage",
                companies > 0,
                f"{companies} companies",
            )

        else:

            record_check(
                "Capital Allocation",
                "Company identifier exists",
                False,
                f"Columns: {list(df.columns)}",
            )

            print(
                "FAIL: No company identifier column found."
            )

        # ----------------------------------------------------
        # Capital allocation pattern
        # ----------------------------------------------------

        pattern_column = None

        for candidate in [
            "pattern_label",
            "capital_allocation_pattern",
            "pattern",
        ]:

            if candidate in df.columns:
                pattern_column = candidate
                break

        if pattern_column is not None:

            patterns = (
                df[pattern_column]
                .dropna()
                .astype(str)
                .str.strip()
            )

            patterns = patterns[
                patterns != ""
            ].nunique()

            print(
                f"Allocation patterns: {patterns}"
            )

            record_check(
                "Capital Allocation",
                "Allocation patterns generated",
                patterns > 0,
                f"{patterns} patterns",
            )

        else:

            record_check(
                "Capital Allocation",
                "Allocation pattern column exists",
                False,
                f"Columns: {list(df.columns)}",
            )

            print(
                "FAIL: No capital-allocation pattern column found."
            )

    except Exception as exc:

        record_check(
            "Capital Allocation",
            "Capital allocation file readable",
            False,
            exc,
        )

        print(
            f"FAIL: Capital allocation error: {exc}"
        )


# ============================================================
# 5. DASHBOARD FILE VALIDATION
# ============================================================

def validate_dashboard():

    print("\n" + "=" * 72)
    print("5. DASHBOARD FILE VALIDATION")
    print("=" * 72)

    dashboard_files = {
        "Dashboard App":
            PROJECT_ROOT
            / "src"
            / "dashboard"
            / "app.py",

        "Home Page":
            PROJECT_ROOT
            / "src"
            / "dashboard"
            / "pages"
            / "01_home.py",

        "Company Profile Page":
            PROJECT_ROOT
            / "src"
            / "dashboard"
            / "pages"
            / "02_profile.py",

        "Financial Screener Page":
            PROJECT_ROOT
            / "src"
            / "dashboard"
            / "pages"
            / "03_screener.py",

        "Peer Comparison Page":
            PROJECT_ROOT
            / "src"
            / "dashboard"
            / "pages"
            / "04_peers.py",

        "Financial Trends Page":
            PROJECT_ROOT
            / "src"
            / "dashboard"
            / "pages"
            / "05_trends.py",

        "Sector Analysis Page":
            PROJECT_ROOT
            / "src"
            / "dashboard"
            / "pages"
            / "06_sectors.py",

        "Capital Allocation Page":
            PROJECT_ROOT
            / "src"
            / "dashboard"
            / "pages"
            / "07_capital.py",

        "Annual Reports Page":
            PROJECT_ROOT
            / "src"
            / "dashboard"
            / "pages"
            / "08_reports.py",
    }

    for label, path in dashboard_files.items():

        exists = path.exists()

        size = (
            path.stat().st_size
            if exists
            else 0
        )

        passed = (
            exists
            and path.is_file()
            and size > 0
        )

        record_check(
            "Dashboard",
            f"{label} exists",
            passed,
            (
                f"{path} ({size:,} bytes)"
                if exists
                else f"Missing: {path}"
            ),
        )

        print(
            f"{'PASS' if passed else 'FAIL'} "
            f"{label}: {path}"
        )


# ============================================================
# 6. ANNUAL REPORT DATA VALIDATION
# ============================================================

def validate_documents():

    print("\n" + "=" * 72)
    print("6. ANNUAL REPORT DATA VALIDATION")
    print("=" * 72)

    documents_path = (
        PROJECT_ROOT
        / "data"
        / "raw"
        / "documents.xlsx"
    )

    exists = documents_path.exists()

    record_check(
        "Reports",
        "documents.xlsx exists",
        exists,
        documents_path,
    )

    print(
        f"{'PASS' if exists else 'FAIL'} "
        "documents.xlsx exists"
    )

    if not exists:
        return

    try:

        raw = pd.read_excel(
            documents_path
        )

        print(
            f"\nRaw document rows: {len(raw)}"
        )

        record_check(
            "Reports",
            "Documents dataset readable",
            len(raw) > 0,
            f"{len(raw)} rows",
        )

    except Exception as exc:

        record_check(
            "Reports",
            "Documents dataset readable",
            False,
            exc,
        )

        print(
            f"FAIL: Documents dataset error: {exc}"
        )


# ============================================================
# FINAL QA REPORT
# ============================================================

def generate_report():

    print("\n" + "=" * 72)
    print("DAY 27 FINAL QA REPORT")
    print("=" * 72)

    results = pd.DataFrame(checks)

    if results.empty:

        print("No checks executed.")

        return

    passed = (
        results["status"] == "PASS"
    ).sum()

    failed = (
        results["status"] == "FAIL"
    ).sum()

    total = len(results)

    print(f"\nTotal checks : {total}")
    print(f"Passed       : {passed}")
    print(f"Failed       : {failed}")

    pass_rate = (
        passed / total * 100
        if total
        else 0
    )

    print(
        f"Pass rate    : {pass_rate:.1f}%"
    )

    failed_checks = results[
        results["status"] == "FAIL"
    ]

    if not failed_checks.empty:

        print("\nFAILED CHECKS:")

        print(
            failed_checks[
                [
                    "category",
                    "check",
                    "details",
                ]
            ].to_string(
                index=False
            )
        )

    else:

        print(
            "\nALL DAY 27 INTEGRATION CHECKS PASSED."
        )

    # --------------------------------------------------------
    # Save validation report
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIR
        / "sprint4_validation.csv"
    )

    results.to_csv(
        output_path,
        index=False,
    )

    print(
        f"\nValidation report saved to:"
        f"\n{output_path}"
    )

    print("=" * 72)


# ============================================================
# MAIN
# ============================================================

def main():

    # Clear previous results in case main() is called again
    checks.clear()

    validate_database()

    validate_outputs()

    validate_valuation()

    validate_capital_allocation()

    validate_dashboard()

    validate_documents()

    generate_report()


if __name__ == "__main__":
    main()