from pathlib import Path
import sqlite3
import traceback
import pandas as pd

DB_PATH = Path("db/nifty100.db")
RAW_DATA_DIR = Path("data/raw")
OUTPUT_DIR = Path("output")

OUTPUT_DIR.mkdir(exist_ok=True)

FILE_TABLE_MAP = {
    "companies.xlsx": "companies",
    "profitandloss.xlsx": "profitandloss",
    "balancesheet.xlsx": "balancesheet",
    "cashflow.xlsx": "cashflow",
    "analysis.xlsx": "analysis",
    "documents.xlsx": "documents",
    "prosandcons.xlsx": "prosandcons",
    "financial_ratios.xlsx": "financial_ratios",
    "market_cap.xlsx": "market_cap",
    "peer_groups.xlsx": "peer_groups",
    "sectors.xlsx": "sectors",
    "stock_prices.xlsx": "stock_prices",
}


def clean_column_name(column):
    return (
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace(".", "")
        .replace("(", "")
        .replace(")", "")
        .replace("%", "pct")
        .replace("&", "and")
    )


def load_excel_to_sqlite():
    audit_records = []

    if not DB_PATH.exists():
        raise FileNotFoundError(
            "nifty100.db not found. Run: py src\\etl\\create_database.py"
        )

    conn = sqlite3.connect(DB_PATH)

    for file_name, table_name in FILE_TABLE_MAP.items():
        file_path = RAW_DATA_DIR / file_name

        if not file_path.exists():
            audit_records.append({
                "file_name": file_name,
                "table_name": table_name,
                "status": "FILE_NOT_FOUND",
                "rows_loaded": 0,
                "error": "Source file missing"
            })
            print(f"FAILED: {table_name}")
            print(f"ERROR: Missing file {file_path}")
            continue

        try:
            df = pd.read_excel(file_path)

            df.columns = [clean_column_name(col) for col in df.columns]

            df.to_sql(
                table_name,
                conn,
                if_exists="replace",
                index=False
            )

            audit_records.append({
                "file_name": file_name,
                "table_name": table_name,
                "status": "SUCCESS",
                "rows_loaded": len(df),
                "error": ""
            })

            print(f"Loaded {table_name}: {len(df)} rows")

        except Exception as e:
            audit_records.append({
                "file_name": file_name,
                "table_name": table_name,
                "status": "ERROR",
                "rows_loaded": 0,
                "error": str(e)
            })

            print(f"\nFAILED: {table_name}")
            print(f"ERROR: {e}")
            traceback.print_exc()

    conn.close()

    audit_df = pd.DataFrame(audit_records)
    audit_path = OUTPUT_DIR / "load_audit.csv"
    audit_df.to_csv(audit_path, index=False)

    print("\nLoad audit generated.")
    print(f"Saved to: {audit_path}")


if __name__ == "__main__":
    load_excel_to_sqlite()