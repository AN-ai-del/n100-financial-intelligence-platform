from pathlib import Path
import sqlite3
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"

# Change this only if your Excel source is stored somewhere else.
POSSIBLE_PATHS = [
    PROJECT_ROOT / "data" / "companies.xlsx",
    PROJECT_ROOT / "data" / "raw" / "companies.xlsx",
    PROJECT_ROOT / "companies.xlsx",
]


def find_companies_file():
    for path in POSSIBLE_PATHS:
        if path.exists():
            return path

    raise FileNotFoundError(
        "companies.xlsx could not be found.\n"
        "Checked:\n"
        + "\n".join(str(p) for p in POSSIBLE_PATHS)
    )


def repair_companies():

    excel_path = find_companies_file()

    print("=" * 60)
    print("REPAIRING COMPANIES TABLE")
    print("=" * 60)

    print(f"Source: {excel_path}")
    print(f"Database: {DB_PATH}")

    # IMPORTANT:
    # Row 1 of the Excel workbook contains the actual column names.
    df = pd.read_excel(
        excel_path,
        header=1
    )

    # Normalize column names.
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace(r"[^\w]+", "_", regex=True)
        .str.strip("_")
    )

    print("\nColumns found:")
    print(df.columns.tolist())

    # Normalize company ID.
    if "id" in df.columns:
        df["id"] = (
            df["id"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

    # Remove empty rows.
    df = df.dropna(how="all")

    # Remove rows without an ID.
    if "id" in df.columns:
        df = df[
            df["id"].notna()
            & ~df["id"].isin(["", "NAN", "NONE"])
        ]

    df = df.reset_index(drop=True)

    print(f"\nRows to insert: {len(df)}")

    print("\nPreview:")
    print(df.head())

    conn = sqlite3.connect(DB_PATH)

    try:
        df.to_sql(
            "companies",
            conn,
            if_exists="replace",
            index=False
        )

        conn.commit()

    finally:
        conn.close()

    print("\n" + "=" * 60)
    print("companies table repaired successfully.")
    print(f"Rows inserted: {len(df)}")
    print("=" * 60)


if __name__ == "__main__":
    repair_companies()