from pathlib import Path
import sqlite3
import pandas as pd

from src.analytics.ratios import (
    calculate_net_profit_margin,
    calculate_operating_profit_margin,
    calculate_roe,
    calculate_debt_to_equity,
    calculate_interest_coverage,
    calculate_asset_turnover,
)

DB_PATH = Path("db/nifty100.db")


def safe_get(row, column, default=0):
    return row[column] if column in row and pd.notna(row[column]) else default


def populate_financial_ratios():
    conn = sqlite3.connect(DB_PATH)

    profit_df = pd.read_sql_query("SELECT * FROM profitandloss", conn)

    records = []

    for _, row in profit_df.iterrows():
        company_id = safe_get(row, "id", None)
        company_name = safe_get(row, "company_name", safe_get(row, "name", ""))
        year = safe_get(row, "year", None)

        sales = safe_get(row, "sales", safe_get(row, "revenue", 0))
        net_profit = safe_get(row, "net_profit", safe_get(row, "profit_after_tax", 0))
        operating_profit = safe_get(row, "operating_profit", 0)

        equity_capital = safe_get(row, "equity_capital", 0)
        reserves = safe_get(row, "reserves", 0)
        borrowings = safe_get(row, "borrowings", 0)
        total_assets = safe_get(row, "total_assets", 0)

        other_income = safe_get(row, "other_income", 0)
        interest = safe_get(row, "interest", 0)

        net_profit_margin = calculate_net_profit_margin(net_profit, sales)
        operating_profit_margin = calculate_operating_profit_margin(
            operating_profit,
            sales
        )
        roe = calculate_roe(net_profit, equity_capital, reserves)
        debt_to_equity = calculate_debt_to_equity(
            borrowings,
            equity_capital,
            reserves
        )
        interest_coverage = calculate_interest_coverage(
            operating_profit,
            other_income,
            interest
        )
        asset_turnover = calculate_asset_turnover(sales, total_assets)

        records.append({
            "company_id": company_id,
            "company_name": company_name,
            "year": year,
            "net_profit_margin_pct": net_profit_margin,
            "operating_profit_margin_pct": operating_profit_margin,
            "return_on_equity_pct": roe,
            "debt_to_equity": debt_to_equity,
            "interest_coverage": interest_coverage,
            "asset_turnover": asset_turnover,
            "earnings_per_share": safe_get(row, "eps", 0),
            "total_debt_cr": borrowings,
            "cash_from_operations_cr": 0,
            "composite_quality_score": None,
        })

    ratio_df = pd.DataFrame(records)

    ratio_df.to_sql(
        "financial_ratios",
        conn,
        if_exists="replace",
        index=False
    )

    count = pd.read_sql_query(
        "SELECT COUNT(*) AS count FROM financial_ratios",
        conn
    )

    print("financial_ratios table populated.")
    print(f"Rows inserted: {count['count'].iloc[0]}")

    conn.close()


if __name__ == "__main__":
    populate_financial_ratios()