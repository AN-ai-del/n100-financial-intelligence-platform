from pathlib import Path
import sqlite3

import pandas as pd
import yaml

DB_PATH = Path("db/nifty100.db")
CONFIG_PATH = Path("config/screener_config.yaml")


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def apply_filters(df, config):

    filters = config["filters"]

    if "return_on_equity_pct" in df.columns:
        df = df[
            df["return_on_equity_pct"].fillna(-999)
            >= filters["roe_min"]
        ]

    if "debt_to_equity" in df.columns:

        if "broad_sector" in df.columns:

            financial_mask = (
                df["broad_sector"]
                .fillna("")
                .str.lower()
                == "financials"
            )

            df = df[
                financial_mask
                |
                (
                    df["debt_to_equity"].fillna(999)
                    <= filters["debt_to_equity_max"]
                )
            ]

        else:

            df = df[
                df["debt_to_equity"].fillna(999)
                <= filters["debt_to_equity_max"]
            ]

    if "interest_coverage" in df.columns:

        df["interest_coverage_numeric"] = (
            df["interest_coverage"]
            .replace("Debt Free", float("inf"))
        )

        df = df[
            pd.to_numeric(
                df["interest_coverage_numeric"],
                errors="coerce"
            ).fillna(0)
            >= filters["interest_coverage_min"]
        ]

    if "composite_quality_score" not in df.columns:
        df["composite_quality_score"] = 0

    df = df.sort_values(
        by="composite_quality_score",
        ascending=False
    )

    return df


def main():

    conn = sqlite3.connect(DB_PATH)

    ratios = pd.read_sql_query(
        "SELECT * FROM financial_ratios",
        conn
    )

    config = load_config()

    filtered = apply_filters(ratios, config)

    print(filtered.head())

    conn.close()


if __name__ == "__main__":
    main()