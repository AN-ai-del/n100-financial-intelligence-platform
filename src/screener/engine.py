from pathlib import Path
import sqlite3

import pandas as pd
import yaml

DB_PATH = Path("db/nifty100.db")
CONFIG_PATH = Path("config/screener_config.yaml")


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def apply_threshold(df, column, operator, value):

    if column not in df.columns:
        return df

    series = pd.to_numeric(df[column], errors="coerce")

    if operator == ">":
        return df[series > value]

    if operator == ">=":
        return df[series >= value]

    if operator == "<":
        return df[series < value]

    if operator == "<=":
        return df[series <= value]

    if operator == "=":
        return df[series == value]

    return df


# ------------------------
# Presets
# ------------------------

def quality_compounder(df):

    df = apply_threshold(df, "return_on_equity_pct", ">", 15)
    df = apply_threshold(df, "debt_to_equity", "<", 1)
    df = apply_threshold(df, "free_cash_flow_cr", ">", 0)
    df = apply_threshold(df, "revenue_cagr_5yr", ">", 10)

    return df


def value_pick(df):

    df = apply_threshold(df, "pe_ratio", "<", 20)
    df = apply_threshold(df, "pb_ratio", "<", 3)
    df = apply_threshold(df, "debt_to_equity", "<", 2)
    df = apply_threshold(df, "dividend_yield", ">", 1)

    return df


def growth_accelerator(df):

    df = apply_threshold(df, "pat_cagr_5yr", ">", 20)
    df = apply_threshold(df, "revenue_cagr_5yr", ">", 15)
    df = apply_threshold(df, "debt_to_equity", "<", 2)

    return df


def dividend_champion(df):

    df = apply_threshold(df, "dividend_yield", ">", 2)
    df = apply_threshold(df, "dividend_payout_ratio_pct", "<", 80)
    df = apply_threshold(df, "free_cash_flow_cr", ">", 0)

    return df


def debt_free_bluechip(df):

    df = apply_threshold(df, "debt_to_equity", "=", 0)
    df = apply_threshold(df, "return_on_equity_pct", ">", 12)
    df = apply_threshold(df, "sales", ">", 5000)

    return df


def turnaround_watch(df):

    df = apply_threshold(df, "revenue_cagr_3yr", ">", 10)
    df = apply_threshold(df, "free_cash_flow_cr", ">", 0)

    return df


PRESETS = {
    "Quality Compounder": quality_compounder,
    "Value Pick": value_pick,
    "Growth Accelerator": growth_accelerator,
    "Dividend Champion": dividend_champion,
    "Debt-Free Blue Chip": debt_free_bluechip,
    "Turnaround Watch": turnaround_watch,
}


def main():

    conn = sqlite3.connect(DB_PATH)

    ratios = pd.read_sql_query(
        "SELECT * FROM financial_ratios",
        conn
    )

    for name, func in PRESETS.items():

        result = func(ratios.copy())

        print("=" * 60)
        print(name)
        print(f"Companies Found : {len(result)}")

        if len(result):

            print(
                result.head()[
                    result.columns[:8]
                ]
            )

    conn.close()


if __name__ == "__main__":
    main()