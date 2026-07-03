import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path("db/nifty100.db")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


def log_edge_cases():

    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql_query(
        "SELECT * FROM financial_ratios",
        conn
    )

    log_lines = []

    for _, row in df.iterrows():

        company = row.get("company_name", "Unknown")

        roe = row.get("return_on_equity_pct")
        debt = row.get("debt_to_equity")
        icr = row.get("interest_coverage")

        if pd.notna(roe):

            if roe > 100:
                log_lines.append(
                    f"{company}: Extremely high ROE ({roe}) -> Possible data source issue"
                )

            elif roe < -50:
                log_lines.append(
                    f"{company}: Very negative ROE ({roe}) -> Loss-making company"
                )

        if pd.notna(debt):

            if debt > 5:
                log_lines.append(
                    f"{company}: High Debt-to-Equity ({debt})"
                )

        if pd.notna(icr):

            if icr < 1.5:
                log_lines.append(
                    f"{company}: Low Interest Coverage ({icr})"
                )

    logfile = OUTPUT_DIR / "ratio_edge_cases.log"

    with open(logfile, "w", encoding="utf-8") as f:

        f.write("Sprint 2 Day 13\n")
        f.write("=" * 60 + "\n\n")

        if len(log_lines) == 0:

            f.write("No edge cases detected.\n")

        else:

            for line in log_lines:
                f.write(line + "\n")

    print(f"Edge case log saved to {logfile}")

    conn.close()


if __name__ == "__main__":
    log_edge_cases()