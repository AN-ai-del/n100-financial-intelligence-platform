import sqlite3
from pathlib import Path


# ---------------------------------------------------------
# PATH CONFIGURATION
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"


# ---------------------------------------------------------
# DATABASE INSPECTION
# ---------------------------------------------------------

def inspect_database():
    print("=" * 80)
    print("SPRINT 5 DATABASE INSPECTION")
    print("=" * 80)

    print(f"\nDatabase: {DB_PATH}")

    if not DB_PATH.exists():
        print("\nERROR: Database not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # -----------------------------------------------------
    # TABLE LIST
    # -----------------------------------------------------

    tables = cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()

    table_names = [row[0] for row in tables]

    print("\n" + "=" * 80)
    print("DATABASE TABLES")
    print("=" * 80)

    for table in table_names:
        print(table)

    print(f"\nTotal tables: {len(table_names)}")

    # -----------------------------------------------------
    # TABLE SCHEMAS
    # -----------------------------------------------------

    print("\n" + "=" * 80)
    print("TABLE SCHEMAS")
    print("=" * 80)

    for table in table_names:

        print("\n" + "-" * 80)
        print(table.upper())
        print("-" * 80)

        columns = cursor.execute(
            f'PRAGMA table_info("{table}")'
        ).fetchall()

        for column in columns:
            cid, name, dtype, notnull, default_value, pk = column

            print(
                f"{name:<35}"
                f"{dtype:<15}"
                f"PK={pk}"
            )

        count = cursor.execute(
            f'SELECT COUNT(*) FROM "{table}"'
        ).fetchone()[0]

        print(f"\nRows: {count}")

    # -----------------------------------------------------
    # SAMPLE DATA
    # -----------------------------------------------------

    print("\n" + "=" * 80)
    print("SAMPLE DATA")
    print("=" * 80)

    important_tables = [
        "companies",
        "financial_ratios",
        "market_cap",
        "profitandloss",
        "cashflow",
        "sectors",
        "documents",
    ]

    for table in important_tables:

        if table not in table_names:
            continue

        print("\n" + "-" * 80)
        print(f"{table.upper()} — FIRST 2 ROWS")
        print("-" * 80)

        try:
            rows = cursor.execute(
                f'SELECT * FROM "{table}" LIMIT 2'
            ).fetchall()

            for row in rows:
                print(row)

        except sqlite3.Error as error:
            print(f"Could not inspect {table}: {error}")

    conn.close()

    print("\n" + "=" * 80)
    print("INSPECTION COMPLETE")
    print("=" * 80)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

if __name__ == "__main__":
    inspect_database()