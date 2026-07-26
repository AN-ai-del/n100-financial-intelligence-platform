import pandas as pd
import streamlit as st

from src.dashboard.utils.db import get_companies, run_query


# ============================================================
# PAGE HEADER
# ============================================================

st.title("📚 Annual Reports")

st.caption(
    "Search Nifty 100 companies and access available annual reports "
    "and corporate documents."
)


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    """
    Safely converts a value to a cleaned string.
    """
    if value is None:
        return ""

    text = str(value).strip()

    if text.lower() in {
        "",
        "nan",
        "none",
        "null",
        "nat",
    }:
        return ""

    return text


def normalize_column_name(value):
    """
    Normalizes raw column/header text.
    """
    return (
        clean_text(value)
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace("(", "")
        .replace(")", "")
        .strip("_")
    )


def repair_embedded_header(df):
    """
    Some project tables were imported with the real Excel header
    stored as the first database row.

    Example:
        current columns:
            weird_title_column
            unnamed:_1
            unnamed:_2
            unnamed:_3

        first row:
            id
            company_id
            Year
            Annual_Report

    This function promotes that row into the actual dataframe header.
    """

    if df is None or df.empty:
        return df

    df = df.copy()

    # Already repaired.
    normalized_existing = {
        normalize_column_name(col)
        for col in df.columns
    }

    if (
        "company_id" in normalized_existing
        and (
            "annual_report" in normalized_existing
            or "annual_report_url" in normalized_existing
        )
    ):
        df.columns = [
            normalize_column_name(col)
            for col in df.columns
        ]

        return df

    # Search the first few rows for embedded headers.
    search_rows = min(10, len(df))

    for row_index in range(search_rows):

        values = [
            normalize_column_name(value)
            for value in df.iloc[row_index].tolist()
        ]

        has_company = any(
            value in {
                "company_id",
                "ticker",
                "symbol",
                "nse_ticker",
            }
            for value in values
        )

        has_report = any(
            value in {
                "annual_report",
                "annual_report_url",
                "report_url",
                "url",
            }
            for value in values
        )

        if has_company and has_report:

            new_columns = []

            for index, value in enumerate(
                df.iloc[row_index].tolist()
            ):
                cleaned = normalize_column_name(value)

                if not cleaned:
                    cleaned = f"unnamed_{index}"

                new_columns.append(cleaned)

            df = df.iloc[row_index + 1:].copy()

            df.columns = new_columns

            df = df.reset_index(drop=True)

            return df

    # At minimum normalize existing names.
    df.columns = [
        normalize_column_name(col)
        for col in df.columns
    ]

    return df


def find_column(df, candidates):
    """
    Finds the first existing column from candidate names.
    """

    if df is None or df.empty:
        return None

    lookup = {
        normalize_column_name(column): column
        for column in df.columns
    }

    for candidate in candidates:

        normalized = normalize_column_name(candidate)

        if normalized in lookup:
            return lookup[normalized]

    return None


def normalize_company_id(value):
    return clean_text(value).upper()


def normalize_year(value):
    """
    Extract a display year from values such as:

    2024
    Mar-24
    Mar 2024
    Dec 2012
    """

    text = clean_text(value)

    if not text:
        return None

    # Numeric values like 2024 / 2024.0
    try:
        numeric = float(text)

        if 1900 <= numeric <= 2100:
            return int(numeric)

    except (TypeError, ValueError):
        pass

    # Look for normal four-digit year.
    import re

    four_digit = re.search(
        r"\b(19\d{2}|20\d{2}|21\d{2})\b",
        text,
    )

    if four_digit:
        return int(four_digit.group(1))

    # Handle Mar-24, Mar-23 etc.
    two_digit = re.search(
        r"(?<!\d)(\d{2})(?!\d)",
        text,
    )

    if two_digit:

        value = int(two_digit.group(1))

        if value <= 50:
            return 2000 + value

        return 1900 + value

    return None


def valid_report_url(value):
    """
    Determines whether the dataset contains a usable report URL.

    We deliberately do NOT make an HTTP request here because:
    - BSE can reject automated requests,
    - report availability should reflect the supplied dataset,
    - checking dozens of links would slow Streamlit considerably.
    """

    url = clean_text(value)

    if not url:
        return False

    return (
        url.lower().startswith("http://")
        or url.lower().startswith("https://")
    )


def build_company_label(row):
    """
    Returns:
        ABB — Abbott India Ltd
    """

    ticker = normalize_company_id(
        row.get("id", row.get("company_id", ""))
    )

    company_name = clean_text(
        row.get("company_name", "")
    )

    if company_name:
        return f"{ticker} — {company_name}"

    return ticker


# ============================================================
# LOAD COMPANY MASTER
# ============================================================

try:
    companies = get_companies()

except Exception as exc:
    st.error(
        "Unable to load the company master."
    )
    st.exception(exc)
    st.stop()


if companies is None or companies.empty:
    st.error(
        "The company master contains no records."
    )
    st.stop()


companies = companies.copy()

companies.columns = [
    normalize_column_name(column)
    for column in companies.columns
]


# ============================================================
# IDENTIFY COMPANY FIELDS
# ============================================================

company_id_col = find_column(
    companies,
    [
        "id",
        "company_id",
        "ticker",
        "symbol",
        "nse_ticker",
    ],
)

company_name_col = find_column(
    companies,
    [
        "company_name",
        "name",
    ],
)


if company_id_col is None:
    st.error(
        "Could not identify the company ticker column."
    )
    st.stop()


companies["ticker_clean"] = (
    companies[company_id_col]
    .astype(str)
    .str.strip()
    .str.upper()
)


if company_name_col:
    companies["company_name_clean"] = (
        companies[company_name_col]
        .fillna("")
        .astype(str)
        .str.strip()
    )

else:
    companies["company_name_clean"] = ""


companies = companies[
    companies["ticker_clean"] != ""
].copy()


companies["search_label"] = companies.apply(
    lambda row: (
        f"{row['ticker_clean']} — "
        f"{row['company_name_clean']}"
        if row["company_name_clean"]
        else row["ticker_clean"]
    ),
    axis=1,
)


companies = (
    companies
    .sort_values(
        "search_label"
    )
    .drop_duplicates(
        subset=["ticker_clean"]
    )
    .reset_index(drop=True)
)


# ============================================================
# COMPANY SEARCH
# ============================================================

st.subheader("🔎 Find a Company")

search_text = st.text_input(
    "Search by company name or ticker",
    placeholder="Example: TCS, RELIANCE, HDFCBANK...",
)


filtered_companies = companies.copy()


if search_text.strip():

    query = search_text.strip().lower()

    filtered_companies = filtered_companies[
        filtered_companies[
            "search_label"
        ]
        .str.lower()
        .str.contains(
            query,
            regex=False,
            na=False,
        )
    ]


if filtered_companies.empty:

    st.warning(
        "No companies match your search."
    )

    st.stop()


selected_label = st.selectbox(
    "Select company",
    filtered_companies[
        "search_label"
    ].tolist(),
)


selected_company = (
    filtered_companies[
        filtered_companies[
            "search_label"
        ]
        == selected_label
    ]
    .iloc[0]
)


ticker = selected_company[
    "ticker_clean"
]


company_name = selected_company[
    "company_name_clean"
]


if not company_name:
    company_name = ticker


# ============================================================
# LOAD DOCUMENT DATA
# ============================================================

try:

    documents = run_query(
        "SELECT * FROM documents"
    )

except Exception as exc:

    st.error(
        "Unable to load annual-report data."
    )

    st.exception(exc)

    st.stop()


if documents is None or documents.empty:

    st.warning(
        "No document records are available."
    )

    st.stop()


documents = repair_embedded_header(
    documents
)


# ============================================================
# IDENTIFY DOCUMENT FIELDS
# ============================================================

document_company_col = find_column(
    documents,
    [
        "company_id",
        "ticker",
        "symbol",
        "nse_ticker",
    ],
)


year_col = find_column(
    documents,
    [
        "year",
        "financial_year",
        "fy",
    ],
)


report_url_col = find_column(
    documents,
    [
        # This is the exact field in your dataset.
        "annual_report",

        # Fallbacks for future schema variations.
        "annual_report_url",
        "report_url",
        "annualreport",
        "document_url",
        "pdf_url",
        "url",
        "link",
    ],
)


if document_company_col is None:

    st.error(
        "The documents table does not contain "
        "a recognizable company column."
    )

    st.write(
        "Available columns:",
        documents.columns.tolist(),
    )

    st.stop()


if year_col is None:

    st.error(
        "The documents table does not contain "
        "a recognizable year column."
    )

    st.write(
        "Available columns:",
        documents.columns.tolist(),
    )

    st.stop()


if report_url_col is None:

    st.error(
        "The documents table does not contain "
        "a recognizable annual-report URL column."
    )

    st.write(
        "Available columns:",
        documents.columns.tolist(),
    )

    st.stop()


# ============================================================
# FILTER SELECTED COMPANY
# ============================================================

documents["_ticker"] = (
    documents[document_company_col]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.upper()
)


documents["_year"] = (
    documents[year_col]
    .apply(normalize_year)
)


documents["_report_url"] = (
    documents[report_url_col]
    .apply(clean_text)
)


company_documents = documents[
    documents["_ticker"] == ticker
].copy()


company_documents = company_documents[
    company_documents[
        "_year"
    ].notna()
].copy()


company_documents["_year"] = (
    company_documents[
        "_year"
    ].astype(int)
)


company_documents = (
    company_documents
    .sort_values(
        "_year",
        ascending=False,
    )
    .drop_duplicates(
        subset=["_year"],
        keep="first",
    )
    .reset_index(drop=True)
)


# ============================================================
# COMPANY SUMMARY
# ============================================================

st.divider()

st.subheader(
    f"🏢 {company_name}"
)


summary_col1, summary_col2 = st.columns(2)


with summary_col1:

    st.metric(
        "NSE Ticker",
        ticker,
    )


with summary_col2:

    st.metric(
        "Company",
        company_name,
    )


st.divider()


# ============================================================
# NO REPORT RECORDS
# ============================================================

if company_documents.empty:

    st.warning(
        "No annual-report records are available "
        "for this company in the supplied dataset."
    )

    st.stop()


# ============================================================
# REPORT METRICS
# ============================================================

valid_report_mask = (
    company_documents[
        "_report_url"
    ]
    .apply(valid_report_url)
)


report_count = int(
    valid_report_mask.sum()
)


years_available = int(
    company_documents[
        "_year"
    ]
    .nunique()
)


latest_year = int(
    company_documents[
        "_year"
    ]
    .max()
)


st.subheader(
    "📄 Available Annual Reports"
)


metric1, metric2, metric3 = st.columns(3)


with metric1:

    st.metric(
        "Reports Available",
        report_count,
    )


with metric2:

    st.metric(
        "Years Available",
        years_available,
    )


with metric3:

    st.metric(
        "Latest Report",
        latest_year,
    )


# ============================================================
# REPORT LIBRARY
# ============================================================

st.subheader(
    "📑 Report Library"
)


for _, row in company_documents.iterrows():

    year = int(
        row["_year"]
    )

    report_url = clean_text(
        row["_report_url"]
    )

    col_year, col_type, col_action = st.columns(
        [1.0, 2.1, 1.7]
    )


    with col_year:

        st.markdown(
            f"### {year}"
        )


    with col_type:

        st.markdown(
            "**Annual Report**"
        )


    with col_action:

        if valid_report_url(
            report_url
        ):

            st.link_button(
                "📖 Open Annual Report",
                report_url,
                width="stretch",
            )

        else:

            st.error(
                "🔴 Report unavailable"
            )


    st.divider()


# ============================================================
# EXPORT REPORT INDEX
# ============================================================

st.subheader(
    "⬇️ Export Report Index"
)


export_df = (
    company_documents[
        [
            "_ticker",
            "_year",
            "_report_url",
        ]
    ]
    .rename(
        columns={
            "_ticker":
                "Ticker",

            "_year":
                "Year",

            "_report_url":
                "Annual Report URL",
        }
    )
    .copy()
)


export_df.insert(
    1,
    "Company",
    company_name,
)


export_df[
    "Report Available"
] = export_df[
    "Annual Report URL"
].apply(
    lambda value:
        "Yes"
        if valid_report_url(value)
        else "No"
)


csv_data = export_df.to_csv(
    index=False
).encode("utf-8")


st.download_button(
    label="📥 Download Annual Report Index as CSV",
    data=csv_data,
    file_name=(
        f"{ticker}_annual_reports.csv"
    ),
    mime="text/csv",
)


st.caption(
    "Annual-report links are sourced from the documents "
    "dataset provided with the Nifty 100 project."
)