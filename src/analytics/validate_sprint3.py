from pathlib import Path
import sqlite3
import pandas as pd

DB_PATH = Path("db/nifty100.db")


def validate():
    conn = sqlite3.connect(DB_PATH)

    print("=" * 70)
    print("SPRINT 3 VALIDATION")
    print("=" * 70)

    # financial_ratios
    ratios = pd.read_sql_query(
        "SELECT COUNT(*) AS count FROM financial_ratios",
        conn
    )

    print(f"financial_ratios rows : {ratios['count'][0]}")

    # peer_percentiles
    peer = pd.read_sql_query(
        "SELECT COUNT(*) AS count FROM peer_percentiles",
        conn
    )

    print(f"peer_percentiles rows : {peer['count'][0]}")

    # peer groups
    peer_groups = pd.read_excel("data/raw/peer_groups.xlsx")

    print(f"Peer Groups : {peer_groups['peer_group_name'].nunique()}")

    # radar charts
    radar_folder = Path("reports/radar_charts")

    charts = len(list(radar_folder.glob("*.png")))

    print(f"Radar Charts : {charts}")

    # screener workbook
    screener_exists = Path(
        "output/screener_output.xlsx"
    ).exists()

    print(f"Screener Workbook : {screener_exists}")

    # peer workbook
    peer_exists = Path(
        "output/peer_comparison.xlsx"
    ).exists()

    print(f"Peer Workbook : {peer_exists}")

    conn.close()

    print("=" * 70)
    print("Sprint 3 validation complete.")
    print("=" * 70)


if __name__ == "__main__":
    validate()