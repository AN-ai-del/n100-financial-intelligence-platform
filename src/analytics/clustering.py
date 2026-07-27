"""
Sprint 6 — Day 36
KMeans Clustering Engine

Features:
1. return_on_equity_pct
2. debt_to_equity
3. revenue_cagr_5yr
4. fcf_cagr_5yr
5. operating_profit_margin_pct

Pipeline:
- Load official company universe
- Load financial ratios
- Load profit & loss data
- Load sector mappings
- Repair embedded spreadsheet headers
- Repair known / detectable financial-data anomalies
- Calculate 5-year Revenue CAGR
- Calculate 5-year Free Cash Flow CAGR
- Impute missing values using broad-sector median
- Fall back to portfolio median when sector median is unavailable
- Standardize features
- Generate elbow data for k=2..10
- Run KMeans with 5 clusters and random_state=42
- Calculate distance from centroid
- Validate output
- Export clustering artifacts
"""

from pathlib import Path
import sqlite3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"

OUTPUT_DIR = PROJECT_ROOT / "output"
REPORTS_DIR = PROJECT_ROOT / "reports"

CLUSTER_OUTPUT_PATH = (
    OUTPUT_DIR / "cluster_labels.csv"
)

FEATURE_OUTPUT_PATH = (
    OUTPUT_DIR / "clustering_features.csv"
)

REPAIR_OUTPUT_PATH = (
    OUTPUT_DIR / "clustering_data_repairs.csv"
)

ELBOW_OUTPUT_PATH = (
    REPORTS_DIR / "elbow_plot.png"
)


# =============================================================================
# CONFIGURATION
# =============================================================================

FEATURE_COLUMNS = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
]

N_CLUSTERS = 5
RANDOM_STATE = 42

ELBOW_K_VALUES = range(2, 11)

# Sanity limits used only for identifying obviously unsuitable
# cross-company clustering inputs.
ROE_SANITY_MIN = -200.0
ROE_SANITY_MAX = 200.0

OPM_SANITY_MIN = -100.0
OPM_SANITY_MAX = 100.0


# =============================================================================
# GENERIC HELPERS
# =============================================================================

def clean_text(value):
    """Clean text values."""

    if pd.isna(value):
        return None

    value = str(value).strip()

    if not value:
        return None

    return value


def to_numeric(series):
    """Convert a pandas Series to numeric."""

    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.strip(),
        errors="coerce",
    )


def safe_float(value):
    """Convert one value to float safely."""

    try:
        if pd.isna(value):
            return np.nan

        return float(value)

    except (TypeError, ValueError):
        return np.nan


def repair_embedded_header(df):
    """
    Repair SQLite tables whose real headers are stored
    in the first data row.
    """

    if df.empty:
        return df.copy()

    first_row = df.iloc[0]

    first_values = [
        str(value).strip().lower()
        if pd.notna(value)
        else ""
        for value in first_row
    ]

    if (
        "company_id" in first_values
        and "year" in first_values
    ):
        repaired = df.iloc[1:].copy()

        repaired.columns = [
            str(value).strip()
            if pd.notna(value)
            else f"column_{index}"
            for index, value in enumerate(first_row)
        ]

        repaired = repaired.reset_index(
            drop=True
        )

        return repaired

    return df.copy()


def extract_year_numeric(value):
    """Extract four-digit year from project year strings."""

    if pd.isna(value):
        return np.nan

    text = str(value).strip()

    if text.upper() == "TTM":
        return np.nan

    extracted = pd.Series(
        [text]
    ).str.extract(
        r"(\d{4})",
        expand=False,
    ).iloc[0]

    return pd.to_numeric(
        extracted,
        errors="coerce",
    )


# =============================================================================
# DATABASE LOADERS
# =============================================================================

def load_table(connection, table_name):
    """Load a complete SQLite table."""

    return pd.read_sql_query(
        f"SELECT * FROM {table_name}",
        connection,
    )


def load_project_data():
    """Load all data required for Day 36."""

    with sqlite3.connect(DB_PATH) as connection:

        companies = load_table(
            connection,
            "companies",
        )

        financial_ratios = load_table(
            connection,
            "financial_ratios",
        )

        profit_loss = load_table(
            connection,
            "profitandloss",
        )

        sectors = load_table(
            connection,
            "sectors",
        )

    profit_loss = repair_embedded_header(
        profit_loss
    )

    sectors = repair_embedded_header(
        sectors
    )

    return (
        companies,
        financial_ratios,
        profit_loss,
        sectors,
    )


# =============================================================================
# DATA PREPARATION
# =============================================================================

def prepare_companies(companies):
    """Prepare official company universe."""

    df = companies.copy()

    df["id"] = (
        df["id"]
        .astype(str)
        .str.strip()
    )

    df["company_name"] = (
        df["company_name"]
        .astype(str)
        .str.strip()
    )

    if "roe_percentage" in df.columns:
        df["roe_percentage"] = to_numeric(
            df["roe_percentage"]
        )

    return df


def prepare_sectors(sectors):
    """Prepare sector mapping table."""

    df = sectors.copy()

    if "company_id" not in df.columns:
        raise ValueError(
            "sectors table does not contain company_id."
        )

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
    )

    if "broad_sector" not in df.columns:
        df["broad_sector"] = np.nan

    if "sub_sector" not in df.columns:
        df["sub_sector"] = np.nan

    df["broad_sector"] = (
        df["broad_sector"]
        .astype(str)
        .str.strip()
        .replace(
            {
                "nan": np.nan,
                "None": np.nan,
                "": np.nan,
            }
        )
    )

    df["sub_sector"] = (
        df["sub_sector"]
        .astype(str)
        .str.strip()
        .replace(
            {
                "nan": np.nan,
                "None": np.nan,
                "": np.nan,
            }
        )
    )

    df = (
        df[
            [
                "company_id",
                "broad_sector",
                "sub_sector",
            ]
        ]
        .drop_duplicates(
            subset=["company_id"],
            keep="last",
        )
    )

    return df


def prepare_ratios(financial_ratios):
    """Prepare financial-ratio history."""

    df = financial_ratios.copy()

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
    )

    df["year_numeric"] = (
        df["year"]
        .apply(extract_year_numeric)
    )

    numeric_columns = [
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "free_cash_flow_cr",
        "capex_cr",
        "earnings_per_share",
        "book_value_per_share",
        "dividend_payout_ratio_pct",
        "total_debt_cr",
        "cash_from_operations_cr",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = to_numeric(
                df[column]
            )

    return df


def prepare_profit_loss(profit_loss):
    """Prepare P&L history."""

    df = profit_loss.copy()

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
    )

    df["year"] = (
        df["year"]
        .astype(str)
        .str.strip()
    )

    df["year_numeric"] = (
        df["year"]
        .apply(extract_year_numeric)
    )

    numeric_columns = [
        "sales",
        "expenses",
        "operating_profit",
        "opm_percentage",
        "other_income",
        "interest",
        "depreciation",
        "profit_before_tax",
        "tax_percentage",
        "net_profit",
        "eps",
        "dividend_payout",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = to_numeric(
                df[column]
            )

    return df


# =============================================================================
# LATEST VALUE HELPERS
# =============================================================================

def get_latest_ratio_value(
    ratio_history,
    column,
):
    """Return latest non-null ratio value."""

    if ratio_history.empty:
        return np.nan

    if column not in ratio_history.columns:
        return np.nan

    valid = ratio_history[
        ratio_history[column].notna()
    ].copy()

    if valid.empty:
        return np.nan

    valid = valid.sort_values(
        [
            "year_numeric",
            "year",
        ]
    )

    return safe_float(
        valid.iloc[-1][column]
    )


def get_latest_master_roe(company):
    """Get ROE from company master."""

    if company.empty:
        return np.nan

    if "roe_percentage" not in company.columns:
        return np.nan

    value = company.iloc[0][
        "roe_percentage"
    ]

    return safe_float(value)


# =============================================================================
# CAGR
# =============================================================================

def calculate_cagr(
    start_value,
    end_value,
    years,
):
    """
    Calculate CAGR.

    CAGR is left unavailable when:
    - years <= 0
    - start/end missing
    - start <= 0
    - end <= 0

    This avoids mathematically misleading CAGR values.
    """

    start_value = safe_float(
        start_value
    )

    end_value = safe_float(
        end_value
    )

    years = safe_float(
        years
    )

    if (
        pd.isna(start_value)
        or pd.isna(end_value)
        or pd.isna(years)
        or years <= 0
        or start_value <= 0
        or end_value <= 0
    ):
        return np.nan

    try:
        result = (
            (
                end_value
                / start_value
            )
            ** (
                1.0
                / years
            )
            - 1.0
        ) * 100.0

        if not np.isfinite(result):
            return np.nan

        return float(result)

    except (
        ZeroDivisionError,
        ValueError,
        OverflowError,
    ):
        return np.nan


def calculate_5yr_cagr(
    history,
    value_column,
):
    """
    Calculate five-year CAGR.

    The calculation requires an observation at least five
    financial years before the latest available year.

    Companies without sufficient history are returned as NaN
    and later handled through the required sector-median
    imputation step.

    This prevents newly listed / short-history companies from
    having one-year growth incorrectly labelled as 5-year CAGR.
    """

    if history.empty:
        return np.nan

    if value_column not in history.columns:
        return np.nan

    df = history[
        [
            "year_numeric",
            value_column,
        ]
    ].copy()

    df = df.dropna(
        subset=[
            "year_numeric",
            value_column,
        ]
    )

    if len(df) < 2:
        return np.nan

    df = (
        df.sort_values(
            "year_numeric"
        )
        .drop_duplicates(
            subset=["year_numeric"],
            keep="last",
        )
    )

    latest = df.iloc[-1]

    latest_year = int(
        latest["year_numeric"]
    )

    target_start_year = (
        latest_year - 5
    )

    # ---------------------------------------------------------
    # Only use observations that are actually at least
    # five years before the latest year.
    # ---------------------------------------------------------

    candidates = df[
        df["year_numeric"]
        <= target_start_year
    ].copy()

    if candidates.empty:
        return np.nan

    # Select the closest observation to exactly five years ago.
    start = (
        candidates
        .sort_values(
            "year_numeric",
            ascending=False,
        )
        .iloc[0]
    )

    start_year = int(
        start["year_numeric"]
    )

    actual_years = (
        latest_year
        - start_year
    )

    if actual_years < 5:
        return np.nan

    return calculate_cagr(
        start[value_column],
        latest[value_column],
        actual_years,
    )


# =============================================================================
# P&L OPM REPAIR
# =============================================================================
def calculate_opm_from_profit_loss_row(row):
    """
    Recover operating-profit margin from a P&L row.

    Handles:
    1. Valid raw OPM
    2. Shifted source columns
    3. Standard operating-profit calculation
    4. Sales-minus-expenses fallback
    """

    sales = safe_float(
        row.get("sales")
    )

    expenses = safe_float(
        row.get("expenses")
    )

    stored_operating_profit = safe_float(
        row.get("operating_profit")
    )

    stored_opm = safe_float(
        row.get("opm_percentage")
    )

    # ---------------------------------------------------------
    # 1. Valid raw percentage
    # ---------------------------------------------------------

    if (
        pd.notna(stored_opm)
        and OPM_SANITY_MIN
        <= stored_opm
        <= OPM_SANITY_MAX
    ):
        return (
            stored_opm,
            "raw_pnl_opm",
            stored_opm,
        )

    # ---------------------------------------------------------
    # 2. Shifted P&L detection
    #
    # Example:
    #
    # sales                 = 25,774
    # stored operating_prof = 19,483
    # stored opm            = 6,291
    #
    # 19,483 + 6,291 = 25,774
    #
    # Therefore:
    # 19,483 = expenses
    # 6,291  = operating profit
    # ---------------------------------------------------------

    if (
        pd.notna(sales)
        and sales != 0
        and pd.notna(stored_operating_profit)
        and pd.notna(stored_opm)
    ):

        reconstructed_sales = (
            stored_operating_profit
            + stored_opm
        )

        tolerance = max(
            abs(sales) * 0.01,
            1.0,
        )

        if (
            abs(
                reconstructed_sales
                - sales
            )
            <= tolerance
        ):

            corrected_opm = (
                stored_opm
                / sales
                * 100.0
            )

            if (
                OPM_SANITY_MIN
                <= corrected_opm
                <= OPM_SANITY_MAX
            ):
                return (
                    corrected_opm,
                    "reconstructed_shifted_pnl",
                    stored_opm,
                )

    # ---------------------------------------------------------
    # 3. Normal operating-profit calculation
    # ---------------------------------------------------------

    if (
        pd.notna(sales)
        and sales != 0
        and pd.notna(stored_operating_profit)
    ):

        calculated_opm = (
            stored_operating_profit
            / sales
            * 100.0
        )

        if (
            OPM_SANITY_MIN
            <= calculated_opm
            <= OPM_SANITY_MAX
        ):
            return (
                calculated_opm,
                "calculated_from_operating_profit",
                stored_opm,
            )

    # ---------------------------------------------------------
    # 4. Expenses fallback
    # ---------------------------------------------------------

    if (
        pd.notna(sales)
        and sales != 0
        and pd.notna(expenses)
    ):

        reconstructed_profit = (
            sales - expenses
        )

        calculated_opm = (
            reconstructed_profit
            / sales
            * 100.0
        )

        if (
            OPM_SANITY_MIN
            <= calculated_opm
            <= OPM_SANITY_MAX
        ):
            return (
                calculated_opm,
                "calculated_from_sales_minus_expenses",
                stored_opm,
            )

    return (
        np.nan,
        "unavailable",
        stored_opm,
    )


def get_latest_valid_pnl_opm(
    pnl_history,
):
    """Return repaired latest P&L OPM."""

    if pnl_history.empty:
        return (
            np.nan,
            "unavailable",
            np.nan,
        )

    annual = pnl_history[
        pnl_history["year_numeric"].notna()
    ].copy()

    if annual.empty:
        return (
            np.nan,
            "unavailable",
            np.nan,
        )

    annual = annual.sort_values(
        "year_numeric"
    )

    row = annual.iloc[-1]

    return calculate_opm_from_profit_loss_row(
        row
    )


# =============================================================================
# FEATURE TABLE
# =============================================================================

def build_feature_table(
    companies,
    financial_ratios,
    profit_loss,
    sectors,
):
    """Build Day 36 clustering feature table."""

    records = []
    repairs = []

    official_ids = set(
        companies["id"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    for ticker in sorted(
        official_ids
    ):

        company = companies[
            companies["id"] == ticker
        ].copy()

        ratio_history = (
            financial_ratios[
                financial_ratios[
                    "company_id"
                ] == ticker
            ]
            .copy()
            .sort_values(
                "year_numeric"
            )
        )

        pnl_history = (
            profit_loss[
                profit_loss[
                    "company_id"
                ] == ticker
            ]
            .copy()
            .sort_values(
                "year_numeric"
            )
        )

        sector_row = sectors[
            sectors["company_id"]
            == ticker
        ].copy()

        broad_sector = np.nan
        sub_sector = np.nan

        if not sector_row.empty:
            broad_sector = (
                sector_row.iloc[0][
                    "broad_sector"
                ]
            )

            sub_sector = (
                sector_row.iloc[0][
                    "sub_sector"
                ]
            )

        # =====================================================
        # ROE
        # =====================================================

        ratio_roe = (
            get_latest_ratio_value(
                ratio_history,
                "return_on_equity_pct",
            )
        )

        master_roe = (
            get_latest_master_roe(
                company
            )
        )

        ratio_roe_is_sane = (
            pd.notna(ratio_roe)
            and ROE_SANITY_MIN
            <= ratio_roe
            <= ROE_SANITY_MAX
        )

        master_roe_is_sane = (
            pd.notna(master_roe)
            and ROE_SANITY_MIN
            <= master_roe
            <= ROE_SANITY_MAX
        )

        if master_roe_is_sane:

            latest_roe = master_roe

            if (
                pd.notna(ratio_roe)
                and (
                    not ratio_roe_is_sane
                    or abs(
                        ratio_roe
                        - master_roe
                    ) > 100
                )
            ):
                repairs.append(
                    {
                        "company_id":
                            ticker,

                        "metric":
                            "return_on_equity_pct",

                        "raw_value":
                            ratio_roe,

                        "repaired_value":
                            master_roe,

                        "repair_reason":
                            (
                                "Latest financial-ratio ROE "
                                "failed sanity check; valid "
                                "company-master ROE used"
                            ),
                    }
                )

        elif ratio_roe_is_sane:

            latest_roe = ratio_roe

        else:

            latest_roe = np.nan

            if pd.notna(ratio_roe):

                repairs.append(
                    {
                        "company_id":
                            ticker,

                        "metric":
                            "return_on_equity_pct",

                        "raw_value":
                            ratio_roe,

                        "repaired_value":
                            np.nan,

                        "repair_reason":
                            (
                                "ROE failed sanity check and "
                                "no valid company-master ROE "
                                "was available; value deferred "
                                "to sector-median imputation"
                            ),
                    }
                )

        # =====================================================
        # DEBT / EQUITY
        # =====================================================

        latest_de = (
            get_latest_ratio_value(
                ratio_history,
                "debt_to_equity",
            )
        )

        # =====================================================
        # OPERATING PROFIT MARGIN
        # =====================================================

        ratio_opm = (
            get_latest_ratio_value(
                ratio_history,
                "operating_profit_margin_pct",
            )
        )

        ratio_opm_is_sane = (
            pd.notna(ratio_opm)
            and OPM_SANITY_MIN
            <= ratio_opm
            <= OPM_SANITY_MAX
        )

        if ratio_opm_is_sane:

            latest_opm = ratio_opm

        else:

            (
                repaired_opm,
                repair_source,
                raw_pnl_opm,
            ) = get_latest_valid_pnl_opm(
                pnl_history
            )

            latest_opm = repaired_opm

            repairs.append(
                {
                    "company_id":
                        ticker,

                    "metric":
                        "operating_profit_margin_pct",

                    "raw_value":
                        ratio_opm,

                    "repaired_value":
                        repaired_opm,

                    "repair_reason":
                        (
                            "Implausible ratio-table OPM; "
                            f"P&L repair source={repair_source}; "
                            f"raw_pnl_opm={raw_pnl_opm}"
                        ),
                }
            )

        # =====================================================
        # REVENUE CAGR
        # =====================================================

        revenue_cagr_5yr = (
            calculate_5yr_cagr(
                pnl_history,
                "sales",
            )
        )

        # =====================================================
        # FREE CASH FLOW CAGR
        # =====================================================

        fcf_cagr_5yr = (
            calculate_5yr_cagr(
                ratio_history,
                "free_cash_flow_cr",
            )
        )
        
        

        # =====================================================
        # RECORD
        # =====================================================

        company_name = ticker

        if not company.empty:
            company_name = (
                clean_text(
                    company.iloc[0][
                        "company_name"
                    ]
                )
                or ticker
            )

        records.append(
            {
                "company_id":
                    ticker,

                "company_name":
                    company_name,

                "broad_sector":
                    broad_sector,

                "sub_sector":
                    sub_sector,

                "return_on_equity_pct":
                    latest_roe,

                "debt_to_equity":
                    latest_de,

                "revenue_cagr_5yr":
                    revenue_cagr_5yr,

                "fcf_cagr_5yr":
                    fcf_cagr_5yr,

                "operating_profit_margin_pct":
                    latest_opm,
            }
        )

    features = pd.DataFrame(
        records
    )

    repairs_df = pd.DataFrame(
        repairs,
        columns=[
            "company_id",
            "metric",
            "raw_value",
            "repaired_value",
            "repair_reason",
        ],
    )

    return (
        features,
        repairs_df,
    )


# =============================================================================
# IMPUTATION
# =============================================================================

def impute_features(
    feature_df,
):
    """
    Impute missing clustering feature values.

    Required method:
    1. Convert extreme FCF CAGR values into missing values.
    2. Impute missing values using broad-sector median.
    3. Use portfolio median only when sector median is unavailable.

    Extreme FCF CAGR values are treated as unstable observations
    because large swings in free cash flow can dominate KMeans
    after StandardScaler.
    """

    df = feature_df.copy()

    summary_records = []

    # ============================================================
    # FCF CAGR SANITY CHECK
    # ============================================================

    # Prevent extreme FCF CAGR values from creating a
    # single-company KMeans cluster.
    #
    # Example:
    # CIPLA = 228.75%
    #
    # Instead of clipping/fabricating a value, mark it missing.
    # The required sector-median imputation below will then
    # provide a representative Healthcare-sector value.

    extreme_fcf_mask = (
        df["fcf_cagr_5yr"].notna()
        & (
            df["fcf_cagr_5yr"].abs()
            > 100
        )
    )

    extreme_fcf_count = int(
        extreme_fcf_mask.sum()
    )

    if extreme_fcf_count > 0:

        print(
            "\nFCF CAGR SANITY CHECK"
        )

        print(
            "-" * 100
        )

        print(
            "Extreme FCF CAGR values "
            "(absolute value > 100%):"
        )

        print(
            df.loc[
                extreme_fcf_mask,
                [
                    "company_id",
                    "broad_sector",
                    "fcf_cagr_5yr",
                ],
            ].to_string(
                index=False
            )
        )

        print(
            "\nThese values will be deferred "
            "to sector-median imputation."
        )

        df.loc[
            extreme_fcf_mask,
            "fcf_cagr_5yr",
        ] = np.nan

    # ============================================================
    # FEATURE IMPUTATION
    # ============================================================

    for feature in FEATURE_COLUMNS:

        # --------------------------------------------------------
        # Count missing values BEFORE imputation
        # --------------------------------------------------------

        original_missing = int(
            df[feature]
            .isna()
            .sum()
        )

        sector_median_imputed = 0
        portfolio_median_imputed = 0

        # --------------------------------------------------------
        # Broad-sector median
        # --------------------------------------------------------

        sector_medians = (
            df.groupby(
                "broad_sector"
            )[feature]
            .transform(
                "median"
            )
        )

        sector_mask = (
            df[feature].isna()
            & sector_medians.notna()
        )

        sector_median_imputed = int(
            sector_mask.sum()
        )

        df.loc[
            sector_mask,
            feature,
        ] = sector_medians[
            sector_mask
        ]

        # --------------------------------------------------------
        # Portfolio median fallback
        # --------------------------------------------------------

        remaining_mask = (
            df[feature].isna()
        )

        if remaining_mask.any():

            portfolio_median = (
                df[feature].median()
            )

            if pd.notna(
                portfolio_median
            ):

                portfolio_median_imputed = int(
                    remaining_mask.sum()
                )

                df.loc[
                    remaining_mask,
                    feature,
                ] = portfolio_median

        # --------------------------------------------------------
        # Final missing count
        # --------------------------------------------------------

        remaining_missing = int(
            df[feature]
            .isna()
            .sum()
        )

        # --------------------------------------------------------
        # Save summary
        # --------------------------------------------------------

        summary_records.append(
            {
                "feature":
                    feature,

                "original_missing":
                    original_missing,

                "sector_median_imputed":
                    sector_median_imputed,

                "portfolio_median_imputed":
                    portfolio_median_imputed,

                "remaining_missing":
                    remaining_missing,
            }
        )

    summary = pd.DataFrame(
        summary_records
    )

    return (
        df,
        summary,
    )


# =============================================================================
# ELBOW ANALYSIS
# =============================================================================

def generate_elbow_data(
    scaled_features,
):
    """Calculate inertia for k=2..10."""

    records = []

    for k in ELBOW_K_VALUES:

        model = KMeans(
            n_clusters=k,
            random_state=RANDOM_STATE,
            n_init=10,
        )

        model.fit(
            scaled_features
        )

        records.append(
            {
                "k": k,
                "inertia": model.inertia_,
            }
        )

    return pd.DataFrame(
        records
    )


def save_elbow_plot(
    elbow_df,
):
    """Save elbow plot."""

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.figure(
        figsize=(9, 6)
    )

    plt.plot(
        elbow_df["k"],
        elbow_df["inertia"],
        marker="o",
    )

    plt.xlabel(
        "Number of Clusters (k)"
    )

    plt.ylabel(
        "Inertia"
    )

    plt.title(
        "Sprint 6 Day 36 — KMeans Elbow Plot"
    )

    plt.xticks(
        list(ELBOW_K_VALUES)
    )

    plt.grid(
        alpha=0.25
    )

    plt.tight_layout()

    plt.savefig(
        ELBOW_OUTPUT_PATH,
        dpi=180,
        bbox_inches="tight",
    )

    plt.close()


# =============================================================================
# KMEANS
# =============================================================================

def run_kmeans(
    feature_df,
):
    """Scale features and run KMeans."""

    scaler = StandardScaler()

    scaled_features = (
        scaler.fit_transform(
            feature_df[
                FEATURE_COLUMNS
            ]
        )
    )

    elbow_df = (
        generate_elbow_data(
            scaled_features
        )
    )

    model = KMeans(
        n_clusters=N_CLUSTERS,
        random_state=RANDOM_STATE,
        n_init=10,
    )

    cluster_ids = (
        model.fit_predict(
            scaled_features
        )
    )

    distances = np.linalg.norm(
        scaled_features
        - model.cluster_centers_[
            cluster_ids
        ],
        axis=1,
    )

    result = feature_df.copy()

    result[
        "cluster_id"
    ] = cluster_ids

    result[
        "cluster_name"
    ] = (
        result["cluster_id"]
        .apply(
            lambda value:
                f"Cluster {int(value)}"
        )
    )

    result[
        "distance_from_centroid"
    ] = distances

    return (
        result,
        elbow_df,
        model,
        scaler,
    )


# =============================================================================
# VALIDATION
# =============================================================================

def validate_results(
    clustered_df,
):
    """Validate Day 36 output."""

    company_count = len(
        clustered_df
    )

    unique_company_count = (
        clustered_df[
            "company_id"
        ]
        .nunique()
    )

    cluster_count = (
        clustered_df[
            "cluster_id"
        ]
        .nunique()
    )

    missing_cluster_ids = int(
        clustered_df[
            "cluster_id"
        ]
        .isna()
        .sum()
    )

    missing_distances = int(
        clustered_df[
            "distance_from_centroid"
        ]
        .isna()
        .sum()
    )

    missing_features = int(
        clustered_df[
            FEATURE_COLUMNS
        ]
        .isna()
        .sum()
        .sum()
    )

    checks = {
        "company_count":
            company_count,

        "unique_company_count":
            unique_company_count,

        "cluster_count":
            cluster_count,

        "missing_cluster_ids":
            missing_cluster_ids,

        "missing_distances":
            missing_distances,

        "missing_features":
            missing_features,
    }

    passed = (
        company_count == 92
        and unique_company_count == 92
        and cluster_count == N_CLUSTERS
        and missing_cluster_ids == 0
        and missing_distances == 0
        and missing_features == 0
    )

    return (
        checks,
        passed,
    )


# =============================================================================
# OUTPUT
# =============================================================================

def save_outputs(
    clustered_df,
    repairs_df,
):
    """Save Day 36 CSV outputs."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    cluster_labels = clustered_df[
        [
            "company_id",
            "cluster_id",
            "cluster_name",
            "distance_from_centroid",
        ]
    ].copy()

    cluster_labels.to_csv(
        CLUSTER_OUTPUT_PATH,
        index=False,
    )

    clustered_df.to_csv(
        FEATURE_OUTPUT_PATH,
        index=False,
    )

    repairs_df.to_csv(
        REPAIR_OUTPUT_PATH,
        index=False,
    )


# =============================================================================
# DISPLAY HELPERS
# =============================================================================

def print_header(
    title,
    width=100,
):
    print("=" * width)
    print(title)
    print("=" * width)


def print_section(
    title,
    width=100,
):
    print("\n" + title)
    print("-" * width)


# =============================================================================
# MAIN
# =============================================================================

def main():

    print_header(
        "SPRINT 6 — DAY 36 KMEANS CLUSTERING"
    )

    # -------------------------------------------------------------------------
    # Load
    # -------------------------------------------------------------------------

    (
        companies,
        financial_ratios,
        profit_loss,
        sectors,
    ) = load_project_data()

    companies = prepare_companies(
        companies
    )

    financial_ratios = prepare_ratios(
        financial_ratios
    )

    profit_loss = prepare_profit_loss(
        profit_loss
    )

    sectors = prepare_sectors(
        sectors
    )

    print(
        f"\nOfficial companies : "
        f"{companies['id'].nunique()}"
    )

    print(
        f"Ratio companies    : "
        f"{financial_ratios['company_id'].nunique()}"
    )

    print(
        f"P&L companies      : "
        f"{profit_loss['company_id'].nunique()}"
    )

    print(
        f"Sector mappings    : "
        f"{sectors['company_id'].nunique()}"
    )

    # -------------------------------------------------------------------------
    # Build raw features
    # -------------------------------------------------------------------------

    (
        raw_features,
        repairs_df,
    ) = build_feature_table(
        companies,
        financial_ratios,
        profit_loss,
        sectors,
    )

    print_section(
        "RAW FEATURE MISSING VALUES"
    )

    print(
        raw_features[
            FEATURE_COLUMNS
        ]
        .isna()
        .sum()
        .to_string()
    )

    # -------------------------------------------------------------------------
    # Impute
    # -------------------------------------------------------------------------

    (
        imputed_features,
        imputation_summary,
    ) = impute_features(
        raw_features
    )

    # -------------------------------------------------------------------------
    # KMeans
    # -------------------------------------------------------------------------

    (
        clustered_df,
        elbow_df,
        model,
        scaler,
    ) = run_kmeans(
        imputed_features
    )

    # -------------------------------------------------------------------------
    # Save
    # -------------------------------------------------------------------------

    save_elbow_plot(
        elbow_df
    )

    save_outputs(
        clustered_df,
        repairs_df,
    )

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    (
        checks,
        validation_passed,
    ) = validate_results(
        clustered_df
    )

    print("\n")
    print_header(
        "SPRINT 6 — DAY 36 KMEANS CLUSTERING VALIDATION"
    )

    print(
        f"\nCompanies processed     : "
        f"{checks['company_count']}"
    )

    print(
        f"Unique companies        : "
        f"{checks['unique_company_count']}"
    )

    print(
        f"Clusters created        : "
        f"{checks['cluster_count']}"
    )

    print(
        f"Missing cluster IDs     : "
        f"{checks['missing_cluster_ids']}"
    )

    print(
        f"Missing distances       : "
        f"{checks['missing_distances']}"
    )

    print(
        f"Missing feature values  : "
        f"{checks['missing_features']}"
    )

    print(
        f"Data-quality repairs    : "
        f"{len(repairs_df)}"
    )

    # -------------------------------------------------------------------------
    # Repair log
    # -------------------------------------------------------------------------

    if not repairs_df.empty:

        print_section(
            "DATA-QUALITY REPAIR LOG"
        )

        print(
            repairs_df.to_string(
                index=False
            )
        )

    # -------------------------------------------------------------------------
    # Imputation
    # -------------------------------------------------------------------------

    print_section(
        "IMPUTATION SUMMARY"
    )

    print(
        imputation_summary.to_string(
            index=False
        )
    )

    # -------------------------------------------------------------------------
    # Cluster distribution
    # -------------------------------------------------------------------------

    print_section(
        "CLUSTER DISTRIBUTION"
    )

    print(
        clustered_df[
            "cluster_id"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    # -------------------------------------------------------------------------
    # Cluster means
    # -------------------------------------------------------------------------

    print_section(
        "CLUSTER FEATURE MEANS"
    )

    cluster_means = (
        clustered_df
        .groupby(
            "cluster_id"
        )[
            FEATURE_COLUMNS
        ]
        .mean()
        .round(2)
    )

    print(
        cluster_means.to_string()
    )

    # -------------------------------------------------------------------------
    # Elbow
    # -------------------------------------------------------------------------

    print_section(
        "ELBOW DATA"
    )

    print(
        elbow_df.to_string(
            index=False
        )
    )

    # -------------------------------------------------------------------------
    # Sample
    # -------------------------------------------------------------------------

    print_section(
        "SAMPLE CLUSTER ASSIGNMENTS"
    )

    sample_columns = [
        "company_id",
        "broad_sector",
        "cluster_id",
        "cluster_name",
        "distance_from_centroid",
    ]

    print(
        clustered_df[
            sample_columns
        ]
        .head(20)
        .to_string(
            index=False
        )
    )

    # -------------------------------------------------------------------------
    # Final validation
    # -------------------------------------------------------------------------

    print_section(
        (
            "DAY 36 VALIDATION PASSED"
            if validation_passed
            else "DAY 36 VALIDATION FAILED"
        )
    )

    print("\nOUTPUT FILES")

    print("-" * 100)

    print(
        "Cluster labels:"
    )

    print(
        CLUSTER_OUTPUT_PATH.resolve()
    )

    print(
        "\nFeature audit:"
    )

    print(
        FEATURE_OUTPUT_PATH.resolve()
    )

    print(
        "\nRepair audit:"
    )

    print(
        REPAIR_OUTPUT_PATH.resolve()
    )

    print(
        "\nElbow plot:"
    )

    print(
        ELBOW_OUTPUT_PATH.resolve()
    )

    print("\n")
    print_header(
        (
            "SPRINT 6 — DAY 36 COMPLETE"
            if validation_passed
            else
            "SPRINT 6 — DAY 36 REQUIRES REVIEW"
        )
    )

    if not validation_passed:
        raise RuntimeError(
            "Day 36 clustering validation failed."
        )


if __name__ == "__main__":
    main()