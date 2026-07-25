from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st


# =========================================================
# Paths
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"


# =========================================================
# Core Database Functions
# =========================================================

def get_connection():
    """Create a SQLite connection."""
    return sqlite3.connect(DB_PATH)


@st.cache_data(ttl=600)
def run_query(query: str, params=None) -> pd.DataFrame:
    """Run a SQLite query and return a DataFrame."""

    params = params or ()

    with get_connection() as conn:
        return pd.read_sql_query(
            query,
            conn,
            params=params,
        )


@st.cache_data(ttl=600)
def get_table_names() -> list[str]:
    """Return all database tables."""

    df = run_query(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    )

    return df["name"].tolist()


@st.cache_data(ttl=600)
def get_table_columns(table_name: str) -> list[str]:
    """Return table column names."""

    with get_connection() as conn:

        cursor = conn.execute(
            f'PRAGMA table_info("{table_name}")'
        )

        return [
            row[1]
            for row in cursor.fetchall()
        ]


# =========================================================
# Generic Helpers
# =========================================================

def find_column(
    df: pd.DataFrame,
    candidates: list[str],
) -> str | None:
    """Find the first matching column name."""

    if df is None or df.empty:
        return None

    lookup = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    for candidate in candidates:

        key = candidate.strip().lower()

        if key in lookup:
            return lookup[key]

    return None


def safe_value(
    row,
    candidates: list[str],
    default=None,
):
    """Return first non-null candidate value."""

    for candidate in candidates:

        if candidate in row.index:

            value = row[candidate]

            if pd.notna(value):
                return value

    return default


def extract_year(value):
    """Extract a four-digit year from a year label."""

    if pd.isna(value):
        return None

    match = pd.Series(
        [str(value)]
    ).str.extract(
        r"(\d{4})"
    )[0].iloc[0]

    if pd.isna(match):
        return None

    return int(match)


def normalize_company_id(series):
    """Normalize ticker/company identifiers."""

    return (
        series
        .astype(str)
        .str.strip()
        .str.upper()
    )


# =========================================================
# Embedded Header Repair
# =========================================================

def promote_first_row_to_header(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Repair tables where actual headers were imported
    as the first database row.
    """

    if df.empty:
        return df

    first_row = (
        df.iloc[0]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    values = set(first_row.tolist())

    expected_header_tokens = {
        "company_id",
        "year",
        "sales",
        "expenses",
        "net_profit",
        "total_assets",
        "borrowings",
        "cash_from_operations",
    }

    if not values.intersection(
        expected_header_tokens
    ):
        return df

    new_columns = []

    for index, value in enumerate(
        df.iloc[0].tolist()
    ):

        if pd.isna(value):
            new_columns.append(
                f"column_{index}"
            )
        else:

            column = (
                str(value)
                .strip()
                .lower()
                .replace(" ", "_")
            )

            new_columns.append(column)

    repaired = df.iloc[1:].copy()

    repaired.columns = new_columns

    repaired = repaired.reset_index(
        drop=True
    )

    return repaired


# =========================================================
# Company Master
# =========================================================

@st.cache_data(ttl=600)
def get_companies() -> pd.DataFrame:
    """Return company master data."""

    return run_query(
        "SELECT * FROM companies"
    )


# =========================================================
# Sector Data
# =========================================================

@st.cache_data(ttl=600)
def get_sectors() -> pd.DataFrame:
    """Return sector classification data."""

    df = run_query(
        "SELECT * FROM sectors"
    )

    if "company_id" in df.columns:

        df["company_id"] = (
            normalize_company_id(
                df["company_id"]
            )
        )

    return df


# =========================================================
# Financial Ratios
# =========================================================

@st.cache_data(ttl=600)
def get_ratios(
    ticker: str | None = None,
    year=None,
) -> pd.DataFrame:
    """Return financial ratio data."""

    df = run_query(
        "SELECT * FROM financial_ratios"
    )

    if df.empty:
        return df

    if "company_id" in df.columns:

        df["company_id"] = (
            normalize_company_id(
                df["company_id"]
            )
        )

    if "year" in df.columns:

        df["year_numeric"] = (
            df["year"]
            .apply(extract_year)
        )

    if ticker:

        ticker = (
            str(ticker)
            .strip()
            .upper()
        )

        df = df[
            df["company_id"] == ticker
        ]

    if year is not None:

        if "year_numeric" in df.columns:

            df = df[
                df["year_numeric"]
                == int(year)
            ]

    if "year_numeric" in df.columns:

        df = df.sort_values(
            [
                "company_id",
                "year_numeric",
            ]
        )

    return df.reset_index(
        drop=True
    )


# =========================================================
# Profit & Loss
# =========================================================

@st.cache_data(ttl=600)
def get_all_pl() -> pd.DataFrame:
    """Return repaired P&L data."""

    df = run_query(
        "SELECT * FROM profitandloss"
    )

    df = promote_first_row_to_header(
        df
    )

    if "company_id" in df.columns:

        df["company_id"] = (
            normalize_company_id(
                df["company_id"]
            )
        )

    if "year" in df.columns:

        df["year_numeric"] = (
            df["year"]
            .apply(extract_year)
        )

    return df


@st.cache_data(ttl=600)
def get_pl(
    ticker: str,
) -> pd.DataFrame:
    """Return P&L history for a company."""

    df = get_all_pl().copy()

    if df.empty:
        return df

    ticker = (
        str(ticker)
        .strip()
        .upper()
    )

    if "company_id" not in df.columns:
        return pd.DataFrame()

    df = df[
        df["company_id"] == ticker
    ]

    if "year_numeric" in df.columns:

        df = df.sort_values(
            "year_numeric"
        )

    return df.reset_index(
        drop=True
    )


# =========================================================
# Balance Sheet
# =========================================================

@st.cache_data(ttl=600)
def get_bs(
    ticker: str,
) -> pd.DataFrame:
    """Return balance sheet history."""

    df = run_query(
        "SELECT * FROM balancesheet"
    )

    df = promote_first_row_to_header(
        df
    )

    if "company_id" not in df.columns:
        return pd.DataFrame()

    df["company_id"] = (
        normalize_company_id(
            df["company_id"]
        )
    )

    ticker = (
        str(ticker)
        .strip()
        .upper()
    )

    df = df[
        df["company_id"] == ticker
    ]

    if "year" in df.columns:

        df["year_numeric"] = (
            df["year"]
            .apply(extract_year)
        )

        df = df.sort_values(
            "year_numeric"
        )

    return df.reset_index(
        drop=True
    )


# =========================================================
# Cash Flow
# =========================================================

@st.cache_data(ttl=600)
def get_cf(
    ticker: str,
) -> pd.DataFrame:
    """Return cash flow history."""

    df = run_query(
        "SELECT * FROM cashflow"
    )

    df = promote_first_row_to_header(
        df
    )

    if "company_id" not in df.columns:
        return pd.DataFrame()

    df["company_id"] = (
        normalize_company_id(
            df["company_id"]
        )
    )

    ticker = (
        str(ticker)
        .strip()
        .upper()
    )

    df = df[
        df["company_id"] == ticker
    ]

    if "year" in df.columns:

        df["year_numeric"] = (
            df["year"]
            .apply(extract_year)
        )

        df = df.sort_values(
            "year_numeric"
        )

    return df.reset_index(
        drop=True
    )


# =========================================================
# Peer Data
# =========================================================

@st.cache_data(ttl=600)
def get_peers(
    group_name: str | None = None,
) -> pd.DataFrame:
    """Return peer percentile data."""

    df = run_query(
        "SELECT * FROM peer_percentiles"
    )

    if group_name is None:
        return df

    group_col = find_column(
        df,
        [
            "peer_group_name",
            "group_name",
            "peer_group",
        ],
    )

    if group_col is None:
        return pd.DataFrame()

    return df[
        df[group_col] == group_name
    ].reset_index(drop=True)


# =========================================================
# Market Cap / Valuation
# =========================================================

@st.cache_data(ttl=600)
def get_market_cap(
    ticker: str | None = None,
    year=None,
) -> pd.DataFrame:
    """Return simulated market-cap data."""

    df = run_query(
        "SELECT * FROM market_cap"
    )

    if df.empty:
        return df

    if "company_id" in df.columns:

        df["company_id"] = (
            normalize_company_id(
                df["company_id"]
            )
        )

    if ticker:

        ticker = (
            str(ticker)
            .strip()
            .upper()
        )

        df = df[
            df["company_id"] == ticker
        ]

    if year is not None:

        df = df[
            pd.to_numeric(
                df["year"],
                errors="coerce",
            )
            == int(year)
        ]

    return df.reset_index(
        drop=True
    )


@st.cache_data(ttl=600)
def get_valuation(
    ticker: str | None = None,
) -> pd.DataFrame:
    """Return valuation data."""

    return get_market_cap(
        ticker=ticker
    )