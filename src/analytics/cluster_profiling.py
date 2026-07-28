"""
Sprint 6 — Day 37
Cluster Profiling, Statistics, Correlation and Outlier Analysis

Inputs:
    output/clustering_features.csv
    output/cluster_labels.csv
    db/nifty100.db

Outputs:
    output/cluster_profiles.csv
    output/company_cluster_profiles.csv
    output/outlier_report.csv
    output/portfolio_stats.csv
    output/day37_validation_summary.csv
    reports/correlation_heatmap.png

Main tasks:
    1. Profile each of the five KMeans clusters.
    2. Calculate mean and median of all five clustering features.
    3. Assign descriptive financial archetype names.
    4. Update company-level cluster labels.
    5. Generate a Pearson correlation heatmap for 10 KPIs.
    6. Detect sector-relative outliers using absolute Z-score > 3.
    7. Calculate portfolio percentiles and descriptive statistics.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"

OUTPUT_DIR = PROJECT_ROOT / "output"
REPORTS_DIR = PROJECT_ROOT / "reports"

CLUSTER_FEATURES_PATH = (
    OUTPUT_DIR / "clustering_features.csv"
)

CLUSTER_LABELS_PATH = (
    OUTPUT_DIR / "cluster_labels.csv"
)

CLUSTER_PROFILES_PATH = (
    OUTPUT_DIR / "cluster_profiles.csv"
)

COMPANY_PROFILES_PATH = (
    OUTPUT_DIR / "company_cluster_profiles.csv"
)

OUTLIER_REPORT_PATH = (
    OUTPUT_DIR / "outlier_report.csv"
)

PORTFOLIO_STATS_PATH = (
    OUTPUT_DIR / "portfolio_stats.csv"
)

VALIDATION_SUMMARY_PATH = (
    OUTPUT_DIR / "day37_validation_summary.csv"
)

CORRELATION_HEATMAP_PATH = (
    REPORTS_DIR / "correlation_heatmap.png"
)


# =============================================================================
# CONFIGURATION
# =============================================================================

CLUSTER_FEATURES = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
]

CORE_KPIS = [
    "return_on_equity_pct",
    "operating_profit_margin_pct",
    "net_profit_margin_pct",
    "debt_to_equity",
    "interest_coverage",
    "asset_turnover",
    "free_cash_flow_cr",
    "earnings_per_share",
    "dividend_payout_ratio_pct",
    "composite_quality_score",
]

STAT_ORDER = [
    "P10",
    "P25",
    "P50",
    "P75",
    "P90",
    "Mean",
    "Std",
]

EXPECTED_COMPANY_COUNT = 92
EXPECTED_CLUSTER_COUNT = 5
OUTLIER_Z_THRESHOLD = 3.0


# =============================================================================
# GENERIC HELPERS
# =============================================================================

def normalize_column(value: object) -> str:
    """Normalize a column name to snake_case."""

    text = str(value).strip().lower()
    text = re.sub(r"[^\w]+", "_", text)

    return text.strip("_")


def safe_numeric(value: object) -> float:
    """Convert one financial value safely to float."""

    if value is None or pd.isna(value):
        return np.nan

    text = (
        str(value)
        .replace(",", "")
        .replace("%", "")
        .replace("₹", "")
        .strip()
    )

    if text.lower() in {
        "",
        "nan",
        "none",
        "null",
        "na",
        "n/a",
        "-",
    }:
        return np.nan

    try:
        return float(text)

    except (TypeError, ValueError):
        return np.nan


def extract_year(value: object) -> float:
    """Extract a four-digit year from project financial-year strings."""

    if value is None or pd.isna(value):
        return np.nan

    text = str(value).strip()

    match = re.search(
        r"(19|20)\d{2}",
        text,
    )

    if match:
        return float(
            match.group()
        )

    return np.nan


def clean_text(value: object) -> str:
    """Clean display text."""

    if value is None or pd.isna(value):
        return ""

    return (
        str(value)
        .replace("\n", " ")
        .strip()
    )


def ensure_directories() -> None:
    """Create output and report directories."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


# =============================================================================
# INPUT LOADERS
# =============================================================================

def load_clustering_features() -> pd.DataFrame:
    """Load the completed Day 36 clustering feature table."""

    if not CLUSTER_FEATURES_PATH.exists():
        raise FileNotFoundError(
            "Day 36 feature file not found: "
            f"{CLUSTER_FEATURES_PATH}"
        )

    df = pd.read_csv(
        CLUSTER_FEATURES_PATH
    )

    required = {
        "company_id",
        "company_name",
        "broad_sector",
        "cluster_id",
        "distance_from_centroid",
        *CLUSTER_FEATURES,
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            "Missing clustering feature columns: "
            + ", ".join(sorted(missing))
        )

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["cluster_id"] = pd.to_numeric(
        df["cluster_id"],
        errors="coerce",
    )

    for column in (
        CLUSTER_FEATURES
        + ["distance_from_centroid"]
    ):
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    return (
        df
        .sort_values("company_id")
        .reset_index(drop=True)
    )


def load_latest_ratios() -> pd.DataFrame:
    """Load the latest annual KPI row for each company."""

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    with sqlite3.connect(DB_PATH) as connection:
        ratios = pd.read_sql_query(
            """
            SELECT *
            FROM financial_ratios
            """,
            connection,
        )

    ratios.columns = [
        normalize_column(column)
        for column in ratios.columns
    ]

    ratios["company_id"] = (
        ratios["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    ratios["year_numeric"] = (
        ratios["year"]
        .apply(extract_year)
    )

    for column in CORE_KPIS:
        if column in ratios.columns:
            ratios[column] = (
                ratios[column]
                .apply(safe_numeric)
            )
        else:
            ratios[column] = np.nan

    ratios = ratios[
        ratios["year_numeric"].notna()
    ].copy()

    ratios["year_numeric"] = (
        ratios["year_numeric"]
        .astype(int)
    )

    ratios["_kpi_completeness"] = (
        ratios[CORE_KPIS]
        .notna()
        .sum(axis=1)
    )

    latest = (
        ratios
        .sort_values(
            [
                "company_id",
                "year_numeric",
                "_kpi_completeness",
            ],
            ascending=[
                True,
                True,
                False,
            ],
        )
        .drop_duplicates(
            subset=["company_id"],
            keep="last",
        )
        .drop(
            columns=["_kpi_completeness"]
        )
        .reset_index(drop=True)
    )

    return latest


# =============================================================================
# CLUSTER PROFILING
# =============================================================================

def calculate_cluster_profiles(
    company_df: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate cluster size, mean and median for all five features."""

    profile_records = []

    for cluster_id, group in (
        company_df.groupby(
            "cluster_id",
            sort=True,
        )
    ):
        record = {
            "cluster_id":
                int(cluster_id),

            "company_count":
                int(len(group)),

            "sector_count":
                int(
                    group["broad_sector"]
                    .nunique()
                ),

            "average_distance_from_centroid":
                float(
                    group[
                        "distance_from_centroid"
                    ].mean()
                ),

            "median_distance_from_centroid":
                float(
                    group[
                        "distance_from_centroid"
                    ].median()
                ),
        }

        for feature in CLUSTER_FEATURES:
            record[
                f"{feature}_mean"
            ] = float(
                group[feature].mean()
            )

            record[
                f"{feature}_median"
            ] = float(
                group[feature].median()
            )

        top_sectors = (
            group["broad_sector"]
            .fillna("Unknown")
            .value_counts()
            .head(3)
        )

        record["top_sectors"] = "; ".join(
            f"{sector} ({count})"
            for sector, count
            in top_sectors.items()
        )

        nearest_companies = (
            group
            .nsmallest(
                5,
                "distance_from_centroid",
            )["company_id"]
            .tolist()
        )

        record[
            "representative_companies"
        ] = ", ".join(
            nearest_companies
        )

        profile_records.append(
            record
        )

    return pd.DataFrame(
        profile_records
    ).sort_values(
        "cluster_id"
    ).reset_index(
        drop=True
    )


# =============================================================================
# CLUSTER NAMING
# =============================================================================

def calculate_profile_ranks(
    profiles: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate relative cluster ranks used for naming."""

    ranked = profiles.copy()

    rank_specs = {
        "roe_rank":
            "return_on_equity_pct_mean",

        "debt_rank":
            "debt_to_equity_mean",

        "revenue_growth_rank":
            "revenue_cagr_5yr_mean",

        "fcf_growth_rank":
            "fcf_cagr_5yr_mean",

        "margin_rank":
            "operating_profit_margin_pct_mean",
    }

    for rank_column, value_column in (
        rank_specs.items()
    ):
        ranked[rank_column] = (
            ranked[value_column]
            .rank(
                method="min",
                ascending=False,
            )
            .astype(int)
        )

    ranked[
        "low_debt_rank"
    ] = (
        ranked[
            "debt_to_equity_mean"
        ]
        .rank(
            method="min",
            ascending=True,
        )
        .astype(int)
    )

    return ranked


def score_cluster_archetypes(
    row: pd.Series,
) -> dict[str, float]:
    """Score one cluster against candidate financial archetypes."""

    roe = row[
        "return_on_equity_pct_mean"
    ]

    debt = row[
        "debt_to_equity_mean"
    ]

    revenue_growth = row[
        "revenue_cagr_5yr_mean"
    ]

    fcf_growth = row[
        "fcf_cagr_5yr_mean"
    ]

    margin = row[
        "operating_profit_margin_pct_mean"
    ]

    scores = {
        "High-Quality Compounders":
            (
                roe * 0.35
                + margin * 0.25
                + revenue_growth * 0.20
                + fcf_growth * 0.20
                - max(debt, 0) * 4
            ),

        "Defensive Cash Generators":
            (
                fcf_growth * 0.40
                + margin * 0.30
                + roe * 0.20
                - max(debt, 0) * 5
                - abs(revenue_growth) * 0.05
            ),

        "Value Cyclicals":
            (
                revenue_growth * 0.30
                + margin * 0.15
                + fcf_growth * 0.10
                + max(debt, 0) * 3
                - roe * 0.05
            ),

        "Leveraged or Turnaround":
            (
                max(debt, 0) * 8
                - roe * 0.15
                - fcf_growth * 0.15
                + revenue_growth * 0.10
            ),

        "Emerging Growth":
            (
                revenue_growth * 0.45
                + roe * 0.20
                + fcf_growth * 0.20
                + margin * 0.15
                - max(debt, 0) * 2
            ),
    }

    return scores


def assign_unique_cluster_names(
    profiles: pd.DataFrame,
) -> pd.DataFrame:
    """
    Assign one unique descriptive archetype name to each cluster.

    Names are selected from score-based preferences while ensuring
    every cluster receives a distinct label.
    """

    ranked = calculate_profile_ranks(
        profiles
    )

    archetypes = [
        "High-Quality Compounders",
        "Defensive Cash Generators",
        "Value Cyclicals",
        "Leveraged or Turnaround",
        "Emerging Growth",
    ]

    score_rows = []

    for _, row in ranked.iterrows():
        scores = score_cluster_archetypes(
            row
        )

        for archetype, score in scores.items():
            score_rows.append(
                {
                    "cluster_id":
                        int(
                            row[
                                "cluster_id"
                            ]
                        ),

                    "archetype":
                        archetype,

                    "score":
                        float(score),
                }
            )

    scores_df = pd.DataFrame(
        score_rows
    )

    assignments = {}
    used_names = set()

    # Assign strongest cluster/archetype combinations first.
    for _, candidate in (
        scores_df
        .sort_values(
            "score",
            ascending=False,
        )
        .iterrows()
    ):
        cluster_id = int(
            candidate["cluster_id"]
        )

        archetype = candidate[
            "archetype"
        ]

        if (
            cluster_id not in assignments
            and archetype not in used_names
        ):
            assignments[
                cluster_id
            ] = archetype

            used_names.add(
                archetype
            )

    # Defensive fallback.
    unassigned_clusters = [
        int(cluster_id)
        for cluster_id in ranked[
            "cluster_id"
        ]
        if int(cluster_id)
        not in assignments
    ]

    unused_names = [
        name
        for name in archetypes
        if name not in used_names
    ]

    for cluster_id, name in zip(
        unassigned_clusters,
        unused_names,
    ):
        assignments[
            cluster_id
        ] = name

    ranked[
        "cluster_name"
    ] = ranked[
        "cluster_id"
    ].map(
        assignments
    )

    ranked[
        "cluster_description"
    ] = ranked.apply(
        build_cluster_description,
        axis=1,
    )

    return ranked


def build_cluster_description(
    row: pd.Series,
) -> str:
    """Build a compact business description for one cluster."""

    characteristics = []

    if row[
        "roe_rank"
    ] == 1:
        characteristics.append(
            "highest average ROE"
        )

    if row[
        "margin_rank"
    ] == 1:
        characteristics.append(
            "highest operating margins"
        )

    if row[
        "revenue_growth_rank"
    ] == 1:
        characteristics.append(
            "strongest revenue growth"
        )

    if row[
        "fcf_growth_rank"
    ] == 1:
        characteristics.append(
            "strongest FCF growth"
        )

    if row[
        "low_debt_rank"
    ] == 1:
        characteristics.append(
            "lowest leverage"
        )

    if row[
        "debt_rank"
    ] == 1:
        characteristics.append(
            "highest leverage"
        )

    if not characteristics:
        characteristics.append(
            "balanced financial characteristics"
        )

    return (
        f"{row['cluster_name']}: "
        + ", ".join(characteristics)
        + "."
    )


# =============================================================================
# COMPANY-LEVEL CLUSTER OUTPUT
# =============================================================================

def build_company_profiles(
    company_df: pd.DataFrame,
    cluster_profiles: pd.DataFrame,
) -> pd.DataFrame:
    """Attach final cluster names and descriptions to all companies."""

    profile_columns = [
        "cluster_id",
        "cluster_name",
        "cluster_description",
        "company_count",
        "representative_companies",
    ]

    final = company_df.drop(
        columns=[
            "cluster_name",
        ],
        errors="ignore",
    ).merge(
        cluster_profiles[
            profile_columns
        ],
        on="cluster_id",
        how="left",
        validate="many_to_one",
    )

    ordered_columns = [
        "company_id",
        "company_name",
        "broad_sector",
        "sub_sector",
        "cluster_id",
        "cluster_name",
        "cluster_description",
        "distance_from_centroid",
        *CLUSTER_FEATURES,
        "company_count",
        "representative_companies",
    ]

    available_columns = [
        column
        for column in ordered_columns
        if column in final.columns
    ]

    return (
        final[
            available_columns
        ]
        .sort_values("company_id")
        .reset_index(drop=True)
    )


# =============================================================================
# CORRELATION HEATMAP
# =============================================================================

def prepare_latest_kpi_dataset(
    company_profiles: pd.DataFrame,
    latest_ratios: pd.DataFrame,
) -> pd.DataFrame:
    """
    Combine company metadata with latest KPI values.

    Day 36 repaired ROE and Operating Profit Margin values take
    precedence over raw values from the financial_ratios table.
    """

    official_ids = set(
        company_profiles[
            "company_id"
        ]
    )

    latest_ratios = latest_ratios[
        latest_ratios[
            "company_id"
        ].isin(
            official_ids
        )
    ].copy()

    # Keep repaired Day 36 values under temporary names.
    company_metadata = (
        company_profiles[
            [
                "company_id",
                "company_name",
                "broad_sector",
                "cluster_id",
                "cluster_name",
                "return_on_equity_pct",
                "operating_profit_margin_pct",
            ]
        ]
        .drop_duplicates(
            subset=["company_id"]
        )
        .rename(
            columns={
                "return_on_equity_pct":
                    "repaired_return_on_equity_pct",

                "operating_profit_margin_pct":
                    "repaired_operating_profit_margin_pct",
            }
        )
    )

    latest = company_metadata.merge(
        latest_ratios[
            [
                "company_id",
                "year",
                "year_numeric",
                *CORE_KPIS,
            ]
        ],
        on="company_id",
        how="left",
        validate="one_to_one",
    )

    # Day 36 repaired values override raw ratio-table values.
    latest[
        "return_on_equity_pct"
    ] = pd.to_numeric(
        latest[
            "repaired_return_on_equity_pct"
        ],
        errors="coerce",
    )

    latest[
        "operating_profit_margin_pct"
    ] = pd.to_numeric(
        latest[
            "repaired_operating_profit_margin_pct"
        ],
        errors="coerce",
    )

    latest = latest.drop(
        columns=[
            "repaired_return_on_equity_pct",
            "repaired_operating_profit_margin_pct",
        ]
    )

    return latest


def generate_correlation_heatmap(
    latest_kpis: pd.DataFrame,
) -> pd.DataFrame:
    """Generate annotated Pearson correlation heatmap for 10 KPIs."""

    numeric = latest_kpis[
        CORE_KPIS
    ].copy()

    for column in CORE_KPIS:
        numeric[column] = pd.to_numeric(
            numeric[column],
            errors="coerce",
        )

    correlation = numeric.corr(
        method="pearson"
    )

    display_labels = {
        "return_on_equity_pct":
            "ROE",

        "operating_profit_margin_pct":
            "OPM",

        "net_profit_margin_pct":
            "NPM",

        "debt_to_equity":
            "Debt/Equity",

        "interest_coverage":
            "Interest Coverage",

        "asset_turnover":
            "Asset Turnover",

        "free_cash_flow_cr":
            "Free Cash Flow",

        "earnings_per_share":
            "EPS",

        "dividend_payout_ratio_pct":
            "Dividend Payout",

        "composite_quality_score":
            "Quality Score",
    }

    display_correlation = correlation.rename(
        index=display_labels,
        columns=display_labels,
    )

    plt.figure(
        figsize=(14, 11)
    )

    sns.heatmap(
        display_correlation,
        annot=True,
        fmt=".2f",
        linewidths=0.5,
        square=True,
        cbar_kws={
            "label":
                "Pearson Correlation",
        },
        vmin=-1,
        vmax=1,
        center=0,
    )

    plt.title(
        "Nifty 100 — Latest-Year KPI Correlation Matrix",
        fontsize=15,
        pad=18,
    )

    plt.xticks(
        rotation=45,
        ha="right",
    )

    plt.yticks(
        rotation=0,
    )

    plt.tight_layout()

    plt.savefig(
        CORRELATION_HEATMAP_PATH,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    return correlation


# =============================================================================
# OUTLIER DETECTION
# =============================================================================

def calculate_sector_z_scores(
    latest_kpis: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate Z-scores for each KPI inside each broad sector.

    Companies are flagged when any valid absolute sector-relative
    Z-score exceeds 3.
    """

    working = latest_kpis.copy()

    for metric in CORE_KPIS:
        working[
            f"{metric}_zscore"
        ] = np.nan

        for sector, sector_group in (
            working.groupby(
                "broad_sector",
                dropna=False,
            )
        ):
            values = pd.to_numeric(
                sector_group[metric],
                errors="coerce",
            )

            valid_values = values.dropna()

            if len(valid_values) < 3:
                continue

            standard_deviation = (
                valid_values.std(
                    ddof=0
                )
            )

            if (
                pd.isna(
                    standard_deviation
                )
                or standard_deviation == 0
            ):
                continue

            mean_value = (
                valid_values.mean()
            )

            z_scores = (
                values
                - mean_value
            ) / standard_deviation

            working.loc[
                sector_group.index,
                f"{metric}_zscore",
            ] = z_scores

    return working


def build_outlier_report(
    zscore_df: pd.DataFrame,
) -> pd.DataFrame:
    """Create one row for each company-metric outlier."""

    outlier_records = []

    for _, row in zscore_df.iterrows():
        for metric in CORE_KPIS:
            z_column = (
                f"{metric}_zscore"
            )

            z_score = row.get(
                z_column
            )

            if (
                pd.notna(z_score)
                and abs(z_score)
                > OUTLIER_Z_THRESHOLD
            ):
                direction = (
                    "High"
                    if z_score > 0
                    else "Low"
                )

                outlier_records.append(
                    {
                        "company_id":
                            row[
                                "company_id"
                            ],

                        "company_name":
                            row[
                                "company_name"
                            ],

                        "broad_sector":
                            row[
                                "broad_sector"
                            ],

                        "cluster_id":
                            row[
                                "cluster_id"
                            ],

                        "cluster_name":
                            row[
                                "cluster_name"
                            ],

                        "metric":
                            metric,

                        "metric_value":
                            row[
                                metric
                            ],

                        "sector_zscore":
                            float(z_score),

                        "absolute_zscore":
                            float(
                                abs(z_score)
                            ),

                        "direction":
                            direction,

                        "threshold":
                            OUTLIER_Z_THRESHOLD,
                    }
                )

    columns = [
        "company_id",
        "company_name",
        "broad_sector",
        "cluster_id",
        "cluster_name",
        "metric",
        "metric_value",
        "sector_zscore",
        "absolute_zscore",
        "direction",
        "threshold",
    ]

    report = pd.DataFrame(
        outlier_records,
        columns=columns,
    )

    if not report.empty:
        report = (
            report
            .sort_values(
                [
                    "absolute_zscore",
                    "company_id",
                ],
                ascending=[
                    False,
                    True,
                ],
            )
            .reset_index(drop=True)
        )

    return report


# =============================================================================
# PORTFOLIO STATISTICS
# =============================================================================

def calculate_portfolio_statistics(
    latest_kpis: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate P10–P90, mean and standard deviation for each KPI."""

    records = []

    for metric in CORE_KPIS:
        values = pd.to_numeric(
            latest_kpis[metric],
            errors="coerce",
        ).dropna()

        if values.empty:
            statistics = {
                "P10":
                    np.nan,

                "P25":
                    np.nan,

                "P50":
                    np.nan,

                "P75":
                    np.nan,

                "P90":
                    np.nan,

                "Mean":
                    np.nan,

                "Std":
                    np.nan,
            }

        else:
            statistics = {
                "P10":
                    values.quantile(0.10),

                "P25":
                    values.quantile(0.25),

                "P50":
                    values.quantile(0.50),

                "P75":
                    values.quantile(0.75),

                "P90":
                    values.quantile(0.90),

                "Mean":
                    values.mean(),

                "Std":
                    values.std(ddof=1),
            }

        record = {
            "kpi":
                metric,

            "available_company_count":
                int(values.count()),

            "missing_company_count":
                int(
                    EXPECTED_COMPANY_COUNT
                    - values.count()
                ),
        }

        record.update(
            statistics
        )

        records.append(
            record
        )

    columns = [
        "kpi",
        "available_company_count",
        "missing_company_count",
        *STAT_ORDER,
    ]

    return pd.DataFrame(
        records
    )[columns]


# =============================================================================
# VALIDATION
# =============================================================================

def validate_day37(
    cluster_profiles: pd.DataFrame,
    company_profiles: pd.DataFrame,
    outlier_report: pd.DataFrame,
    portfolio_stats: pd.DataFrame,
    correlation_matrix: pd.DataFrame,
) -> tuple[pd.DataFrame, bool]:
    """Validate all Day 37 deliverables."""

    checks = []

    def add_check(
        check_name: str,
        expected: object,
        actual: object,
        passed: bool,
    ) -> None:
        checks.append(
            {
                "check":
                    check_name,

                "expected":
                    expected,

                "actual":
                    actual,

                "status":
                    (
                        "PASS"
                        if passed
                        else "FAIL"
                    ),
            }
        )

    add_check(
        "Cluster count",
        EXPECTED_CLUSTER_COUNT,
        cluster_profiles[
            "cluster_id"
        ].nunique(),
        cluster_profiles[
            "cluster_id"
        ].nunique()
        == EXPECTED_CLUSTER_COUNT,
    )

    add_check(
        "Unique cluster names",
        EXPECTED_CLUSTER_COUNT,
        cluster_profiles[
            "cluster_name"
        ].nunique(),
        cluster_profiles[
            "cluster_name"
        ].nunique()
        == EXPECTED_CLUSTER_COUNT,
    )

    add_check(
        "Company count",
        EXPECTED_COMPANY_COUNT,
        len(company_profiles),
        len(company_profiles)
        == EXPECTED_COMPANY_COUNT,
    )

    add_check(
        "Unique company count",
        EXPECTED_COMPANY_COUNT,
        company_profiles[
            "company_id"
        ].nunique(),
        company_profiles[
            "company_id"
        ].nunique()
        == EXPECTED_COMPANY_COUNT,
    )

    add_check(
        "Missing cluster names",
        0,
        int(
            company_profiles[
                "cluster_name"
            ].isna().sum()
        ),
        company_profiles[
            "cluster_name"
        ].isna().sum()
        == 0,
    )

    add_check(
        "Cluster membership reconciliation",
        EXPECTED_COMPANY_COUNT,
        int(
            cluster_profiles[
                "company_count"
            ].sum()
        ),
        cluster_profiles[
            "company_count"
        ].sum()
        == EXPECTED_COMPANY_COUNT,
    )

    add_check(
        "Portfolio KPI row count",
        len(CORE_KPIS),
        len(portfolio_stats),
        len(portfolio_stats)
        == len(CORE_KPIS),
    )

    add_check(
        "Correlation matrix dimensions",
        f"{len(CORE_KPIS)}x{len(CORE_KPIS)}",
        (
            f"{correlation_matrix.shape[0]}"
            f"x{correlation_matrix.shape[1]}"
        ),
        correlation_matrix.shape
        == (
            len(CORE_KPIS),
            len(CORE_KPIS),
        ),
    )

    invalid_outliers = 0

    if not outlier_report.empty:
        invalid_outliers = int(
            (
                outlier_report[
                    "absolute_zscore"
                ]
                <= OUTLIER_Z_THRESHOLD
            ).sum()
        )

    add_check(
        "Invalid outlier rows",
        0,
        invalid_outliers,
        invalid_outliers == 0,
    )

    output_files = [
        CLUSTER_PROFILES_PATH,
        COMPANY_PROFILES_PATH,
        OUTLIER_REPORT_PATH,
        PORTFOLIO_STATS_PATH,
        CORRELATION_HEATMAP_PATH,
    ]

    missing_files = [
        str(path)
        for path in output_files
        if not path.exists()
    ]

    add_check(
        "Missing output files",
        0,
        len(missing_files),
        len(missing_files) == 0,
    )

    validation_df = pd.DataFrame(
        checks
    )

    passed = (
        validation_df[
            "status"
        ]
        .eq("PASS")
        .all()
    )

    return (
        validation_df,
        bool(passed),
    )


# =============================================================================
# SAVE OUTPUTS
# =============================================================================

def save_outputs(
    cluster_profiles: pd.DataFrame,
    company_profiles: pd.DataFrame,
    outlier_report: pd.DataFrame,
    portfolio_stats: pd.DataFrame,
) -> None:
    """Save all required Day 37 CSV outputs."""

    cluster_profiles.to_csv(
        CLUSTER_PROFILES_PATH,
        index=False,
    )

    company_profiles.to_csv(
        COMPANY_PROFILES_PATH,
        index=False,
    )

    outlier_report.to_csv(
        OUTLIER_REPORT_PATH,
        index=False,
    )

    portfolio_stats.to_csv(
        PORTFOLIO_STATS_PATH,
        index=False,
    )

    # Update the required Day 36 cluster-label file with the
    # final descriptive Day 37 names.
    updated_labels = company_profiles[
        [
            "company_id",
            "cluster_id",
            "cluster_name",
            "distance_from_centroid",
        ]
    ].copy()

    updated_labels.to_csv(
        CLUSTER_LABELS_PATH,
        index=False,
    )


# =============================================================================
# TERMINAL DISPLAY
# =============================================================================

def print_header(
    title: str,
    width: int = 110,
) -> None:
    """Print a terminal header."""

    print("=" * width)
    print(title)
    print("=" * width)


def print_section(
    title: str,
    width: int = 110,
) -> None:
    """Print a terminal section."""

    print(
        "\n"
        + title
    )

    print("-" * width)


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    """Run the complete Sprint 6 Day 37 analytics workflow."""

    ensure_directories()

    print_header(
        "SPRINT 6 — DAY 37 CLUSTER PROFILING & STATISTICS"
    )

    # -------------------------------------------------------------------------
    # Load Day 36 data
    # -------------------------------------------------------------------------

    company_features = (
        load_clustering_features()
    )

    latest_ratios = (
        load_latest_ratios()
    )

    print(
        f"\nClustering companies : "
        f"{len(company_features)}"
    )

    print(
        f"Unique clusters      : "
        f"{company_features['cluster_id'].nunique()}"
    )

    print(
        f"Latest ratio rows    : "
        f"{len(latest_ratios)}"
    )

    # -------------------------------------------------------------------------
    # Cluster profiling
    # -------------------------------------------------------------------------

    raw_profiles = (
        calculate_cluster_profiles(
            company_features
        )
    )

    cluster_profiles = (
        assign_unique_cluster_names(
            raw_profiles
        )
    )

    company_profiles = (
        build_company_profiles(
            company_features,
            cluster_profiles,
        )
    )

    # -------------------------------------------------------------------------
    # KPI analytics
    # -------------------------------------------------------------------------

    latest_kpis = (
        prepare_latest_kpi_dataset(
            company_profiles,
            latest_ratios,
        )
    )
    
        # -------------------------------------------------------------------------
    # KPI usability audit
    # -------------------------------------------------------------------------

    print_section(
        "KPI USABILITY AUDIT"
    )

    unusable_kpis = []

    for metric in CORE_KPIS:

        metric_values = pd.to_numeric(
            latest_kpis[metric],
            errors="coerce",
        ).dropna()

        unique_value_count = int(
            metric_values.nunique()
        )

        if unique_value_count <= 1:

            unusable_kpis.append(
                metric
            )

            print(
                f"WARNING: {metric} has only "
                f"{unique_value_count} unique value(s)."
            )

    if not unusable_kpis:
        print(
            "All 10 KPIs contain usable variation."
        )

    correlation_matrix = (
        generate_correlation_heatmap(
            latest_kpis
        )
    )

    zscore_dataset = (
        calculate_sector_z_scores(
            latest_kpis
        )
    )

    outlier_report = (
        build_outlier_report(
            zscore_dataset
        )
    )

    portfolio_stats = (
        calculate_portfolio_statistics(
            latest_kpis
        )
    )

    # -------------------------------------------------------------------------
    # Save required outputs
    # -------------------------------------------------------------------------

    save_outputs(
        cluster_profiles,
        company_profiles,
        outlier_report,
        portfolio_stats,
    )

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    (
        validation_summary,
        validation_passed,
    ) = validate_day37(
        cluster_profiles,
        company_profiles,
        outlier_report,
        portfolio_stats,
        correlation_matrix,
    )

    validation_summary.to_csv(
        VALIDATION_SUMMARY_PATH,
        index=False,
    )

    # -------------------------------------------------------------------------
    # Terminal output
    # -------------------------------------------------------------------------

    print_section(
        "CLUSTER PROFILES"
    )

    profile_display_columns = [
        "cluster_id",
        "cluster_name",
        "company_count",
        "return_on_equity_pct_mean",
        "debt_to_equity_mean",
        "revenue_cagr_5yr_mean",
        "fcf_cagr_5yr_mean",
        "operating_profit_margin_pct_mean",
        "representative_companies",
    ]

    print(
        cluster_profiles[
            profile_display_columns
        ]
        .round(2)
        .to_string(index=False)
    )

    print_section(
        "CLUSTER DESCRIPTIONS"
    )

    print(
        cluster_profiles[
            [
                "cluster_id",
                "cluster_name",
                "cluster_description",
                "top_sectors",
            ]
        ]
        .to_string(index=False)
    )

    print_section(
        "COMPANY DISTRIBUTION"
    )

    print(
        company_profiles[
            "cluster_name"
        ]
        .value_counts()
        .to_string()
    )

    print_section(
        "OUTLIER SUMMARY"
    )

    print(
        f"Outlier rows       : "
        f"{len(outlier_report)}"
    )

    print(
        f"Outlier companies  : "
        f"{outlier_report['company_id'].nunique() if not outlier_report.empty else 0}"
    )

    if not outlier_report.empty:
        print(
            "\nTop outliers:"
        )

        print(
            outlier_report[
                [
                    "company_id",
                    "broad_sector",
                    "metric",
                    "metric_value",
                    "sector_zscore",
                    "direction",
                ]
            ]
            .head(20)
            .round(3)
            .to_string(index=False)
        )

    print_section(
        "PORTFOLIO STATISTICS"
    )

    print(
        portfolio_stats
        .round(3)
        .to_string(index=False)
    )

    print_section(
        "DAY 37 VALIDATION"
    )

    print(
        validation_summary.to_string(
            index=False
        )
    )

    print_section(
        "OUTPUT FILES"
    )

    print(
        f"Cluster profiles:"
        f"\n{CLUSTER_PROFILES_PATH.resolve()}"
    )

    print(
        f"\nCompany cluster profiles:"
        f"\n{COMPANY_PROFILES_PATH.resolve()}"
    )

    print(
        f"\nUpdated cluster labels:"
        f"\n{CLUSTER_LABELS_PATH.resolve()}"
    )

    print(
        f"\nOutlier report:"
        f"\n{OUTLIER_REPORT_PATH.resolve()}"
    )

    print(
        f"\nPortfolio statistics:"
        f"\n{PORTFOLIO_STATS_PATH.resolve()}"
    )

    print(
        f"\nCorrelation heatmap:"
        f"\n{CORRELATION_HEATMAP_PATH.resolve()}"
    )

    print(
        f"\nValidation summary:"
        f"\n{VALIDATION_SUMMARY_PATH.resolve()}"
    )

    print("\n")

    if validation_passed:
        print_header(
            "SPRINT 6 — DAY 37 COMPLETE"
        )

    else:
        print_header(
            "SPRINT 6 — DAY 37 REQUIRES REVIEW"
        )

        raise RuntimeError(
            "Day 37 validation failed."
        )


if __name__ == "__main__":
    main()