from pathlib import Path
import pandas as pd


RAW_DATA_DIR = Path("data/raw")


EXPECTED_FILES = [
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


def load_excel_file(file_name):
    """
    Load one Excel file from data/raw.
    """
    file_path = RAW_DATA_DIR / file_name

    if not file_path.exists():
        raise FileNotFoundError(f"Missing file: {file_path}")

    df = pd.read_excel(file_path)
    return df


def inspect_all_files():
    """
    Load all expected Excel files and print shape + columns.
    """
    summary = []

    for file_name in EXPECTED_FILES:
        df = load_excel_file(file_name)

        summary.append({
            "file_name": file_name,
            "rows": df.shape[0],
            "columns": df.shape[1],
            "column_names": list(df.columns)
        })

        print("\n" + "=" * 80)
        print(f"FILE: {file_name}")
        print(f"SHAPE: {df.shape}")
        print("COLUMNS:")
        for col in df.columns:
            print(f" - {col}")
        print("FIRST 3 ROWS:")
        print(df.head(3))

    return summary


if __name__ == "__main__":
    inspect_all_files()