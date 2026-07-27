import sqlite3
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"


def get_connection():
    """Create a connection to the Nifty 100 SQLite database."""
    return sqlite3.connect(DB_PATH)


def load_table(table_name):
    """Load a complete SQLite table."""
    with get_connection() as conn:
        return pd.read_sql_query(
            f'SELECT * FROM "{table_name}"',
            conn
        )


def repair_embedded_header(df):
    """
    Repair tables where the actual column names were imported
    as the first data row.
    """
    if df.empty:
        return df

    first_row = df.iloc[0].astype(str).str.strip()

    # Detect the common embedded-header structure.
    if (
        "company_id" in first_row.values
        or "year" in [value.lower() for value in first_row.values]
    ):
        df = df.copy()

        new_columns = [
            str(value).strip().lower()
            for value in df.iloc[0]
        ]

        df = df.iloc[1:].copy()
        df.columns = new_columns
        df.reset_index(drop=True, inplace=True)

    return df


def load_companies():
    return load_table("companies")


def load_sectors():
    return load_table("sectors")


def load_financial_ratios():
    return load_table("financial_ratios")


def load_market_cap():
    return load_table("market_cap")


def load_profit_and_loss():
    df = load_table("profitandloss")
    return repair_embedded_header(df)


def load_cashflow():
    df = load_table("cashflow")
    return repair_embedded_header(df)


def load_documents():
    df = load_table("documents")
    return repair_embedded_header(df)


def get_company_identity(company_id):
    """Return company metadata and sector information."""

    companies = load_companies()
    sectors = load_sectors()

    company = companies[
        companies["id"] == company_id
    ].copy()

    sector = sectors[
        sectors["company_id"] == company_id
    ].copy()

    if company.empty:
        return None

    result = company.merge(
        sector,
        left_on="id",
        right_on="company_id",
        how="left",
        suffixes=("", "_sector")
    )

    return result.iloc[0].to_dict()


def get_company_ratios(company_id):
    """Return historical financial-ratio records."""

    df = load_financial_ratios()

    result = df[
        df["company_id"] == company_id
    ].copy()

    return result.reset_index(drop=True)


def get_company_market_cap(company_id):
    """Return historical valuation records."""

    df = load_market_cap()

    result = df[
        df["company_id"] == company_id
    ].copy()

    return result.sort_values(
        "year"
    ).reset_index(drop=True)


def get_company_profit_loss(company_id):
    """Return historical P&L records."""

    df = load_profit_and_loss()

    result = df[
        df["company_id"] == company_id
    ].copy()

    return result.reset_index(drop=True)


def get_company_cashflow(company_id):
    """Return historical cash-flow records."""

    df = load_cashflow()

    result = df[
        df["company_id"] == company_id
    ].copy()

    return result.reset_index(drop=True)


def get_company_documents(company_id):
    """Return annual-report records."""

    df = load_documents()

    result = df[
        df["company_id"] == company_id
    ].copy()

    if "year" in result.columns:
        result["year"] = pd.to_numeric(
            result["year"],
            errors="coerce"
        )

        result = result.sort_values(
            "year",
            ascending=False
        )

    return result.reset_index(drop=True)


def build_company_report_data(company_id):
    """
    Build the complete analytical data package for one company.
    """

    identity = get_company_identity(company_id)

    if identity is None:
        raise ValueError(
            f"Company '{company_id}' does not exist in the companies table."
        )

    return {
        "identity": identity,
        "financial_ratios": get_company_ratios(company_id),
        "market_cap": get_company_market_cap(company_id),
        "profit_and_loss": get_company_profit_loss(company_id),
        "cashflow": get_company_cashflow(company_id),
        "documents": get_company_documents(company_id),
    }


def print_report_summary(company_id):
    """Development helper used during Sprint 5 validation."""

    report = build_company_report_data(company_id)

    identity = report["identity"]

    print("=" * 80)
    print("SPRINT 5 — COMPANY REPORT DATA ENGINE")
    print("=" * 80)

    print(f"\nTicker: {company_id}")
    print(f"Company: {identity.get('company_name')}")
    print(f"Sector: {identity.get('broad_sector')}")
    print(f"Sub-sector: {identity.get('sub_sector')}")

    print("\nDATA COVERAGE")
    print("-" * 80)

    print(
        f"Financial ratio records : "
        f"{len(report['financial_ratios'])}"
    )

    print(
        f"Market-cap records      : "
        f"{len(report['market_cap'])}"
    )

    print(
        f"Profit & loss records   : "
        f"{len(report['profit_and_loss'])}"
    )

    print(
        f"Cash-flow records       : "
        f"{len(report['cashflow'])}"
    )

    print(
        f"Annual-report records   : "
        f"{len(report['documents'])}"
    )

    print("\nLATEST FINANCIAL RATIOS")
    print("-" * 80)

    ratios = report["financial_ratios"]

    if not ratios.empty:
        print(ratios.tail(1).to_string(index=False))
    else:
        print("No financial-ratio records available.")

    print("\nLATEST VALUATION")
    print("-" * 80)

    market_cap = report["market_cap"]

    if not market_cap.empty:
        print(market_cap.tail(1).to_string(index=False))
    else:
        print("No market-cap records available.")

    print("\n" + "=" * 80)
    print("COMPANY REPORT DATA BUILD COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    print_report_summary("ABB")