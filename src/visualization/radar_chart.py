from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

DB_PATH = "db/nifty100.db"

OUTPUT_DIR = Path("reports/radar_charts")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

METRICS = [
    "return_on_equity_pct",
    "net_profit_margin_pct",
    "debt_to_equity",
    "interest_coverage",
    "asset_turnover",
    "free_cash_flow_cr",
    "cash_from_operations_cr",
    "composite_quality_score",
]


def load_data():

    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql("""
        SELECT *
        FROM financial_ratios
    """, conn)

    peers = pd.read_sql("""
        SELECT *
        FROM peer_percentiles
    """, conn)

    conn.close()

    return df, peers


def latest_year(df):

    latest = (
        df.groupby("company_id")["year"]
        .max()
        .reset_index()
    )

    return df.merge(latest, on=["company_id", "year"])


def radar(company_row, peer_avg, company_name):

    values = company_row[METRICS].fillna(0).values.astype(float)
    avg = peer_avg[METRICS].fillna(0).values.astype(float)

    labels = [
        "ROE",
        "NPM",
        "D/E",
        "ICR",
        "Asset",
        "FCF",
        "CFO",
        "Score",
    ]

    N = len(labels)

    angles = np.linspace(0, 2 * np.pi, N, endpoint=False)

    values = np.concatenate((values, [values[0]]))
    avg = np.concatenate((avg, [avg[0]]))
    angles = np.concatenate((angles, [angles[0]]))

    plt.figure(figsize=(8, 8))

    ax = plt.subplot(111, polar=True)

    ax.plot(angles, values, linewidth=2)

    ax.fill(angles, values, alpha=0.25)

    ax.plot(
        angles,
        avg,
        linestyle="--",
        linewidth=2,
    )

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)

    plt.title(company_name)

    plt.savefig(
        OUTPUT_DIR / f"{company_name}_radar.png",
        dpi=150,
        bbox_inches="tight"
    )

    plt.close()


def generate():

    ratios, peer_percentiles = load_data()

    ratios = latest_year(ratios)

    peer_map = (
        peer_percentiles[
            ["company_id", "peer_group_name"]
        ]
        .drop_duplicates()
    )

    ratios = ratios.merge(
        peer_map,
        on="company_id",
        how="left"
    )

    groups = ratios.groupby("peer_group_name")

    charts = 0

    for peer_name, group in groups:

        if pd.isna(peer_name):
            continue

        avg = group[METRICS].mean(numeric_only=True)

        for _, row in group.iterrows():

            radar(
                row,
                avg,
                row.company_id,
            )

            charts += 1

    print("=" * 60)
    print("Radar charts generated")
    print("Charts:", charts)
    print("Saved to:", OUTPUT_DIR)
    print("=" * 60)


if __name__ == "__main__":
    generate()