from pathlib import Path
import pandas as pd

RAW_DATA_DIR = Path("data/raw")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

CRITICAL = "CRITICAL"
WARNING = "WARNING"


def add_failure(failures, rule_id, severity, file_name, column, message):
    failures.append({
        "rule_id": rule_id,
        "severity": severity,
        "file_name": file_name,
        "column": column,
        "message": message
    })


def load_file(file_name):
    file_path = RAW_DATA_DIR / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"Missing file: {file_path}")
    return pd.read_excel(file_path)


def check_missing_file(failures, file_name, rule_id):
    file_path = RAW_DATA_DIR / file_name
    if not file_path.exists():
        add_failure(
            failures,
            rule_id,
            CRITICAL,
            file_name,
            "",
            "Required source file is missing"
        )


def check_empty_dataframe(failures, df, file_name, rule_id):
    if df.empty:
        add_failure(
            failures,
            rule_id,
            CRITICAL,
            file_name,
            "",
            "File has zero rows"
        )


def check_duplicate_rows(failures, df, file_name, rule_id):
    duplicate_count = df.duplicated().sum()
    if duplicate_count > 0:
        add_failure(
            failures,
            rule_id,
            WARNING,
            file_name,
            "",
            f"Found {duplicate_count} duplicate rows"
        )


def check_missing_values(failures, df, file_name, rule_id):
    missing = df.isnull().sum()

    for column, count in missing.items():
        if count > 0:
            add_failure(
                failures,
                rule_id,
                WARNING,
                file_name,
                column,
                f"Found {count} missing values"
            )


def check_required_columns(failures, df, file_name, required_columns, rule_id):
    for column in required_columns:
        if column not in df.columns:
            add_failure(
                failures,
                rule_id,
                CRITICAL,
                file_name,
                column,
                "Required column is missing"
            )


def validate_all_files():
    failures = []

    expected_files = [
        "companies.xlsx",
        "profitandloss.xlsx",
        "balancesheet.xlsx",
        "cashflow.xlsx",
        "analysis.xlsx",
        "documents.xlsx",
        "prosandcons.xlsx",
        "financial_ratios.xlsx",
        "market_cap.xlsx",
        "peer_groups.xlsx",
        "sectors.xlsx",
        "stock_prices.xlsx",
    ]

    for index, file_name in enumerate(expected_files, start=1):
        check_missing_file(failures, file_name, f"DQ-{index:02d}")

    for file_name in expected_files:
        file_path = RAW_DATA_DIR / file_name

        if not file_path.exists():
            continue

        df = load_file(file_name)

        check_empty_dataframe(failures, df, file_name, "DQ-01")
        check_duplicate_rows(failures, df, file_name, "DQ-02")
        check_missing_values(failures, df, file_name, "DQ-03")

    companies = load_file("companies.xlsx")

    check_required_columns(
        failures,
        companies,
        "companies.xlsx",
        ["Company Name"],
        "DQ-04"
    )

    output_path = OUTPUT_DIR / "validation_failures.csv"
    failures_df = pd.DataFrame(failures)

    if failures_df.empty:
        failures_df = pd.DataFrame(columns=[
            "rule_id",
            "severity",
            "file_name",
            "column",
            "message"
        ])

    failures_df.to_csv(output_path, index=False)

    print(f"Validation completed.")
    print(f"Total failures found: {len(failures_df)}")
    print(f"Saved to: {output_path}")

    return failures_df


if __name__ == "__main__":
    validate_all_files()