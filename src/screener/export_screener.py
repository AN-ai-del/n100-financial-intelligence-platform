from pathlib import Path
import sqlite3

import pandas as pd

from src.screener.engine import PRESETS

DB_PATH = Path("db/nifty100.db")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "screener_output.xlsx"


def ensure_composite_score(df):
    if "composite_quality_score" not in df.columns:
        df["composite_quality_score"] = 0

    df["composite_quality_score"] = pd.to_numeric(
        df["composite_quality_score"],
        errors="coerce"
    ).fillna(0)

    return df


def clean_sheet_name(name):
    return name.replace("-", " ").replace("/", " ")[:31]


def export_screener_output():
    conn = sqlite3.connect(DB_PATH)

    ratios = pd.read_sql_query(
        "SELECT * FROM financial_ratios",
        conn
    )

    ratios = ensure_composite_score(ratios)

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        for preset_name, preset_function in PRESETS.items():
            result = preset_function(ratios.copy())
            result = ensure_composite_score(result)

            result = result.sort_values(
                by="composite_quality_score",
                ascending=False
            )

            export_columns = [
                col for col in [
                    "company_id",
                    "company_name",
                    "year",
                    "net_profit_margin_pct",
                    "operating_profit_margin_pct",
                    "return_on_equity_pct",
                    "debt_to_equity",
                    "interest_coverage",
                    "asset_turnover",
                    "earnings_per_share",
                    "total_debt_cr",
                    "cash_from_operations_cr",
                    "composite_quality_score",
                ]
                if col in result.columns
            ]

            result[export_columns].to_excel(
                writer,
                sheet_name=clean_sheet_name(preset_name),
                index=False
            )

    conn.close()

    print(f"Screener output generated: {OUTPUT_FILE}")


if __name__ == "__main__":
    export_screener_output()