from pathlib import Path
import sqlite3
import pandas as pd

DB_PATH = Path("db/nifty100.db")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


def table_exists(conn, table_name):
    query = """
    SELECT name FROM sqlite_master
    WHERE type='table' AND name=?;
    """
    result = pd.read_sql_query(query, conn, params=(table_name,))
    return not result.empty


def get_column_names(conn, table_name):
    result = pd.read_sql_query(f"PRAGMA table_info({table_name});", conn)
    return result["name"].tolist()


def find_company_column(columns):
    for possible in ["company_name", "company", "name", "companyname"]:
        if possible in columns:
            return possible
    return columns[0]


def find_year_column(columns):
    for possible in ["year", "financial_year", "fy"]:
        if possible in columns:
            return possible
    return None


def count_company_rows(conn, table_name, company_col, company_name):
    query = f"""
    SELECT COUNT(*) as row_count
    FROM {table_name}
    WHERE {company_col} = ?;
    """
    result = pd.read_sql_query(query, conn, params=(company_name,))
    return int(result["row_count"].iloc[0])


def get_year_range(conn, table_name, company_col, year_col, company_name):
    if year_col is None:
        return ""

    query = f"""
    SELECT MIN({year_col}) as min_year, MAX({year_col}) as max_year
    FROM {table_name}
    WHERE {company_col} = ?;
    """
    result = pd.read_sql_query(query, conn, params=(company_name,))

    min_year = result["min_year"].iloc[0]
    max_year = result["max_year"].iloc[0]

    if pd.isna(min_year) or pd.isna(max_year):
        return ""

    return f"{int(min_year)}-{int(max_year)}"


def run_manual_review():
    conn = sqlite3.connect(DB_PATH)

    companies_df = pd.read_sql_query("SELECT * FROM companies LIMIT 5;", conn)
    company_columns = companies_df.columns.tolist()
    company_col = find_company_column(company_columns)

    selected_companies = companies_df[company_col].dropna().head(5).tolist()

    review_records = []

    tables_to_check = [
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "stock_prices",
    ]

    for company_name in selected_companies:
        record = {
            "company_name": company_name,
            "review_status": "PASS",
            "notes": ""
        }

        notes = []

        for table_name in tables_to_check:
            if not table_exists(conn, table_name):
                record[f"{table_name}_rows"] = 0
                record[f"{table_name}_years"] = ""
                notes.append(f"{table_name} table missing")
                record["review_status"] = "FAIL"
                continue

            columns = get_column_names(conn, table_name)
            table_company_col = find_company_column(columns)
            year_col = find_year_column(columns)

            try:
                row_count = count_company_rows(
                    conn,
                    table_name,
                    table_company_col,
                    company_name
                )

                year_range = get_year_range(
                    conn,
                    table_name,
                    table_company_col,
                    year_col,
                    company_name
                )

                record[f"{table_name}_rows"] = row_count
                record[f"{table_name}_years"] = year_range

                if row_count == 0:
                    notes.append(f"No rows found in {table_name}")
                    record["review_status"] = "WARNING"

            except Exception as e:
                record[f"{table_name}_rows"] = 0
                record[f"{table_name}_years"] = ""
                notes.append(f"Error checking {table_name}: {e}")
                record["review_status"] = "WARNING"

        record["notes"] = "; ".join(notes) if notes else "Data available across reviewed tables"
        review_records.append(record)

    review_df = pd.DataFrame(review_records)
    output_path = OUTPUT_DIR / "manual_review_day06.csv"
    review_df.to_csv(output_path, index=False)

    print("Manual review completed.")
    print(review_df)
    print(f"Saved to: {output_path}")

    conn.close()


if __name__ == "__main__":
    run_manual_review()