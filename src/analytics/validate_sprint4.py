"""
Sprint 4 - Day 28
Dashboard Validation and Sprint Review

Validates the major files, database tables, generated outputs,
and dashboard modules required for Sprint 4.
"""

from pathlib import Path
import sqlite3
import sys


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"

DASHBOARD_DIR = PROJECT_ROOT / "src" / "dashboard"
PAGES_DIR = DASHBOARD_DIR / "pages"

OUTPUT_DIR = PROJECT_ROOT / "output"


# ---------------------------------------------------------
# Utility functions
# ---------------------------------------------------------

def print_check(label, passed, details=""):
    status = "PASS" if passed else "FAIL"

    print(f"[{status}] {label}")

    if details:
        print(f"       {details}")

    return passed


def check_file(path, label):
    exists = path.exists()

    return print_check(
        label,
        exists,
        str(path)
    )


def get_database_tables():
    if not DB_PATH.exists():
        return []

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        )

        return [row[0] for row in cursor.fetchall()]


def get_table_count(table_name):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute(
                f'SELECT COUNT(*) FROM "{table_name}"'
            )

            return cursor.fetchone()[0]

    except Exception:
        return None


# ---------------------------------------------------------
# Main validation
# ---------------------------------------------------------

def main():

    print("=" * 72)
    print("SPRINT 4 VALIDATION")
    print("=" * 72)

    checks = []

    # -----------------------------------------------------
    # 1. Database
    # -----------------------------------------------------

    print("\n1. DATABASE")
    print("-" * 72)

    checks.append(
        check_file(
            DB_PATH,
            "Nifty100 SQLite database exists"
        )
    )

    tables = get_database_tables()

    required_tables = [
        "companies",
        "financial_ratios",
        "profitandloss",
        "cashflow",
        "market_cap",
        "sectors",
        "documents",
        "peer_groups",
        "peer_percentiles",
    ]

    for table in required_tables:

        exists = table in tables

        count = get_table_count(table) if exists else None

        details = (
            f"{count} rows"
            if count is not None
            else "table not found"
        )

        checks.append(
            print_check(
                f"Table: {table}",
                exists and count is not None and count > 0,
                details
            )
        )

    # -----------------------------------------------------
    # 2. Dashboard application
    # -----------------------------------------------------

    print("\n2. DASHBOARD APPLICATION")
    print("-" * 72)

    app_files = [
        (
            DASHBOARD_DIR / "app.py",
            "Dashboard app.py"
        ),
        (
            PAGES_DIR / "01_home.py",
            "Home page"
        ),
        (
            PAGES_DIR / "02_profile.py",
            "Company Profile page"
        ),
        (
            PAGES_DIR / "03_screener.py",
            "Financial Screener page"
        ),
        (
            PAGES_DIR / "04_peers.py",
            "Peer Comparison page"
        ),
        (
            PAGES_DIR / "05_trends.py",
            "Financial Trends page"
        ),
        (
            PAGES_DIR / "06_sectors.py",
            "Sector Analysis page"
        ),
        (
            PAGES_DIR / "07_capital.py",
            "Capital Allocation page"
        ),
        (
            PAGES_DIR / "08_reports.py",
            "Annual Reports page"
        ),
    ]

    for file_path, label in app_files:
        checks.append(
            check_file(
                file_path,
                label
            )
        )

    # -----------------------------------------------------
    # 3. Sprint 3 / Sprint 4 analytical outputs
    # -----------------------------------------------------

    print("\n3. ANALYTICAL OUTPUTS")
    print("-" * 72)

    output_checks = [
        (
            OUTPUT_DIR / "screener_output.xlsx",
            "Screener output workbook"
        ),
        (
            OUTPUT_DIR / "peer_comparison.xlsx",
            "Peer comparison workbook"
        ),
        (
            OUTPUT_DIR / "capital_allocation.csv",
            "Capital allocation dataset"
        ),
    ]

    for file_path, label in output_checks:
        checks.append(
            check_file(
                file_path,
                label
            )
        )

    # -----------------------------------------------------
    # 4. Supporting analytics scripts
    # -----------------------------------------------------

    print("\n4. ANALYTICS MODULES")
    print("-" * 72)

    analytics_dir = PROJECT_ROOT / "src" / "analytics"

    analytics_files = [
        (
            analytics_dir / "ratios.py",
            "Financial ratio engine"
        ),
        (
            analytics_dir / "cagr.py",
            "CAGR engine"
        ),
        (
            analytics_dir / "cashflow_kpis.py",
            "Cash-flow KPI engine"
        ),
        (
            analytics_dir / "peer.py",
            "Peer percentile engine"
        ),
        (
            analytics_dir / "peer_report.py",
            "Peer comparison report engine"
        ),
        (
            analytics_dir / "generate_capital_allocation.py",
            "Capital allocation generator"
        ),
    ]

    for file_path, label in analytics_files:
        checks.append(
            check_file(
                file_path,
                label
            )
        )

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    print("\n" + "=" * 72)
    print("SPRINT 4 VALIDATION SUMMARY")
    print("=" * 72)

    passed = sum(checks)
    total = len(checks)
    failed = total - passed

    print(f"Checks passed : {passed}")
    print(f"Checks failed : {failed}")
    print(f"Total checks  : {total}")

    print("=" * 72)

    if failed == 0:

        print("SPRINT 4 VALIDATION PASSED")
        print("Dashboard is ready for Sprint 4 closure.")

        sys.exit(0)

    else:

        print("SPRINT 4 VALIDATION FAILED")
        print("Fix the failed checks before closing Sprint 4.")

        sys.exit(1)


if __name__ == "__main__":
    main()