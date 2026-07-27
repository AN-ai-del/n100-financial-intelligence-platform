from pathlib import Path

import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "output"
    / "cashflow_intelligence.csv"
)

EXCEL_OUTPUT = (
    PROJECT_ROOT
    / "output"
    / "cashflow_intelligence.xlsx"
)

SUMMARY_OUTPUT = (
    PROJECT_ROOT
    / "output"
    / "capital_allocation_summary.csv"
)


# ============================================================
# LOAD DAY 31 OUTPUT
# ============================================================

def load_cashflow_intelligence():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Day 31 output not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    if df.empty:
        raise ValueError(
            "cashflow_intelligence.csv is empty."
        )

    required_columns = {
        "company_id",
        "company_name",
        "year",
        "year_numeric",
        "free_cash_flow_cr",
        "cfo_quality_label",
        "capex_intensity_label",
        "capital_allocation_pattern",
        "distress_flag",
        "cashflow_health_score",
        "cashflow_health_label",
    }

    missing = (
        required_columns
        - set(df.columns)
    )

    if missing:
        raise ValueError(
            "Missing required Day 31 columns: "
            + ", ".join(sorted(missing))
        )

    df["year_numeric"] = pd.to_numeric(
        df["year_numeric"],
        errors="coerce",
    )

    df["cashflow_health_score"] = pd.to_numeric(
        df["cashflow_health_score"],
        errors="coerce",
    )

    return df


# ============================================================
# LATEST COMPANY SNAPSHOT
# ============================================================

def build_latest_snapshot(df):

    valid = df[
        df["year_numeric"].notna()
    ].copy()

    valid = valid.sort_values(
        [
            "company_id",
            "year_numeric",
        ]
    )

    latest = (
        valid
        .groupby(
            "company_id",
            as_index=False,
        )
        .tail(1)
        .copy()
    )

    latest = latest.sort_values(
        "company_id"
    ).reset_index(drop=True)

    return latest


# ============================================================
# HEALTH SUMMARY
# ============================================================

def build_health_summary(latest):

    summary = (
        latest[
            "cashflow_health_label"
        ]
        .fillna("NOT_AVAILABLE")
        .value_counts()
        .rename_axis(
            "cashflow_health_label"
        )
        .reset_index(
            name="company_count"
        )
    )

    total = summary[
        "company_count"
    ].sum()

    summary[
        "percentage"
    ] = (
        summary["company_count"]
        / total
        * 100
    ).round(2)

    return summary


# ============================================================
# CAPITAL ALLOCATION SUMMARY
# ============================================================

def build_capital_allocation_summary(df):

    summary = (
        df[
            "capital_allocation_pattern"
        ]
        .fillna("NOT_AVAILABLE")
        .value_counts()
        .rename_axis(
            "capital_allocation_pattern"
        )
        .reset_index(
            name="record_count"
        )
    )

    total = summary[
        "record_count"
    ].sum()

    summary[
        "percentage"
    ] = (
        summary["record_count"]
        / total
        * 100
    ).round(2)

    return summary


# ============================================================
# DISTRESS COMPANY TABLE
# ============================================================

def build_distress_table(latest):

    distress = latest[
        latest[
            "cashflow_health_label"
        ].eq("Distress")
        |
        latest[
            "distress_flag"
        ].eq(True)
    ].copy()

    selected_columns = [
        "company_id",
        "company_name",
        "year",
        "year_numeric",
        "free_cash_flow_cr",
        "cfo_quality_label",
        "capex_intensity_label",
        "capital_allocation_pattern",
        "negative_fcf_3yr_flag",
        "negative_cfo_flag",
        "financing_dependence_flag",
        "capital_allocation_distress_flag",
        "distress_flag",
        "cashflow_health_score",
        "cashflow_health_label",
    ]

    selected_columns = [
        column
        for column in selected_columns
        if column in distress.columns
    ]

    distress = distress[
        selected_columns
    ].copy()

    distress = distress.sort_values(
        [
            "cashflow_health_score",
            "company_id",
        ],
        ascending=[
            True,
            True,
        ],
    )

    return distress.reset_index(
        drop=True
    )


# ============================================================
# DATA COVERAGE
# ============================================================

def build_data_coverage(df, latest):

    coverage = pd.DataFrame(
        [
            {
                "metric":
                    "Cash-flow intelligence records",
                "value":
                    len(df),
            },
            {
                "metric":
                    "Companies with cash-flow intelligence",
                "value":
                    df[
                        "company_id"
                    ].nunique(),
            },
            {
                "metric":
                    "Latest company snapshots",
                "value":
                    latest[
                        "company_id"
                    ].nunique(),
            },
            {
                "metric":
                    "Minimum financial year",
                "value":
                    int(
                        df[
                            "year_numeric"
                        ].min()
                    ),
            },
            {
                "metric":
                    "Maximum financial year",
                "value":
                    int(
                        df[
                            "year_numeric"
                        ].max()
                    ),
            },
            {
                "metric":
                    "Distress latest snapshots",
                "value":
                    int(
                        (
                            latest[
                                "cashflow_health_label"
                            ]
                            == "Distress"
                        ).sum()
                    ),
            },
        ]
    )

    return coverage


# ============================================================
# EXCEL FORMATTING
# ============================================================

def format_worksheet(
    worksheet,
    dataframe,
):

    worksheet.freeze_panes = "A2"

    worksheet.auto_filter.ref = (
        worksheet.dimensions
    )

    for column_cells in worksheet.columns:

        column_letter = (
            column_cells[0]
            .column_letter
        )

        max_length = 0

        for cell in column_cells:

            value = cell.value

            if value is None:
                continue

            max_length = max(
                max_length,
                len(str(value)),
            )

        worksheet.column_dimensions[
            column_letter
        ].width = min(
            max_length + 2,
            45,
        )


# ============================================================
# WRITE EXCEL WORKBOOK
# ============================================================

def write_excel_report(
    df,
    latest,
    health_summary,
    allocation_summary,
    distress,
    coverage,
):

    EXCEL_OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with pd.ExcelWriter(
        EXCEL_OUTPUT,
        engine="openpyxl",
    ) as writer:

        df.to_excel(
            writer,
            sheet_name="Cash Flow Intelligence",
            index=False,
        )

        latest.to_excel(
            writer,
            sheet_name="Latest Company Snapshot",
            index=False,
        )

        health_summary.to_excel(
            writer,
            sheet_name="Health Summary",
            index=False,
        )

        allocation_summary.to_excel(
            writer,
            sheet_name="Capital Allocation",
            index=False,
        )

        distress.to_excel(
            writer,
            sheet_name="Distress Companies",
            index=False,
        )

        coverage.to_excel(
            writer,
            sheet_name="Data Coverage",
            index=False,
        )

        workbook = writer.book

        for worksheet in (
            workbook.worksheets
        ):
            format_worksheet(
                worksheet,
                pd.DataFrame(),
            )


# ============================================================
# VALIDATION
# ============================================================

def validate_report(
    df,
    latest,
    health_summary,
    allocation_summary,
    distress,
):

    print("\n" + "=" * 100)
    print(
        "SPRINT 5 — DAY 32 "
        "CASH FLOW REPORT VALIDATION"
    )
    print("=" * 100)

    print(
        f"\nIntelligence records : {len(df)}"
    )

    print(
        "Companies covered    : "
        f"{df['company_id'].nunique()}"
    )

    print(
        "Latest snapshots     : "
        f"{latest['company_id'].nunique()}"
    )

    print(
        "Health categories    : "
        f"{len(health_summary)}"
    )

    print(
        "Allocation patterns  : "
        f"{len(allocation_summary)}"
    )

    print(
        "Latest distress rows : "
        f"{len(distress)}"
    )

    print(
        "\nLATEST HEALTH DISTRIBUTION"
    )
    print("-" * 100)

    print(
        health_summary.to_string(
            index=False
        )
    )

    print(
        "\nCAPITAL ALLOCATION DISTRIBUTION"
    )
    print("-" * 100)

    print(
        allocation_summary.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # Validation checks
    # --------------------------------------------------------

    duplicate_latest = (
        latest[
            "company_id"
        ].duplicated().sum()
    )

    allocation_total = (
        allocation_summary[
            "record_count"
        ].sum()
    )

    health_total = (
        health_summary[
            "company_count"
        ].sum()
    )

    invalid_scores = (
        ~latest[
            "cashflow_health_score"
        ].between(
            0,
            100,
            inclusive="both",
        )
    ).sum()

    print(
        "\nVALIDATION CHECKS"
    )
    print("-" * 100)

    print(
        "Duplicate latest companies : "
        f"{duplicate_latest}"
    )

    print(
        "Allocation summary records : "
        f"{allocation_total}/{len(df)}"
    )

    print(
        "Health summary companies   : "
        f"{health_total}/{len(latest)}"
    )

    print(
        "Invalid latest scores      : "
        f"{invalid_scores}"
    )

    if duplicate_latest != 0:
        raise ValueError(
            "Duplicate companies found "
            "in latest snapshot."
        )

    if allocation_total != len(df):
        raise ValueError(
            "Capital-allocation summary "
            "does not reconcile."
        )

    if health_total != len(latest):
        raise ValueError(
            "Health summary does not "
            "reconcile."
        )

    if invalid_scores != 0:
        raise ValueError(
            "Invalid cash-flow health "
            "scores detected."
        )

    print("\n" + "=" * 100)
    print(
        "DAY 32 VALIDATION PASSED"
    )
    print("=" * 100)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 100)
    print(
        "SPRINT 5 — DAY 32 "
        "CASH FLOW INTELLIGENCE REPORTING"
    )
    print("=" * 100)

    df = load_cashflow_intelligence()

    latest = build_latest_snapshot(
        df
    )

    health_summary = (
        build_health_summary(
            latest
        )
    )

    allocation_summary = (
        build_capital_allocation_summary(
            df
        )
    )

    distress = build_distress_table(
        latest
    )

    coverage = build_data_coverage(
        df,
        latest,
    )

    validate_report(
        df,
        latest,
        health_summary,
        allocation_summary,
        distress,
    )

    write_excel_report(
        df,
        latest,
        health_summary,
        allocation_summary,
        distress,
        coverage,
    )

    allocation_summary.to_csv(
        SUMMARY_OUTPUT,
        index=False,
    )

    print("\nOUTPUT FILES")
    print("-" * 100)

    print(
        f"Excel workbook:\n{EXCEL_OUTPUT}"
    )

    print(
        "\nCapital-allocation summary:\n"
        f"{SUMMARY_OUTPUT}"
    )

    print("\n" + "=" * 100)
    print(
        "SPRINT 5 — DAY 32 "
        "REPORT GENERATION COMPLETE"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()