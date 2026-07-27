"""
Sprint 5 — Day 29

Multi-company validation for the Company Report Data Engine
and Company Report Snapshot Engine.
"""

from typing import Dict, List

import pandas as pd

from src.analytics.company_report_snapshot import (
    build_company_snapshot,
    validate_snapshot,
)


# ---------------------------------------------------------------------
# Representative companies
# ---------------------------------------------------------------------

TEST_COMPANIES = [
    "ABB",
    "RELIANCE",
    "TCS",
    "HDFCBANK",
    "INFY",
    "MARUTI",
    "TATAMOTORS",
    "SBIN",
    "ITC",
    "BHARTIARTL",
]


def validate_company(company_id: str) -> Dict:
    """
    Build and validate the report snapshot for one company.
    """

    result = {
        "company_id": company_id,
        "company_name": None,
        "snapshot_created": False,
        "required_fields_available": False,
        "financial_ratio_records": 0,
        "valuation_records": 0,
        "pnl_records": 0,
        "cashflow_records": 0,
        "annual_report_records": 0,
        "status": "FAILED",
        "error": None,
    }

    try:
        snapshot = build_company_snapshot(company_id)

        result["snapshot_created"] = True
        result["company_name"] = snapshot.get("company_name")

        result["financial_ratio_records"] = snapshot.get(
            "financial_ratio_records", 0
        )

        result["valuation_records"] = snapshot.get(
            "valuation_records", 0
        )

        result["pnl_records"] = snapshot.get(
            "profit_loss_records", 0
        )

        result["cashflow_records"] = snapshot.get(
            "cashflow_records", 0
        )

        result["annual_report_records"] = snapshot.get(
            "annual_report_records", 0
        )

        validation = validate_snapshot(snapshot)

        required_available = bool(
            validation["available"].all()
        )

        result["required_fields_available"] = required_available

        if required_available:
            result["status"] = "PASS"
        else:
            result["status"] = "PARTIAL"

    except Exception as exc:
        result["error"] = str(exc)
        result["status"] = "FAILED"

    return result


def run_multi_company_validation(
    company_ids: List[str],
) -> pd.DataFrame:
    """
    Validate the reporting pipeline across multiple companies.
    """

    results = []

    for company_id in company_ids:
        print(f"Validating {company_id}...")

        result = validate_company(company_id)

        results.append(result)

    return pd.DataFrame(results)


def print_summary(results: pd.DataFrame):
    """
    Print readable validation summary.
    """

    print("\n" + "=" * 100)
    print("SPRINT 5 — DAY 29 MULTI-COMPANY REPORT VALIDATION")
    print("=" * 100)

    display_columns = [
        "company_id",
        "company_name",
        "snapshot_created",
        "required_fields_available",
        "financial_ratio_records",
        "valuation_records",
        "pnl_records",
        "cashflow_records",
        "annual_report_records",
        "status",
    ]

    print(
        results[display_columns].to_string(
            index=False
        )
    )

    print("\n" + "-" * 100)

    total = len(results)

    passed = int(
        (results["status"] == "PASS").sum()
    )

    partial = int(
        (results["status"] == "PARTIAL").sum()
    )

    failed = int(
        (results["status"] == "FAILED").sum()
    )

    print(f"Companies tested : {total}")
    print(f"PASS             : {passed}")
    print(f"PARTIAL          : {partial}")
    print(f"FAILED           : {failed}")

    if total:
        pass_rate = (passed / total) * 100
    else:
        pass_rate = 0

    print(f"Pass rate        : {pass_rate:.1f}%")

    print("-" * 100)

    if failed == 0:
        print(
            "COMPANY REPORT PIPELINE EXECUTED "
            "SUCCESSFULLY FOR ALL TEST COMPANIES."
        )
    else:
        print(
            "ONE OR MORE COMPANY REPORT PIPELINES FAILED."
        )

    if partial > 0:
        print(
            "Some companies contain missing optional or "
            "required analytical fields."
        )

    print("=" * 100)


def save_validation_report(results: pd.DataFrame):
    """
    Save Day 29 validation results.
    """

    output_path = (
        "output/sprint5_day29_company_validation.csv"
    )

    results.to_csv(
        output_path,
        index=False,
    )

    print(
        f"\nValidation report saved to: {output_path}"
    )


def main():
    results = run_multi_company_validation(
        TEST_COMPANIES
    )

    print_summary(results)

    save_validation_report(results)


if __name__ == "__main__":
    main()