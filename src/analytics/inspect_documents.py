import sqlite3
import pandas as pd


DB_PATH = "db/nifty100.db"


def clean(value):
    if value is None:
        return ""

    text = str(value).strip()

    if text.lower() in {"nan", "none", "null"}:
        return ""

    return text


def main():
    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql_query(
        "SELECT * FROM documents",
        conn,
    )

    conn.close()

    print("=" * 80)
    print("DOCUMENT TABLE INSPECTION")
    print("=" * 80)

    print("\nRaw shape:")
    print(df.shape)

    print("\nRaw columns:")
    print(df.columns.tolist())

    print("\nFirst 5 raw rows:")
    print(df.head().to_string(index=False))

    # --------------------------------------------------------
    # Promote embedded header
    # --------------------------------------------------------

    for row_index in range(min(5, len(df))):

        row_values = [
            clean(value).lower()
            for value in df.iloc[row_index].tolist()
        ]

        if (
            "company_id" in row_values
            or "ticker" in row_values
        ):
            new_columns = []

            for i, value in enumerate(
                df.iloc[row_index].tolist()
            ):
                value = clean(value)

                if not value:
                    value = f"unnamed_{i}"

                value = (
                    value.lower()
                    .replace(" ", "_")
                    .replace("-", "_")
                    .replace("/", "_")
                )

                new_columns.append(value)

            df = df.iloc[row_index + 1:].copy()
            df.columns = new_columns
            df = df.reset_index(drop=True)

            break

    print("\n" + "=" * 80)
    print("AFTER HEADER REPAIR")
    print("=" * 80)

    print("\nColumns:")
    print(df.columns.tolist())

    company_col = None

    for candidate in [
        "company_id",
        "ticker",
        "symbol",
        "nse_ticker",
    ]:
        if candidate in df.columns:
            company_col = candidate
            break

    if company_col is None:
        print("\nCould not detect company column.")
        return

    abb = df[
        df[company_col]
        .astype(str)
        .str.strip()
        .str.upper()
        == "ABB"
    ].copy()

    print("\n" + "=" * 80)
    print("ABB DOCUMENT RECORDS")
    print("=" * 80)

    print("\nNumber of ABB rows:")
    print(len(abb))

    print("\nABB data:")
    print(
        abb.to_string(
            index=False,
            max_colwidth=120,
        )
    )

    print("\n" + "=" * 80)

    possible_url_columns = [
        column
        for column in df.columns
        if any(
            word in column.lower()
            for word in [
                "url",
                "link",
                "pdf",
                "document",
                "report",
            ]
        )
    ]

    print("Possible URL-related columns:")
    print(possible_url_columns)

    for column in possible_url_columns:
        print(f"\n--- {column} ---")

        if column in abb.columns:
            for value in abb[column].tolist():
                print(repr(value))


if __name__ == "__main__":
    main()