# src/analytics/peer.py

from pathlib import Path
import sqlite3
import pandas as pd

DB_PATH = Path("db/nifty100.db")
PEER_GROUPS_PATH = Path("data/raw/peer_groups.xlsx")


METRICS = {
    "return_on_equity_pct": "normal",
    "net_profit_margin_pct": "normal",
    "debt_to_equity": "inverse",
    "free_cash_flow_cr": "normal",
    "revenue_cagr_5yr": "normal",
    "pat_cagr_5yr": "normal",
    "eps_cagr_5yr": "normal",
    "interest_coverage": "normal",
    "asset_turnover": "normal",
    "composite_quality_score": "normal",
}


def percent_rank(series, inverse=False):
    numeric = pd.to_numeric(series, errors="coerce")

    if numeric.notna().sum() <= 1:
        ranks = pd.Series(1.0, index=series.index)
    else:
        ranks = numeric.rank(method="min", pct=True)

    if inverse:
        ranks = 1 - ranks

    return ranks.round(4)


def load_data():
    conn = sqlite3.connect(DB_PATH)

    ratios = pd.read_sql_query(
        "SELECT * FROM financial_ratios",
        conn
    )

    conn.close()

    peer_groups = pd.read_excel(PEER_GROUPS_PATH)

    ratios.columns = ratios.columns.str.strip()
    peer_groups.columns = peer_groups.columns.str.strip()

    return ratios, peer_groups


def build_peer_percentiles():
    ratios, peer_groups = load_data()

    merged = ratios.merge(
        peer_groups[["peer_group_name", "company_id", "is_benchmark"]],
        on="company_id",
        how="left"
    )

    records = []

    grouped = merged.dropna(subset=["peer_group_name"]).groupby(
        ["peer_group_name", "year"],
        dropna=False
    )

    for (peer_group_name, year), group in grouped:
        for metric, direction in METRICS.items():
            if metric not in group.columns:
                continue

            ranks = percent_rank(
                group[metric],
                inverse=(direction == "inverse")
            )

            for idx, row in group.iterrows():
                value = row.get(metric)

                records.append({
                    "company_id": row.get("company_id"),
                    "peer_group_name": peer_group_name,
                    "metric": metric,
                    "value": value,
                    "percentile_rank": ranks.loc[idx],
                    "year": year,
                    "is_benchmark": row.get("is_benchmark", False),
                })

    peer_percentiles = pd.DataFrame(records)

    conn = sqlite3.connect(DB_PATH)

    peer_percentiles.to_sql(
        "peer_percentiles",
        conn,
        if_exists="replace",
        index=False
    )

    print("peer_percentiles table created.")
    print(f"Rows inserted: {len(peer_percentiles)}")

    print("\nPreview:")
    print(peer_percentiles.head(10))

    conn.close()


if __name__ == "__main__":
    build_peer_percentiles()