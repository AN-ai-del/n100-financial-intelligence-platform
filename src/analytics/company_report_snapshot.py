from typing import Any, Dict

import pandas as pd

from src.analytics.company_report_data import build_company_report_data


def safe_number(value, decimals=2):
    """
    Convert a value to a rounded numeric value where possible.
    Returns None for missing/non-numeric values.
    """
    if value is None:
        return None

    try:
        value = pd.to_numeric(value, errors="coerce")

        if pd.isna(value):
            return None

        return round(float(value), decimals)

    except (TypeError, ValueError):
        return None


def latest_row(df: pd.DataFrame) -> Dict[str, Any]:
    """Return the latest row of a dataframe as a dictionary."""
    if df is None or df.empty:
        return {}

    return df.iloc[-1].to_dict()


def build_company_snapshot(company_id: str) -> Dict[str, Any]:
    """
    Convert the company report data package into a concise,
    report-ready analytical snapshot.
    """

    report = build_company_report_data(company_id)

    identity = report["identity"]

    ratios = report["financial_ratios"]
    market_cap = report["market_cap"]
    pnl = report["profit_and_loss"]
    cashflow = report["cashflow"]
    documents = report["documents"]

    latest_ratios = latest_row(ratios)
    latest_valuation = latest_row(market_cap)

    snapshot = {
        # -------------------------------------------------
        # Identity
        # -------------------------------------------------
        "company_id": company_id,
        "company_name": identity.get("company_name"),
        "broad_sector": identity.get("broad_sector"),
        "sub_sector": identity.get("sub_sector"),

        # -------------------------------------------------
        # Profitability
        # -------------------------------------------------
        "net_profit_margin_pct": safe_number(
            latest_ratios.get("net_profit_margin_pct")
        ),
        "operating_profit_margin_pct": safe_number(
            latest_ratios.get("operating_profit_margin_pct")
        ),
        "return_on_equity_pct": safe_number(
            latest_ratios.get("return_on_equity_pct")
        ),

        # -------------------------------------------------
        # Balance-sheet / risk
        # -------------------------------------------------
        "debt_to_equity": safe_number(
            latest_ratios.get("debt_to_equity")
        ),
        "interest_coverage": safe_number(
            latest_ratios.get("interest_coverage")
        ),
        "total_debt_cr": safe_number(
            latest_ratios.get("total_debt_cr")
        ),

        # -------------------------------------------------
        # Cash flow
        # -------------------------------------------------
        "free_cash_flow_cr": safe_number(
            latest_ratios.get("free_cash_flow_cr")
        ),
        "cash_from_operations_cr": safe_number(
            latest_ratios.get("cash_from_operations_cr")
        ),
        "capex_cr": safe_number(
            latest_ratios.get("capex_cr")
        ),

        # -------------------------------------------------
        # Per-share metrics
        # -------------------------------------------------
        "earnings_per_share": safe_number(
            latest_ratios.get("earnings_per_share")
        ),
        "book_value_per_share": safe_number(
            latest_ratios.get("book_value_per_share")
        ),
        "dividend_payout_ratio_pct": safe_number(
            latest_ratios.get("dividend_payout_ratio_pct")
        ),

        # -------------------------------------------------
        # Valuation
        # -------------------------------------------------
        "market_cap_crore": safe_number(
            latest_valuation.get("market_cap_crore")
        ),
        "enterprise_value_crore": safe_number(
            latest_valuation.get("enterprise_value_crore")
        ),
        "pe_ratio": safe_number(
            latest_valuation.get("pe_ratio")
        ),
        "pb_ratio": safe_number(
            latest_valuation.get("pb_ratio")
        ),
        "ev_ebitda": safe_number(
            latest_valuation.get("ev_ebitda")
        ),
        "dividend_yield_pct": safe_number(
            latest_valuation.get("dividend_yield_pct")
        ),

        # -------------------------------------------------
        # Data coverage
        # -------------------------------------------------
        "financial_ratio_records": len(ratios),
        "valuation_records": len(market_cap),
        "profit_loss_records": len(pnl),
        "cashflow_records": len(cashflow),
        "annual_report_records": len(documents),
    }

    return snapshot


def validate_snapshot(snapshot: Dict[str, Any]):
    """
    Perform basic structural validation of the company snapshot.
    """

    required_fields = [
        "company_id",
        "company_name",
        "broad_sector",
        "sub_sector",
        "return_on_equity_pct",
        "debt_to_equity",
        "market_cap_crore",
        "pe_ratio",
    ]

    results = []

    for field in required_fields:
        value = snapshot.get(field)

        results.append(
            {
                "field": field,
                "available": value is not None,
                "value": value,
            }
        )

    return pd.DataFrame(results)


def print_snapshot(company_id: str):
    snapshot = build_company_snapshot(company_id)

    print("=" * 80)
    print("SPRINT 5 — COMPANY REPORT SNAPSHOT")
    print("=" * 80)

    print("\nIDENTITY")
    print("-" * 80)

    print(f"Ticker      : {snapshot['company_id']}")
    print(f"Company     : {snapshot['company_name']}")
    print(f"Sector      : {snapshot['broad_sector']}")
    print(f"Sub-sector  : {snapshot['sub_sector']}")

    print("\nPROFITABILITY")
    print("-" * 80)

    print(
        f"Net Profit Margin     : "
        f"{snapshot['net_profit_margin_pct']}"
    )

    print(
        f"Operating Margin      : "
        f"{snapshot['operating_profit_margin_pct']}"
    )

    print(
        f"ROE                   : "
        f"{snapshot['return_on_equity_pct']}"
    )

    print("\nFINANCIAL RISK")
    print("-" * 80)

    print(
        f"Debt / Equity         : "
        f"{snapshot['debt_to_equity']}"
    )

    print(
        f"Interest Coverage     : "
        f"{snapshot['interest_coverage']}"
    )

    print(
        f"Total Debt            : "
        f"{snapshot['total_debt_cr']}"
    )

    print("\nCASH FLOW")
    print("-" * 80)

    print(
        f"Free Cash Flow        : "
        f"{snapshot['free_cash_flow_cr']}"
    )

    print(
        f"Cash From Operations  : "
        f"{snapshot['cash_from_operations_cr']}"
    )

    print(
        f"CAPEX                 : "
        f"{snapshot['capex_cr']}"
    )

    print("\nVALUATION")
    print("-" * 80)

    print(
        f"Market Cap            : "
        f"{snapshot['market_cap_crore']}"
    )

    print(
        f"Enterprise Value      : "
        f"{snapshot['enterprise_value_crore']}"
    )

    print(f"P/E                   : {snapshot['pe_ratio']}")
    print(f"P/B                   : {snapshot['pb_ratio']}")
    print(f"EV / EBITDA           : {snapshot['ev_ebitda']}")

    print("\nDATA COVERAGE")
    print("-" * 80)

    print(
        f"Financial Ratios      : "
        f"{snapshot['financial_ratio_records']}"
    )

    print(
        f"Valuation Records     : "
        f"{snapshot['valuation_records']}"
    )

    print(
        f"P&L Records           : "
        f"{snapshot['profit_loss_records']}"
    )

    print(
        f"Cash-flow Records     : "
        f"{snapshot['cashflow_records']}"
    )

    print(
        f"Annual Reports        : "
        f"{snapshot['annual_report_records']}"
    )

    print("\nSNAPSHOT VALIDATION")
    print("-" * 80)

    validation = validate_snapshot(snapshot)

    print(validation.to_string(index=False))

    print("\n" + "=" * 80)

    if validation["available"].all():
        print("COMPANY REPORT SNAPSHOT VALIDATION PASSED")
    else:
        print("COMPANY REPORT SNAPSHOT VALIDATION COMPLETED WITH MISSING DATA")

    print("=" * 80)


if __name__ == "__main__":
    print_snapshot("ABB")