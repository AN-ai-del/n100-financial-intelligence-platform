"""
Sprint 4 - Day 26
Valuation Analysis Engine

Creates:
1. output/valuation_summary.xlsx
2. output/valuation_flags.csv

The module uses the supplied project database only.
No valuation data is fabricated.
"""

from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

SUMMARY_PATH = OUTPUT_DIR / "valuation_summary.xlsx"
FLAGS_PATH = OUTPUT_DIR / "valuation_flags.csv"


# ============================================================
# HELPERS
# ============================================================

def clean_numeric(series: pd.Series) -> pd.Series:
    """
    Convert a pandas Series safely to numeric.
    Non-numeric values become NaN.
    """
    return pd.to_numeric(series, errors="coerce")


def extract_year(value) -> float:
    """
    Convert values such as:
        'Mar 2024'
        'Dec 2012'
        2024
    into a numeric year.
    """
    if pd.isna(value):
        return np.nan

    text = str(value).strip()

    year = pd.to_numeric(text, errors="coerce")

    if not pd.isna(year):
        return float(year)

    extracted = pd.Series([text]).str.extract(r"(\d{4})")[0].iloc[0]

    if pd.isna(extracted):
        return np.nan

    return float(extracted)


def percentile_score(
    series: pd.Series,
    higher_is_better: bool = True,
) -> pd.Series:
    """
    Convert values into percentile scores from 0 to 100.
    """
    numeric = clean_numeric(series)

    if numeric.notna().sum() == 0:
        return pd.Series(np.nan, index=series.index)

    percentile = numeric.rank(
        pct=True,
        method="average",
        ascending=higher_is_better,
    )

    if higher_is_better:
        return percentile * 100

    return (1 - percentile + (1 / numeric.notna().sum())) * 100


def classify_valuation(row: pd.Series) -> str:
    """
    Classifies each company using valuation percentile scores.

    Lower P/E, P/B and EV/EBITDA are considered cheaper.
    Higher dividend yield is considered more attractive.
    """

    score = row.get("valuation_score")

    if pd.isna(score):
        return "Insufficient Data"

    if score >= 70:
        return "Attractive Valuation"

    if score >= 40:
        return "Fairly Valued"

    return "Expensive Valuation"


def build_flag_reasons(row: pd.Series) -> list[str]:
    """
    Generate valuation-related flag explanations.
    """

    flags = []

    pe = row.get("pe_ratio")
    pb = row.get("pb_ratio")
    ev = row.get("ev_ebitda")
    dividend = row.get("dividend_yield_pct")

    pe_sector = row.get("sector_median_pe")
    pb_sector = row.get("sector_median_pb")
    ev_sector = row.get("sector_median_ev_ebitda")

    if pd.notna(pe) and pd.notna(pe_sector):
        if pe > pe_sector * 1.5:
            flags.append("P/E substantially above sector median")
        elif pe < pe_sector * 0.7:
            flags.append("P/E substantially below sector median")

    if pd.notna(pb) and pd.notna(pb_sector):
        if pb > pb_sector * 1.5:
            flags.append("P/B substantially above sector median")
        elif pb < pb_sector * 0.7:
            flags.append("P/B substantially below sector median")

    if pd.notna(ev) and pd.notna(ev_sector):
        if ev > ev_sector * 1.5:
            flags.append("EV/EBITDA substantially above sector median")
        elif ev < ev_sector * 0.7:
            flags.append("EV/EBITDA substantially below sector median")

    if pd.notna(dividend):
        if dividend >= 3:
            flags.append("High dividend yield")
        elif dividend == 0:
            flags.append("No dividend yield")

    return flags


# ============================================================
# DATA LOADING
# ============================================================

def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load required project tables from SQLite.
    """

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    connection = sqlite3.connect(DB_PATH)

    try:
        companies = pd.read_sql_query(
            """
            SELECT
                id AS company_id,
                company_name,
                roce_percentage,
                roe_percentage
            FROM companies
            """,
            connection,
        )

        ratios = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                net_profit_margin_pct,
                operating_profit_margin_pct,
                return_on_equity_pct,
                debt_to_equity,
                interest_coverage,
                asset_turnover,
                free_cash_flow_cr,
                earnings_per_share,
                book_value_per_share,
                broad_sector,
                sub_sector,
                composite_quality_score
            FROM financial_ratios
            """,
            connection,
        )

        market_cap = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                market_cap_crore,
                enterprise_value_crore,
                pe_ratio,
                pb_ratio,
                ev_ebitda,
                dividend_yield_pct
            FROM market_cap
            """,
            connection,
        )

    finally:
        connection.close()

    return companies, ratios, market_cap


# ============================================================
# LATEST RECORD SELECTION
# ============================================================

def prepare_latest_ratios(ratios: pd.DataFrame) -> pd.DataFrame:
    """
    Select the latest available financial-ratio record per company.
    """

    df = ratios.copy()

    df["year_numeric"] = df["year"].apply(extract_year)

    df = df.sort_values(
        ["company_id", "year_numeric"],
        ascending=[True, False],
        na_position="last",
    )

    df = df.drop_duplicates(
        subset=["company_id"],
        keep="first",
    )

    return df


def prepare_latest_market_cap(
    market_cap: pd.DataFrame,
) -> pd.DataFrame:
    """
    Select the latest available market-cap record per company.
    """

    df = market_cap.copy()

    df["year_numeric"] = df["year"].apply(extract_year)

    df = df.sort_values(
        ["company_id", "year_numeric"],
        ascending=[True, False],
        na_position="last",
    )

    df = df.drop_duplicates(
        subset=["company_id"],
        keep="first",
    )

    return df


# ============================================================
# VALUATION ENGINE
# ============================================================

def build_valuation_dataset() -> pd.DataFrame:
    companies, ratios, market_cap = load_data()

    latest_ratios = prepare_latest_ratios(ratios)
    latest_market = prepare_latest_market_cap(market_cap)

    # Avoid duplicate year columns after merge.
    latest_ratios = latest_ratios.rename(
        columns={
            "year": "financial_year",
            "year_numeric": "financial_year_numeric",
        }
    )

    latest_market = latest_market.rename(
        columns={
            "year": "valuation_year",
            "year_numeric": "valuation_year_numeric",
        }
    )

    df = (
        companies
        .merge(
            latest_ratios,
            on="company_id",
            how="left",
        )
        .merge(
            latest_market,
            on="company_id",
            how="left",
        )
    )

    numeric_columns = [
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "free_cash_flow_cr",
        "earnings_per_share",
        "book_value_per_share",
        "composite_quality_score",
        "market_cap_crore",
        "enterprise_value_crore",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "dividend_yield_pct",
        "roce_percentage",
        "roe_percentage",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = clean_numeric(df[column])

    # --------------------------------------------------------
    # Remove impossible valuation ratios from scoring.
    # Negative ratios can result from loss-making businesses
    # and should not automatically be interpreted as "cheap."
    # --------------------------------------------------------

    for column in [
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
    ]:
        df[f"{column}_for_scoring"] = df[column].where(
            df[column] > 0
        )

    # --------------------------------------------------------
    # Sector medians
    # --------------------------------------------------------

    sector_group = df.groupby(
        "broad_sector",
        dropna=False,
    )

    df["sector_median_pe"] = sector_group[
        "pe_ratio_for_scoring"
    ].transform("median")

    df["sector_median_pb"] = sector_group[
        "pb_ratio_for_scoring"
    ].transform("median")

    df["sector_median_ev_ebitda"] = sector_group[
        "ev_ebitda_for_scoring"
    ].transform("median")

    df["sector_median_dividend_yield"] = sector_group[
        "dividend_yield_pct"
    ].transform("median")

    # --------------------------------------------------------
    # Relative valuation ratios
    # --------------------------------------------------------

    df["pe_vs_sector"] = (
        df["pe_ratio_for_scoring"]
        / df["sector_median_pe"]
    )

    df["pb_vs_sector"] = (
        df["pb_ratio_for_scoring"]
        / df["sector_median_pb"]
    )

    df["ev_ebitda_vs_sector"] = (
        df["ev_ebitda_for_scoring"]
        / df["sector_median_ev_ebitda"]
    )

    # --------------------------------------------------------
    # Percentile scores
    # Lower valuation multiples = better valuation score.
    # Higher dividend yield = better valuation score.
    # --------------------------------------------------------

    df["pe_score"] = percentile_score(
        df["pe_ratio_for_scoring"],
        higher_is_better=False,
    )

    df["pb_score"] = percentile_score(
        df["pb_ratio_for_scoring"],
        higher_is_better=False,
    )

    df["ev_ebitda_score"] = percentile_score(
        df["ev_ebitda_for_scoring"],
        higher_is_better=False,
    )

    df["dividend_yield_score"] = percentile_score(
        df["dividend_yield_pct"],
        higher_is_better=True,
    )

    # --------------------------------------------------------
    # Composite valuation score
    #
    # P/E          = 35%
    # P/B          = 25%
    # EV/EBITDA    = 25%
    # Dividend     = 15%
    #
    # Missing metrics are handled using weighted averaging
    # rather than filling values artificially.
    # --------------------------------------------------------

    score_columns = {
        "pe_score": 0.35,
        "pb_score": 0.25,
        "ev_ebitda_score": 0.25,
        "dividend_yield_score": 0.15,
    }

    weighted_sum = pd.Series(
        0.0,
        index=df.index,
    )

    available_weight = pd.Series(
        0.0,
        index=df.index,
    )

    for column, weight in score_columns.items():
        mask = df[column].notna()

        weighted_sum.loc[mask] += (
            df.loc[mask, column] * weight
        )

        available_weight.loc[mask] += weight

    df["valuation_score"] = (
        weighted_sum / available_weight.replace(0, np.nan)
    )

    df["valuation_score"] = df[
        "valuation_score"
    ].round(2)

    df["valuation_category"] = df.apply(
        classify_valuation,
        axis=1,
    )

    # --------------------------------------------------------
    # Quality + valuation context
    # --------------------------------------------------------

    df["quality_adjusted_valuation"] = np.where(
        (
            (df["valuation_score"] >= 60)
            & (df["return_on_equity_pct"] >= 15)
            & (df["net_profit_margin_pct"] > 0)
        ),
        "Potential Value + Quality",
        np.where(
            (
                (df["valuation_score"] < 35)
                & (df["return_on_equity_pct"] >= 15)
            ),
            "Quality at Premium",
            "Neutral",
        ),
    )

    return df


# ============================================================
# FLAGS
# ============================================================

def build_flags(df: pd.DataFrame) -> pd.DataFrame:
    records = []

    for _, row in df.iterrows():

        reasons = build_flag_reasons(row)

        if not reasons:
            continue

        for reason in reasons:

            if "above sector median" in reason:
                flag_type = "Potential Overvaluation"

            elif "below sector median" in reason:
                flag_type = "Potential Undervaluation"

            elif reason == "High dividend yield":
                flag_type = "Income Opportunity"

            elif reason == "No dividend yield":
                flag_type = "Dividend Flag"

            else:
                flag_type = "Valuation Flag"

            records.append(
                {
                    "company_id": row["company_id"],
                    "company_name": row["company_name"],
                    "broad_sector": row["broad_sector"],
                    "valuation_year": row["valuation_year"],
                    "flag_type": flag_type,
                    "flag_reason": reason,
                    "pe_ratio": row["pe_ratio"],
                    "pb_ratio": row["pb_ratio"],
                    "ev_ebitda": row["ev_ebitda"],
                    "dividend_yield_pct": row[
                        "dividend_yield_pct"
                    ],
                    "valuation_score": row[
                        "valuation_score"
                    ],
                    "valuation_category": row[
                        "valuation_category"
                    ],
                }
            )

    return pd.DataFrame(records)


# ============================================================
# EXPORT
# ============================================================

def export_summary(df: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary_columns = [
        "company_id",
        "company_name",
        "broad_sector",
        "sub_sector",
        "valuation_year",
        "financial_year",
        "market_cap_crore",
        "enterprise_value_crore",
        "pe_ratio",
        "sector_median_pe",
        "pe_vs_sector",
        "pb_ratio",
        "sector_median_pb",
        "pb_vs_sector",
        "ev_ebitda",
        "sector_median_ev_ebitda",
        "ev_ebitda_vs_sector",
        "dividend_yield_pct",
        "sector_median_dividend_yield",
        "return_on_equity_pct",
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "debt_to_equity",
        "free_cash_flow_cr",
        "composite_quality_score",
        "pe_score",
        "pb_score",
        "ev_ebitda_score",
        "dividend_yield_score",
        "valuation_score",
        "valuation_category",
        "quality_adjusted_valuation",
    ]

    existing_columns = [
        column
        for column in summary_columns
        if column in df.columns
    ]

    summary = df[
        existing_columns
    ].copy()

    summary = summary.sort_values(
        "valuation_score",
        ascending=False,
        na_position="last",
    )

    sector_summary = (
        summary.groupby(
            "broad_sector",
            dropna=False,
        )
        .agg(
            companies=("company_id", "count"),
            median_pe=("pe_ratio", "median"),
            median_pb=("pb_ratio", "median"),
            median_ev_ebitda=("ev_ebitda", "median"),
            median_dividend_yield=(
                "dividend_yield_pct",
                "median",
            ),
            median_valuation_score=(
                "valuation_score",
                "median",
            ),
        )
        .reset_index()
    )

    category_summary = (
        summary[
            "valuation_category"
        ]
        .value_counts(
            dropna=False
        )
        .rename_axis(
            "valuation_category"
        )
        .reset_index(
            name="companies"
        )
    )

    with pd.ExcelWriter(
        SUMMARY_PATH,
        engine="openpyxl",
    ) as writer:

        summary.to_excel(
            writer,
            sheet_name="Company Valuation",
            index=False,
        )

        sector_summary.to_excel(
            writer,
            sheet_name="Sector Summary",
            index=False,
        )

        category_summary.to_excel(
            writer,
            sheet_name="Valuation Categories",
            index=False,
        )

        # ----------------------------------------------------
        # Basic workbook formatting
        # ----------------------------------------------------

        workbook = writer.book

        for worksheet in workbook.worksheets:

            worksheet.freeze_panes = "A2"

            for column_cells in worksheet.columns:
                max_length = 0

                column_letter = column_cells[0].column_letter

                for cell in column_cells:
                    try:
                        value_length = len(
                            str(cell.value)
                        )

                        max_length = max(
                            max_length,
                            value_length,
                        )

                    except Exception:
                        pass

                worksheet.column_dimensions[
                    column_letter
                ].width = min(
                    max(max_length + 2, 12),
                    35,
                )


def export_flags(flags: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if flags.empty:
        flags = pd.DataFrame(
            columns=[
                "company_id",
                "company_name",
                "broad_sector",
                "valuation_year",
                "flag_type",
                "flag_reason",
                "pe_ratio",
                "pb_ratio",
                "ev_ebitda",
                "dividend_yield_pct",
                "valuation_score",
                "valuation_category",
            ]
        )

    flags.to_csv(
        FLAGS_PATH,
        index=False,
    )


# ============================================================
# VALIDATION OUTPUT
# ============================================================

def print_validation(
    df: pd.DataFrame,
    flags: pd.DataFrame,
) -> None:

    print("=" * 72)
    print("VALUATION ENGINE")
    print("=" * 72)

    print(
        f"\nCompanies loaded: "
        f"{df['company_id'].nunique()}"
    )

    print(
        f"Companies with P/E: "
        f"{df['pe_ratio'].notna().sum()}"
    )

    print(
        f"Companies with P/B: "
        f"{df['pb_ratio'].notna().sum()}"
    )

    print(
        f"Companies with EV/EBITDA: "
        f"{df['ev_ebitda'].notna().sum()}"
    )

    print(
        f"Companies with valuation score: "
        f"{df['valuation_score'].notna().sum()}"
    )

    print("\nValuation categories:")

    print(
        df["valuation_category"]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print(
        f"\nValuation flags generated: "
        f"{len(flags)}"
    )

    print("\nTop valuation scores:")

    display_columns = [
        "company_id",
        "company_name",
        "broad_sector",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "dividend_yield_pct",
        "valuation_score",
        "valuation_category",
    ]

    print(
        df.sort_values(
            "valuation_score",
            ascending=False,
        )[
            display_columns
        ]
        .head(10)
        .to_string(
            index=False
        )
    )

    print("\nFiles generated:")

    print(SUMMARY_PATH)
    print(FLAGS_PATH)

    print("=" * 72)


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    valuation_df = build_valuation_dataset()

    flags_df = build_flags(
        valuation_df
    )

    export_summary(
        valuation_df
    )

    export_flags(
        flags_df
    )

    print_validation(
        valuation_df,
        flags_df,
    )


if __name__ == "__main__":
    main()