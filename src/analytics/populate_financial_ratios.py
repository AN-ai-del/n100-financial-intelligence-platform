from pathlib import Path
import sqlite3
import pandas as pd

DB_PATH = Path("db/nifty100.db")
RAW_DIR = Path("data/raw")


def populate_financial_ratios():
    conn = sqlite3.connect(DB_PATH)

    ratios_path = RAW_DIR / "financial_ratios.xlsx"
    sectors_path = RAW_DIR / "sectors.xlsx"

    ratios_df = pd.read_excel(ratios_path)
    sectors_df = pd.read_excel(sectors_path)

    ratios_df.columns = ratios_df.columns.str.strip()
    sectors_df.columns = sectors_df.columns.str.strip()

    ratios_df = ratios_df.merge(
        sectors_df[["company_id", "broad_sector", "sub_sector"]],
        on="company_id",
        how="left"
    )

    ratios_df["composite_quality_score"] = 0

    ratios_df.to_sql(
        "financial_ratios",
        conn,
        if_exists="replace",
        index=False
    )

    count = pd.read_sql_query(
        "SELECT COUNT(*) AS count FROM financial_ratios",
        conn
    )

    print("financial_ratios table rebuilt from financial_ratios.xlsx.")
    print(f"Rows inserted: {count['count'].iloc[0]}")

    conn.close()


if __name__ == "__main__":
    populate_financial_ratios()