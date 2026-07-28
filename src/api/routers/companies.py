"""Company-data endpoints for the Nifty 100 REST API."""

from __future__ import annotations

import math
import re
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from src.api.database import create_connection


router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

EXPECTED_COMPANY_COUNT = 92

HISTORY_TABLES = {
    "pl": "profitandloss",
    "bs": "balancesheet",
    "cashflow": "cashflow",
    "ratios": "financial_ratios",
}


# =============================================================================
# GENERIC HELPERS
# =============================================================================

def clean_text(value: Any) -> str | None:
    """Return cleaned text or None."""

    if value is None:
        return None

    text = str(value).strip()

    if text.lower() in {
        "",
        "none",
        "null",
        "nan",
        "na",
        "n/a",
    }:
        return None

    return text


def clean_number(value: Any) -> int | float | None:
    """Convert database values into JSON-safe numbers."""

    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None

        return value

    text = (
        str(value)
        .replace(",", "")
        .replace("%", "")
        .replace("₹", "")
        .strip()
    )

    if text.lower() in {
        "",
        "none",
        "null",
        "nan",
        "na",
        "n/a",
        "-",
    }:
        return None

    try:
        number = float(text)

    except (TypeError, ValueError):
        return None

    if math.isnan(number) or math.isinf(number):
        return None

    if number.is_integer():
        return int(number)

    return number


def normalize_column_name(value: Any) -> str:
    """Normalize a database column name to snake_case."""

    text = str(value).strip().lower()

    text = re.sub(
        r"[^a-z0-9]+",
        "_",
        text,
    )

    return text.strip("_")


def normalize_ticker(ticker: str) -> str:
    """Normalize an NSE ticker supplied through the API."""

    return ticker.strip().upper()


def quote_identifier(identifier: str) -> str:
    """Safely quote one SQLite identifier."""

    escaped = identifier.replace(
        '"',
        '""',
    )

    return f'"{escaped}"'


def table_exists(
    connection: sqlite3.Connection,
    table_name: str,
) -> bool:
    """Return whether a SQLite table exists."""

    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        LIMIT 1
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_table_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> list[str]:
    """Return physical SQLite columns for a table."""

    if not table_exists(
        connection,
        table_name,
    ):
        return []

    rows = connection.execute(
        f"PRAGMA table_info("
        f"{quote_identifier(table_name)}"
        f")"
    ).fetchall()

    return [
        str(row["name"])
        for row in rows
    ]


def serialize_value(value: Any) -> Any:
    """Convert one database value into a JSON-safe value."""

    if value is None:
        return None

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None

    return value


def serialize_row(
    row: sqlite3.Row,
) -> dict[str, Any]:
    """Convert a SQLite row into a JSON-compatible dictionary."""

    return {
        normalize_column_name(key):
            serialize_value(row[key])
        for key in row.keys()
    }

def first_available(
    record: dict[str, Any],
    candidates: list[str],
) -> Any:
    """Return the first non-empty value among candidate fields."""

    for candidate in candidates:
        value = record.get(candidate)

        if value is not None:
            if isinstance(value, str):
                if value.strip():
                    return value

            else:
                return value

    return None


# =============================================================================
# YEAR HELPERS
# =============================================================================

def normalize_year(value: Any) -> str | None:
    """
    Convert project year formats into YYYY-MM.

    Examples:
        Mar 2024 -> 2024-03
        Mar-24   -> 2024-03
        Dec 2022 -> 2022-12
        FY24     -> 2024-03
        2024     -> 2024-03
    """

    text = clean_text(value)

    if text is None:
        return None

    text = text.strip()

    already_normalized = re.fullmatch(
        r"(19|20)\d{2}-(0[1-9]|1[0-2])",
        text,
    )

    if already_normalized:
        return text

    month_map = {
        "jan": "01",
        "feb": "02",
        "mar": "03",
        "apr": "04",
        "may": "05",
        "jun": "06",
        "jul": "07",
        "aug": "08",
        "sep": "09",
        "sept": "09",
        "oct": "10",
        "nov": "11",
        "dec": "12",
    }

    lowercase = text.lower()

    month = None

    for month_name, month_number in month_map.items():
        if month_name in lowercase:
            month = month_number
            break

    year_match = re.search(
        r"(19|20)\d{2}",
        text,
    )

    if year_match:
        year = int(
            year_match.group()
        )

        return (
            f"{year:04d}-"
            f"{month or '03'}"
        )

    short_year_match = re.search(
        r"(?:fy\s*)?(\d{2})$",
        lowercase,
    )

    if short_year_match:
        short_year = int(
            short_year_match.group(1)
        )

        year = (
            2000 + short_year
            if short_year <= 79
            else 1900 + short_year
        )

        return (
            f"{year:04d}-"
            f"{month or '03'}"
        )

    integer_year_match = re.fullmatch(
        r"\d{4}",
        text,
    )

    if integer_year_match:
        return f"{text}-03"

    return None


def validate_year_parameter(
    value: str | None,
    parameter_name: str,
) -> str | None:
    """Validate an optional API year parameter."""

    if value is None:
        return None

    if not re.fullmatch(
        r"(19|20)\d{2}-(0[1-9]|1[0-2])",
        value,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"{parameter_name} must use "
                "YYYY-MM format."
            ),
        )

    return value


def filter_history_by_year(
    records: list[dict[str, Any]],
    from_year: str | None,
    to_year: str | None,
) -> list[dict[str, Any]]:
    """Filter, deduplicate and sort financial history by year."""

    from_year = validate_year_parameter(
        from_year,
        "from_year",
    )

    to_year = validate_year_parameter(
        to_year,
        "to_year",
    )

    if (
        from_year is not None
        and to_year is not None
        and from_year > to_year
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "from_year cannot be later "
                "than to_year."
            ),
        )

    yearly_records: dict[
        str,
        dict[str, Any],
    ] = {}

    for record in records:
        raw_year = first_available(
            record,
            [
                "year",
                "financial_year",
                "date",
            ],
        )

        normalized_year = normalize_year(
            raw_year
        )

        if normalized_year is None:
            continue

        if (
            from_year is not None
            and normalized_year < from_year
        ):
            continue

        if (
            to_year is not None
            and normalized_year > to_year
        ):
            continue

        cleaned_record = (
            record.copy()
        )

        cleaned_record[
            "normalized_year"
        ] = normalized_year

        existing_record = (
            yearly_records.get(
                normalized_year
            )
        )

        if existing_record is None:
            yearly_records[
                normalized_year
            ] = cleaned_record

            continue

        existing_completeness = sum(
            value is not None
            for value in existing_record.values()
        )

        new_completeness = sum(
            value is not None
            for value in cleaned_record.values()
        )

        existing_id = clean_number(
            existing_record.get(
                "id"
            )
        )

        new_id = clean_number(
            cleaned_record.get(
                "id"
            )
        )

        should_replace = (
            new_completeness
            > existing_completeness
        )

        if (
            new_completeness
            == existing_completeness
            and isinstance(new_id, int)
            and (
                not isinstance(
                    existing_id,
                    int,
                )
                or new_id > existing_id
            )
        ):
            should_replace = True

        if should_replace:
            yearly_records[
                normalized_year
            ] = cleaned_record

    return [
        yearly_records[year]
        for year in sorted(
            yearly_records
        )
    ]


# =============================================================================
# TABLE READING
# =============================================================================

def read_standard_table_records(
    connection: sqlite3.Connection,
    table_name: str,
    ticker: str,
) -> list[dict[str, Any]]:
    """Read rows from a table with a real company_id column."""

    columns = get_table_columns(
        connection,
        table_name,
    )

    normalized_to_physical = {
        normalize_column_name(column):
            column
        for column in columns
    }

    company_column = (
        normalized_to_physical.get(
            "company_id"
        )
    )

    if company_column is None:
        return []

    query = (
        f"SELECT * "
        f"FROM {quote_identifier(table_name)} "
        f"WHERE UPPER(TRIM("
        f"{quote_identifier(company_column)}"
        f")) = ?"
    )

    rows = connection.execute(
        query,
        (ticker,),
    ).fetchall()

    return [
        serialize_row(row)
        for row in rows
    ]


def read_embedded_header_records(
    connection: sqlite3.Connection,
    table_name: str,
    ticker: str,
) -> list[dict[str, Any]]:
    """
    Read tables where the first database row contains the real headers.

    Some imported source tables retain generic physical columns such
    as unnamed:_1 while the first row contains company_id and year.
    """

    query = (
        f"SELECT * "
        f"FROM {quote_identifier(table_name)}"
    )

    rows = connection.execute(
        query
    ).fetchall()

    if not rows:
        return []

    first_row = rows[0]

    physical_columns = list(
        first_row.keys()
    )

    embedded_headers = []

    for physical_column in physical_columns:
        header_value = first_row[
            physical_column
        ]

        normalized_header = (
            normalize_column_name(
                header_value
            )
        )

        if not normalized_header:
            normalized_header = (
                normalize_column_name(
                    physical_column
                )
            )

        embedded_headers.append(
            normalized_header
        )

    if "company_id" not in embedded_headers:
        return []

    company_index = (
        embedded_headers.index(
            "company_id"
        )
    )

    records = []

    for row in rows[1:]:
        values = [
            row[column]
            for column in physical_columns
        ]

        company_value = clean_text(
            values[company_index]
        )

        if (
            company_value is None
            or company_value.upper()
            != ticker
        ):
            continue

        record = {}

        for header, value in zip(
            embedded_headers,
            values,
        ):
            record[header] = (
                serialize_value(value)
            )

        records.append(
            record
        )

    return records


def read_company_history(
    connection: sqlite3.Connection,
    table_name: str,
    ticker: str,
) -> list[dict[str, Any]]:
    """Read company history from either supported table structure."""

    if not table_exists(
        connection,
        table_name,
    ):
        raise HTTPException(
            status_code=503,
            detail=(
                f"Required table "
                f"'{table_name}' is unavailable."
            ),
        )

    standard_records = (
        read_standard_table_records(
            connection,
            table_name,
            ticker,
        )
    )

    if standard_records:
        return standard_records

    return read_embedded_header_records(
        connection,
        table_name,
        ticker,
    )


# =============================================================================
# COMPANY MASTER HELPERS
# =============================================================================

def load_sector_lookup(
    connection: sqlite3.Connection,
) -> dict[str, dict[str, Any]]:
    """Load sector metadata for all companies."""

    if not table_exists(
        connection,
        "sectors",
    ):
        return {}

    rows = connection.execute(
        """
        SELECT *
        FROM sectors
        """
    ).fetchall()

    lookup: dict[
        str,
        dict[str, Any],
    ] = {}

    for row in rows:
        record = serialize_row(
            row
        )

        company_id = clean_text(
            first_available(
                record,
                [
                    "company_id",
                    "ticker",
                    "symbol",
                ],
            )
        )

        if company_id is None:
            continue

        lookup[
            company_id.upper()
        ] = record

    return lookup


def load_latest_ratio_lookup(
    connection: sqlite3.Connection,
) -> dict[str, dict[str, Any]]:
    """Load the latest financial-ratio row for every company."""

    if not table_exists(
        connection,
        "financial_ratios",
    ):
        return {}

    rows = connection.execute(
        """
        SELECT *
        FROM financial_ratios
        """
    ).fetchall()

    latest_lookup: dict[
        str,
        dict[str, Any],
    ] = {}

    latest_year_lookup: dict[
        str,
        str,
    ] = {}

    for row in rows:
        record = serialize_row(
            row
        )

        company_id = clean_text(
            record.get(
                "company_id"
            )
        )

        normalized_year = normalize_year(
            record.get(
                "year"
            )
        )

        if (
            company_id is None
            or normalized_year is None
        ):
            continue

        company_id = (
            company_id.upper()
        )

        current_latest_year = (
            latest_year_lookup.get(
                company_id
            )
        )

        if (
            current_latest_year is None
            or normalized_year
            > current_latest_year
        ):
            latest_year_lookup[
                company_id
            ] = normalized_year

            latest_lookup[
                company_id
            ] = record

    return latest_lookup

def load_all_companies(
    connection: sqlite3.Connection,
) -> list[dict[str, Any]]:
    """Load companies enriched with sector data and latest ROE."""

    if not table_exists(
        connection,
        "companies",
    ):
        raise HTTPException(
            status_code=503,
            detail=(
                "The companies table "
                "is unavailable."
            ),
        )

    rows = connection.execute(
        """
        SELECT *
        FROM companies
        """
    ).fetchall()

    records = [
        serialize_row(row)
        for row in rows
    ]

    sector_lookup = (
        load_sector_lookup(
            connection
        )
    )

    latest_ratio_lookup = (
        load_latest_ratio_lookup(
            connection
        )
    )

    normalized_records = []

    for record in records:
        ticker = clean_text(
            first_available(
                record,
                [
                    "company_id",
                    "id",
                    "ticker",
                    "symbol",
                ],
            )
        )

        if ticker is None:
            continue

        ticker = ticker.upper()

        sector_record = (
            sector_lookup.get(
                ticker,
                {},
            )
        )

        latest_ratios = (
            latest_ratio_lookup.get(
                ticker,
                {},
            )
        )

        company_name = first_available(
            record,
            [
                "company_name",
                "name",
            ],
        )

        broad_sector = first_available(
            sector_record,
            [
                "broad_sector",
                "sector",
            ],
        )

        if broad_sector is None:
            broad_sector = first_available(
                record,
                [
                    "broad_sector",
                    "sector",
                ],
            )

        sub_sector = first_available(
            sector_record,
            [
                "sub_sector",
                "industry",
            ],
        )

        if sub_sector is None:
            sub_sector = first_available(
                record,
                [
                    "sub_sector",
                    "industry",
                ],
            )

        market_cap_category = (
            first_available(
                sector_record,
                [
                    "market_cap_category",
                    "market_cap_classification",
                    "market_cap_segment",
                    "market_cap_type",
                ],
            )
        )

        if market_cap_category is None:
            market_cap_category = (
                first_available(
                    record,
                    [
                        "market_cap_category",
                        "market_cap_classification",
                        "market_cap_segment",
                        "market_cap_type",
                    ],
                )
            )

        # Latest calculated ratio takes precedence over
        # potentially stale company-master ROE.
        roe = first_available(
            latest_ratios,
            [
                "return_on_equity_pct",
                "roe_pct",
            ],
        )

        if roe is None:
            roe = first_available(
                record,
                [
                    "roe_pct",
                    "roe_percentage",
                    "return_on_equity_pct",
                ],
            )

        roce = first_available(
            record,
            [
                "roce_pct",
                "roce_percentage",
                "return_on_capital_employed_pct",
            ],
        )

        normalized_records.append(
            {
                "id":
                    ticker,

                "company_name":
                    clean_text(
                        company_name
                    ),

                "broad_sector":
                    clean_text(
                        broad_sector
                    ),

                "sub_sector":
                    clean_text(
                        sub_sector
                    ),

                "market_cap_category":
                    clean_text(
                        market_cap_category
                    ),

                "roe_pct":
                    clean_number(
                        roe
                    ),

                "roce_pct":
                    clean_number(
                        roce
                    ),

                "_raw":
                    record,
            }
        )

    return normalized_records


def get_company_master_record(
    connection: sqlite3.Connection,
    ticker: str,
) -> dict[str, Any]:
    """Return one normalized company-master record."""

    for company in load_all_companies(
        connection
    ):
        company_id = company.get("id")

        if (
            company_id is not None
            and company_id.upper()
            == ticker
        ):
            return company

    raise HTTPException(
        status_code=404,
        detail=(
            f"Company '{ticker}' "
            "was not found."
        ),
    )


def company_exists(
    connection: sqlite3.Connection,
    ticker: str,
) -> bool:
    """Return whether the ticker exists in the company master."""

    try:
        get_company_master_record(
            connection,
            ticker,
        )

    except HTTPException:
        return False

    return True


# =============================================================================
# SECTOR HELPERS
# =============================================================================

def get_sector_record(
    connection: sqlite3.Connection,
    ticker: str,
) -> dict[str, Any] | None:
    """Return a company's sector record when available."""

    if not table_exists(
        connection,
        "sectors",
    ):
        return None

    records = read_company_history(
        connection,
        "sectors",
        ticker,
    )

    if not records:
        return None

    return records[0]


# =============================================================================
# LATEST RATIOS
# =============================================================================

def get_ratio_history(
    connection: sqlite3.Connection,
    ticker: str,
) -> list[dict[str, Any]]:
    """Return sorted ratio history for one company."""

    records = read_company_history(
        connection,
        HISTORY_TABLES["ratios"],
        ticker,
    )

    return filter_history_by_year(
        records,
        from_year=None,
        to_year=None,
    )


def get_latest_ratios(
    connection: sqlite3.Connection,
    ticker: str,
) -> dict[str, Any] | None:
    """Return the latest available ratio row."""

    history = get_ratio_history(
        connection,
        ticker,
    )

    if not history:
        return None

    return history[-1]


# =============================================================================
# TEARSHEET HELPERS
# =============================================================================

def find_tearsheet(
    ticker: str,
) -> Path | None:
    """Find a pre-generated company tearsheet PDF."""

    candidate_directories = [
        PROJECT_ROOT / "reports" / "tearsheets",
        PROJECT_ROOT / "reports",
        PROJECT_ROOT / "src" / "reports",
    ]

    filename_candidates = [
        f"{ticker}.pdf",
        f"{ticker.lower()}.pdf",
        f"{ticker}_tearsheet.pdf",
        f"{ticker.lower()}_tearsheet.pdf",
        f"{ticker}_report.pdf",
        f"{ticker.lower()}_report.pdf",
    ]

    for directory in candidate_directories:
        if not directory.exists():
            continue

        for filename in filename_candidates:
            candidate = directory / filename

            if candidate.exists():
                return candidate

    # Final case-insensitive search.
    for directory in candidate_directories:
        if not directory.exists():
            continue

        for candidate in directory.glob(
            "*.pdf"
        ):
            stem = candidate.stem.upper()

            if ticker in stem:
                return candidate

    return None


# =============================================================================
# ENDPOINT: COMPANY LIST
# =============================================================================

@router.get(
    "",
    summary="List Nifty 100 companies",
    response_description="Filtered company-master records",
)
def list_companies(
    sector: str | None = Query(
        default=None,
        description=(
            "Optional broad-sector filter."
        ),
    ),
    market_cap_category: str | None = Query(
        default=None,
        description=(
            "Optional market-cap category filter."
        ),
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
        description=(
            "Partial company name or ticker."
        ),
    ),
) -> dict[str, Any]:
    """Return all companies with optional filters."""

    with create_connection() as connection:
        companies = load_all_companies(
            connection
        )

    filtered = companies

    if sector is not None:
        requested_sector = (
            sector.strip().casefold()
        )

        filtered = [
            company
            for company in filtered
            if (
                company.get("broad_sector")
                is not None
                and company[
                    "broad_sector"
                ].casefold()
                == requested_sector
            )
        ]

    if market_cap_category is not None:
        requested_category = (
            market_cap_category
            .strip()
            .casefold()
        )

        filtered = [
            company
            for company in filtered
            if (
                company.get(
                    "market_cap_category"
                )
                is not None
                and company[
                    "market_cap_category"
                ].casefold()
                == requested_category
            )
        ]

    if search is not None:
        search_value = (
            search.strip().casefold()
        )

        filtered = [
            company
            for company in filtered
            if (
                search_value
                in (
                    company.get("id")
                    or ""
                ).casefold()
                or search_value
                in (
                    company.get(
                        "company_name"
                    )
                    or ""
                ).casefold()
            )
        ]

    public_records = [
        {
            key: value
            for key, value in company.items()
            if key != "_raw"
        }
        for company in filtered
    ]

    public_records = sorted(
        public_records,
        key=lambda row: (
            row.get("id")
            or ""
        ),
    )

    return {
        "count":
            len(public_records),

        "filters":
            {
                "sector":
                    sector,

                "market_cap_category":
                    market_cap_category,

                "search":
                    search,
            },

        "companies":
            public_records,
    }


# =============================================================================
# ENDPOINT: P&L HISTORY
# =============================================================================

@router.get(
    "/{ticker}/pl",
    summary="Get company Profit and Loss history",
)
def get_profit_and_loss_history(
    ticker: str,
    from_year: str | None = Query(
        default=None,
        description="Starting year in YYYY-MM format.",
    ),
    to_year: str | None = Query(
        default=None,
        description="Ending year in YYYY-MM format.",
    ),
) -> dict[str, Any]:
    """Return P&L history for one company."""

    ticker = normalize_ticker(
        ticker
    )

    with create_connection() as connection:
        if not company_exists(
            connection,
            ticker,
        ):
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Company '{ticker}' "
                    "was not found."
                ),
            )

        records = read_company_history(
            connection,
            HISTORY_TABLES["pl"],
            ticker,
        )

    records = filter_history_by_year(
        records,
        from_year,
        to_year,
    )

    return {
        "company_id":
            ticker,

        "statement":
            "profit_and_loss",

        "record_count":
            len(records),

        "from_year":
            from_year,

        "to_year":
            to_year,

        "history":
            records,
    }


# =============================================================================
# ENDPOINT: BALANCE-SHEET HISTORY
# =============================================================================

@router.get(
    "/{ticker}/bs",
    summary="Get company balance-sheet history",
)
def get_balance_sheet_history(
    ticker: str,
    from_year: str | None = Query(
        default=None,
        description="Starting year in YYYY-MM format.",
    ),
    to_year: str | None = Query(
        default=None,
        description="Ending year in YYYY-MM format.",
    ),
) -> dict[str, Any]:
    """Return balance-sheet history for one company."""

    ticker = normalize_ticker(
        ticker
    )

    with create_connection() as connection:
        if not company_exists(
            connection,
            ticker,
        ):
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Company '{ticker}' "
                    "was not found."
                ),
            )

        records = read_company_history(
            connection,
            HISTORY_TABLES["bs"],
            ticker,
        )

    records = filter_history_by_year(
        records,
        from_year,
        to_year,
    )

    return {
        "company_id":
            ticker,

        "statement":
            "balance_sheet",

        "record_count":
            len(records),

        "from_year":
            from_year,

        "to_year":
            to_year,

        "history":
            records,
    }


# =============================================================================
# ENDPOINT: CASH-FLOW HISTORY
# =============================================================================

@router.get(
    "/{ticker}/cashflow",
    summary="Get company cash-flow history",
)
def get_cashflow_history(
    ticker: str,
    from_year: str | None = Query(
        default=None,
        description="Starting year in YYYY-MM format.",
    ),
    to_year: str | None = Query(
        default=None,
        description="Ending year in YYYY-MM format.",
    ),
) -> dict[str, Any]:
    """Return cash-flow history for one company."""

    ticker = normalize_ticker(
        ticker
    )

    with create_connection() as connection:
        if not company_exists(
            connection,
            ticker,
        ):
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Company '{ticker}' "
                    "was not found."
                ),
            )

        records = read_company_history(
            connection,
            HISTORY_TABLES["cashflow"],
            ticker,
        )

    records = filter_history_by_year(
        records,
        from_year,
        to_year,
    )

    return {
        "company_id":
            ticker,

        "statement":
            "cash_flow",

        "record_count":
            len(records),

        "from_year":
            from_year,

        "to_year":
            to_year,

        "history":
            records,
    }


# =============================================================================
# ENDPOINT: RATIO HISTORY
# =============================================================================

@router.get(
    "/{ticker}/ratios",
    summary="Get company financial-ratio history",
)
def get_company_ratios(
    ticker: str,
    year: str | None = Query(
        default=None,
        description=(
            "Optional single year in YYYY-MM format."
        ),
    ),
) -> dict[str, Any]:
    """Return all ratio rows or one requested year."""

    ticker = normalize_ticker(
        ticker
    )

    requested_year = validate_year_parameter(
        year,
        "year",
    )

    with create_connection() as connection:
        if not company_exists(
            connection,
            ticker,
        ):
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Company '{ticker}' "
                    "was not found."
                ),
            )

        records = get_ratio_history(
            connection,
            ticker,
        )

    if requested_year is not None:
        records = [
            record
            for record in records
            if record.get(
                "normalized_year"
            )
            == requested_year
        ]

    return {
        "company_id":
            ticker,

        "year":
            requested_year,

        "record_count":
            len(records),

        "ratios":
            records,
    }


# =============================================================================
# ENDPOINT: TEARSHEET DOWNLOAD
# =============================================================================

@router.get(
    "/{ticker}/tearsheet",
    summary="Download a company tearsheet PDF",
    response_class=FileResponse,
)
def download_company_tearsheet(
    ticker: str,
) -> FileResponse:
    """Return a pre-generated company tearsheet PDF."""

    ticker = normalize_ticker(
        ticker
    )

    with create_connection() as connection:
        if not company_exists(
            connection,
            ticker,
        ):
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Company '{ticker}' "
                    "was not found."
                ),
            )

    tearsheet_path = find_tearsheet(
        ticker
    )

    if tearsheet_path is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No pre-generated tearsheet "
                f"was found for '{ticker}'."
            ),
        )

    return FileResponse(
        path=tearsheet_path,
        media_type="application/pdf",
        filename=tearsheet_path.name,
    )


# =============================================================================
# ENDPOINT: FULL COMPANY PROFILE
# =============================================================================

@router.get(
    "/{ticker}",
    summary="Get a complete company profile",
)
def get_company_profile(
    ticker: str,
) -> dict[str, Any]:
    """Return company master data, sector data and latest KPIs."""

    ticker = normalize_ticker(
        ticker
    )

    with create_connection() as connection:
        company = get_company_master_record(
            connection,
            ticker,
        )

        sector_record = get_sector_record(
            connection,
            ticker,
        )

        latest_ratios = get_latest_ratios(
            connection,
            ticker,
        )

    raw_company = company.pop(
        "_raw",
        {},
    )

    return {
        "company_id":
            ticker,

        "company":
            company,

        "company_master_fields":
            raw_company,

        "sector":
            sector_record,

        "latest_kpis":
            latest_ratios,
    }