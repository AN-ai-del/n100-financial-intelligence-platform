"""
Sprint 5 — Day 34
Batch Report Generation

Tasks:
1. Generate company tearsheets for the official 92-company universe.
2. Skip companies with fewer than 3 years of usable P&L data.
3. Log skipped companies to output/skipped_tearsheets.csv.
4. Generate one sector report per broad sector.
5. Validate tearsheet and sector-report output counts.

Outputs:
    reports/tearsheets/<TICKER>_tearsheet.pdf
    reports/sector/<SECTOR>_report.pdf
    output/skipped_tearsheets.csv
    output/day34_report_generation_log.csv
"""

from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path

import numpy as np
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.reports.tearsheet import (
    generate_tearsheet,
    load_sources,
    repair_embedded_header,
)


# ============================================================
# PATH CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = (
    PROJECT_ROOT
    / "db"
    / "nifty100.db"
)

TEARSHEET_DIR = (
    PROJECT_ROOT
    /"src"
    / "reports"
    / "tearsheets"
)

SECTOR_REPORT_DIR = (
    PROJECT_ROOT
    /"src"
    / "reports"
    / "sector"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "output"
)

SKIPPED_OUTPUT = (
    OUTPUT_DIR
    / "skipped_tearsheets.csv"
)

GENERATION_LOG_OUTPUT = (
    OUTPUT_DIR
    / "day34_report_generation_log.csv"
)


# ============================================================
# CONFIGURATION
# ============================================================

MIN_HISTORY_YEARS = 3

EXPECTED_COMPANY_COUNT = 92

EXPECTED_SECTOR_COUNT = None


# ============================================================
# PDF STYLING
# ============================================================

NAVY = colors.HexColor("#0B1F3A")
LIGHT_BLUE = colors.HexColor("#EAF2F8")
LIGHT_GREY = colors.HexColor("#F4F6F7")
MID_GREY = colors.HexColor("#D5D8DC")
DARK_GREY = colors.HexColor("#555555")

styles = getSampleStyleSheet()

SECTOR_TITLE_STYLE = ParagraphStyle(
    "SectorTitle",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=20,
    leading=24,
    textColor=NAVY,
    alignment=TA_LEFT,
)

SECTOR_SUBTITLE_STYLE = ParagraphStyle(
    "SectorSubtitle",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=9,
    leading=12,
    textColor=DARK_GREY,
)

SECTION_STYLE = ParagraphStyle(
    "SectorSection",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=12,
    leading=15,
    textColor=NAVY,
    spaceBefore=8,
    spaceAfter=6,
)

CELL_STYLE = ParagraphStyle(
    "CellStyle",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=7,
    leading=9,
    wordWrap="CJK",
)

CELL_CENTER_STYLE = ParagraphStyle(
    "CellCenter",
    parent=CELL_STYLE,
    alignment=TA_CENTER,
)

HEADER_CELL_STYLE = ParagraphStyle(
    "HeaderCell",
    parent=CELL_STYLE,
    fontName="Helvetica-Bold",
    textColor=colors.white,
    alignment=TA_CENTER,
)


# ============================================================
# GENERIC HELPERS
# ============================================================

def normalize_company_id(value):
    if value is None or pd.isna(value):
        return ""

    return str(value).strip().upper()


def normalize_column(value):
    text = str(value).strip().lower()

    text = re.sub(
        r"[^\w]+",
        "_",
        text,
    )

    return text.strip("_")


def safe_numeric(value):
    if value is None or pd.isna(value):
        return np.nan

    try:
        return float(value)

    except (TypeError, ValueError):
        return np.nan


def clean_text(value):
    if value is None or pd.isna(value):
        return ""

    return (
        str(value)
        .replace("\n", " ")
        .strip()
    )


def safe_filename(value):
    """
    Convert a sector name into a Windows-safe filename.
    """

    text = clean_text(value)

    text = re.sub(
        r'[<>:"/\\|?*]+',
        "_",
        text,
    )

    text = re.sub(
        r"\s+",
        "_",
        text,
    )

    return text.strip("_")


def format_metric(
    value,
    suffix="",
    decimals=2,
):
    value = safe_numeric(value)

    if pd.isna(value):
        return "N/A"

    return (
        f"{value:,.{decimals}f}"
        f"{suffix}"
    )


# ============================================================
# DATABASE HELPERS
# ============================================================

def load_db_table(table_name):
    with sqlite3.connect(DB_PATH) as conn:

        return pd.read_sql_query(
            f'SELECT * FROM "{table_name}"',
            conn,
        )


def load_official_companies():

    companies = load_db_table(
        "companies"
    )

    companies.columns = [
        normalize_column(column)
        for column in companies.columns
    ]

    companies["id"] = (
        companies["id"]
        .apply(normalize_company_id)
    )

    companies["company_name"] = (
        companies["company_name"]
        .astype(str)
        .str.replace(
            "\n",
            " ",
            regex=False,
        )
        .str.strip()
    )

    return (
        companies
        .drop_duplicates(
            subset=["id"]
        )
        .sort_values("id")
        .reset_index(drop=True)
    )


def load_sector_mapping():

    sectors = load_db_table(
        "sectors"
    )

    sectors.columns = [
        normalize_column(column)
        for column in sectors.columns
    ]

    sectors["company_id"] = (
        sectors["company_id"]
        .apply(normalize_company_id)
    )

    sectors["broad_sector"] = (
        sectors["broad_sector"]
        .astype(str)
        .str.replace(
            "\n",
            " ",
            regex=False,
        )
        .str.strip()
    )

    sectors["sub_sector"] = (
        sectors["sub_sector"]
        .astype(str)
        .str.replace(
            "\n",
            " ",
            regex=False,
        )
        .str.strip()
    )

    return sectors


# ============================================================
# HISTORY ELIGIBILITY
# ============================================================

def build_history_coverage(
    sources,
    official_company_ids,
):

    pnl = sources["pnl"].copy()

    if pnl.empty:
        raise ValueError(
            "Profit & Loss table is empty."
        )

    pnl["company_id"] = (
        pnl["company_id"]
        .apply(normalize_company_id)
    )

    pnl = pnl[
        pnl["company_id"].isin(
            official_company_ids
        )
    ].copy()

    coverage = (
        pnl.groupby(
            "company_id"
        )
        .agg(
            history_years=(
                "year",
                "nunique",
            ),
            pnl_records=(
                "year",
                "size",
            ),
        )
        .reset_index()
    )

    return coverage


def determine_eligible_companies(
    companies,
    sources,
):

    official_ids = set(
        companies["id"]
    )

    coverage = build_history_coverage(
        sources,
        official_ids,
    )

    coverage_map = (
        coverage.set_index(
            "company_id"
        )[
            "history_years"
        ]
        .to_dict()
    )

    eligible = []

    skipped = []

    for _, company in companies.iterrows():

        ticker = normalize_company_id(
            company["id"]
        )

        years = int(
            coverage_map.get(
                ticker,
                0,
            )
        )

        if years >= MIN_HISTORY_YEARS:

            eligible.append(
                {
                    "company_id":
                        ticker,
                    "company_name":
                        clean_text(
                            company[
                                "company_name"
                            ]
                        ),
                    "history_years":
                        years,
                }
            )

        else:

            skipped.append(
                {
                    "company_id":
                        ticker,
                    "company_name":
                        clean_text(
                            company[
                                "company_name"
                            ]
                        ),
                    "history_years":
                        years,
                    "reason":
                        (
                            "Fewer than "
                            f"{MIN_HISTORY_YEARS} "
                            "years of P&L data"
                        ),
                }
            )

    return (
        pd.DataFrame(
            eligible
        ),
        pd.DataFrame(
            skipped,
            columns=[
                "company_id",
                "company_name",
                "history_years",
                "reason",
            ],
        ),
    )


# ============================================================
# BATCH TEARSHEET GENERATION
# ============================================================

def generate_company_tearsheets(
    eligible_companies,
    sources,
):

    TEARSHEET_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    generation_rows = []

    total = len(
        eligible_companies
    )

    print(
        "\n"
        + "=" * 100
    )

    print(
        "COMPANY TEARSHEET BATCH"
    )

    print(
        "=" * 100
    )

    for index, row in (
        eligible_companies
        .reset_index(drop=True)
        .iterrows()
    ):

        ticker = row[
            "company_id"
        ]

        start = time.perf_counter()

        print(
            f"[{index + 1:02d}/{total:02d}] "
            f"{ticker:<15}",
            end="",
        )

        try:

            path = generate_tearsheet(
                ticker=ticker,
                sources=sources,
                output_dir=TEARSHEET_DIR,
            )

            runtime = (
                time.perf_counter()
                - start
            )

            exists = path.exists()

            size_bytes = (
                path.stat().st_size
                if exists
                else 0
            )

            status = (
                "PASS"
                if (
                    exists
                    and size_bytes > 5000
                )
                else "FAIL"
            )

            print(
                f"{status:<6} "
                f"{runtime:>6.2f}s "
                f"{size_bytes:>10,} bytes"
            )

            generation_rows.append(
                {
                    "report_type":
                        "company_tearsheet",
                    "company_id":
                        ticker,
                    "sector":
                        "",
                    "output_file":
                        str(path),
                    "size_bytes":
                        size_bytes,
                    "runtime_seconds":
                        round(
                            runtime,
                            3,
                        ),
                    "status":
                        status,
                    "error":
                        "",
                }
            )

        except Exception as exc:

            runtime = (
                time.perf_counter()
                - start
            )

            print(
                f"FAILED {exc}"
            )

            generation_rows.append(
                {
                    "report_type":
                        "company_tearsheet",
                    "company_id":
                        ticker,
                    "sector":
                        "",
                    "output_file":
                        "",
                    "size_bytes":
                        0,
                    "runtime_seconds":
                        round(
                            runtime,
                            3,
                        ),
                    "status":
                        "FAIL",
                    "error":
                        str(exc),
                }
            )

    return pd.DataFrame(
        generation_rows
    )


# ============================================================
# SECTOR DATA PREPARATION
# ============================================================

def build_latest_company_metrics(
    companies,
    sectors,
    sources,
):

    ratios = sources[
        "ratios"
    ].copy()

    market = sources[
        "market_cap"
    ].copy()

    pnl = sources[
        "pnl"
    ].copy()

    # --------------------------------------------------------
    # Normalize ratio data
    # --------------------------------------------------------

    ratios["company_id"] = (
        ratios["company_id"]
        .apply(normalize_company_id)
    )

    ratios["year_numeric"] = (
        ratios["year"]
        .astype(str)
        .str.extract(
            r"(\d{4})"
        )[0]
    )

    ratios[
        "year_numeric"
    ] = pd.to_numeric(
        ratios[
            "year_numeric"
        ],
        errors="coerce",
    )

    ratio_latest = (
        ratios
        .sort_values(
            "year_numeric"
        )
        .drop_duplicates(
            subset=["company_id"],
            keep="last",
        )
    )

    # --------------------------------------------------------
    # Market data
    # --------------------------------------------------------

    market["company_id"] = (
        market["company_id"]
        .apply(normalize_company_id)
    )

    market["year"] = pd.to_numeric(
        market["year"],
        errors="coerce",
    )

    market_latest = (
        market
        .sort_values("year")
        .drop_duplicates(
            subset=["company_id"],
            keep="last",
        )
    )

    # --------------------------------------------------------
    # P&L
    # --------------------------------------------------------

    pnl["company_id"] = (
        pnl["company_id"]
        .apply(normalize_company_id)
    )

    pnl["year_numeric"] = (
        pnl["year"]
        .astype(str)
        .str.extract(
            r"(\d{4})"
        )[0]
    )

    pnl[
        "year_numeric"
    ] = pd.to_numeric(
        pnl[
            "year_numeric"
        ],
        errors="coerce",
    )

    for column in [
        "sales",
        "net_profit",
    ]:

        pnl[column] = pd.to_numeric(
            pnl[column],
            errors="coerce",
        )

    pnl_latest = (
        pnl
        .sort_values(
            "year_numeric"
        )
        .drop_duplicates(
            subset=["company_id"],
            keep="last",
        )
    )

    # --------------------------------------------------------
    # Base company table
    # --------------------------------------------------------

    result = companies[
        [
            "id",
            "company_name",
            "roce_percentage",
        ]
    ].rename(
        columns={
            "id":
                "company_id",
        }
    )

    result = result.merge(
        sectors[
            [
                "company_id",
                "broad_sector",
                "sub_sector",
            ]
        ],
        on="company_id",
        how="left",
    )

    ratio_columns = [
        "company_id",
        "return_on_equity_pct",
        "operating_profit_margin_pct",
        "debt_to_equity",
        "free_cash_flow_cr",
    ]

    ratio_columns = [
        column
        for column in ratio_columns
        if column in ratio_latest.columns
    ]

    result = result.merge(
        ratio_latest[
            ratio_columns
        ],
        on="company_id",
        how="left",
    )

    market_columns = [
        "company_id",
        "pe_ratio",
        "market_cap_crore",
    ]

    market_columns = [
        column
        for column in market_columns
        if column in market_latest.columns
    ]

    result = result.merge(
        market_latest[
            market_columns
        ],
        on="company_id",
        how="left",
    )

    pnl_columns = [
        "company_id",
        "sales",
        "net_profit",
    ]

    result = result.merge(
        pnl_latest[
            pnl_columns
        ],
        on="company_id",
        how="left",
    )

    return result


# ============================================================
# SECTOR PDF COMPONENTS
# ============================================================

def build_sector_median_table(
    sector_data,
):

    median_metrics = [
        (
            "ROE",
            "return_on_equity_pct",
            "%",
        ),
        (
            "ROCE",
            "roce_percentage",
            "%",
        ),
        (
            "OPM",
            "operating_profit_margin_pct",
            "%",
        ),
        (
            "Debt / Equity",
            "debt_to_equity",
            "",
        ),
        (
            "Free Cash Flow",
            "free_cash_flow_cr",
            " Cr",
        ),
        (
            "P/E",
            "pe_ratio",
            "",
        ),
    ]

    headers = []

    values = []

    for label, column, suffix in (
        median_metrics
    ):

        headers.append(
            Paragraph(
                label,
                HEADER_CELL_STYLE,
            )
        )

        if column in sector_data.columns:

            median = pd.to_numeric(
                sector_data[
                    column
                ],
                errors="coerce",
            ).median()

        else:
            median = np.nan

        values.append(
            Paragraph(
                format_metric(
                    median,
                    suffix=suffix,
                ),
                CELL_CENTER_STYLE,
            )
        )

    table = Table(
        [
            headers,
            values,
        ],
        colWidths=[
            30 * mm
        ] * len(headers),
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    NAVY,
                ),
                (
                    "BACKGROUND",
                    (0, 1),
                    (-1, 1),
                    LIGHT_BLUE,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    MID_GREY,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    return table


def build_sector_company_table(
    sector_data,
):

    columns = [
        (
            "Ticker",
            "company_id",
            "",
        ),
        (
            "Company",
            "company_name",
            "",
        ),
        (
            "ROE",
            "return_on_equity_pct",
            "%",
        ),
        (
            "ROCE",
            "roce_percentage",
            "%",
        ),
        (
            "OPM",
            "operating_profit_margin_pct",
            "%",
        ),
        (
            "D/E",
            "debt_to_equity",
            "",
        ),
        (
            "FCF Cr",
            "free_cash_flow_cr",
            "",
        ),
        (
            "P/E",
            "pe_ratio",
            "",
        ),
        (
            "Net Profit Cr",
            "net_profit",
            "",
        ),
        (
            "Mkt Cap Cr",
            "market_cap_crore",
            "",
        ),
    ]

    table_data = [
        [
            Paragraph(
                label,
                HEADER_CELL_STYLE,
            )
            for label, _, _ in columns
        ]
    ]

    for _, row in (
        sector_data
        .sort_values(
            "company_id"
        )
        .iterrows()
    ):

        output_row = []

        for label, column, suffix in columns:

            value = (
                row.get(
                    column,
                    np.nan,
                )
            )

            if column in {
                "company_id",
                "company_name",
            }:

                text = clean_text(
                    value
                )

            else:

                text = format_metric(
                    value,
                    suffix=suffix,
                )

            style = (
                CELL_STYLE
                if column
                == "company_name"
                else CELL_CENTER_STYLE
            )

            output_row.append(
                Paragraph(
                    text,
                    style,
                )
            )

        table_data.append(
            output_row
        )

    col_widths = [
        18 * mm,
        42 * mm,
        17 * mm,
        17 * mm,
        17 * mm,
        14 * mm,
        20 * mm,
        14 * mm,
        22 * mm,
        23 * mm,
    ]

    table = Table(
        table_data,
        colWidths=col_widths,
        repeatRows=1,
    )

    commands = [
        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            NAVY,
        ),
        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.3,
            MID_GREY,
        ),
        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "MIDDLE",
        ),
        (
            "LEFTPADDING",
            (0, 0),
            (-1, -1),
            3,
        ),
        (
            "RIGHTPADDING",
            (0, 0),
            (-1, -1),
            3,
        ),
        (
            "TOPPADDING",
            (0, 0),
            (-1, -1),
            4,
        ),
        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, -1),
            4,
        ),
    ]

    for row_index in range(
        1,
        len(table_data),
    ):

        if row_index % 2 == 0:

            commands.append(
                (
                    "BACKGROUND",
                    (0, row_index),
                    (-1, row_index),
                    LIGHT_GREY,
                )
            )

    table.setStyle(
        TableStyle(
            commands
        )
    )

    return table


# ============================================================
# SECTOR PDF GENERATION
# ============================================================

def generate_sector_report(
    sector,
    company_metrics,
):

    SECTOR_REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    sector_data = company_metrics[
        company_metrics[
            "broad_sector"
        ]
        == sector
    ].copy()

    if sector_data.empty:
        raise ValueError(
            f"No companies found for sector: {sector}"
        )

    output_path = (
        SECTOR_REPORT_DIR
        / (
            safe_filename(
                sector
            )
            + "_report.pdf"
        )
    )

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=(
            f"{sector} Sector Report"
        ),
        author=(
            "Nifty 100 Financial "
            "Intelligence Platform"
        ),
    )

    story = []

    story.append(
        Paragraph(
            f"{clean_text(sector)} Sector Report",
            SECTOR_TITLE_STYLE,
        )
    )

    story.append(
        Paragraph(
            (
                "Nifty 100 Financial Intelligence Platform"
                f" | Companies: {len(sector_data)}"
            ),
            SECTOR_SUBTITLE_STYLE,
        )
    )

    story.append(
        Spacer(
            1,
            8,
        )
    )

    story.append(
        Paragraph(
            "Sector Median KPIs",
            SECTION_STYLE,
        )
    )

    story.append(
        build_sector_median_table(
            sector_data
        )
    )

    story.append(
        Spacer(
            1,
            10,
        )
    )

    story.append(
        Paragraph(
            "Company Comparison",
            SECTION_STYLE,
        )
    )

    story.append(
        build_sector_company_table(
            sector_data
        )
    )

    doc.build(
        story
    )

    return output_path


def generate_all_sector_reports(
    company_metrics,
):

    sectors = sorted(
        company_metrics[
            "broad_sector"
        ]
        .dropna()
        .astype(str)
        .str.strip()
        .loc[
            lambda x:
                x.ne("")
                & x.ne("nan")
        ]
        .unique()
        .tolist()
    )

    logs = []

    print(
        "\n"
        + "=" * 100
    )

    print(
        "SECTOR REPORT BATCH"
    )

    print(
        "=" * 100
    )

    for index, sector in enumerate(
        sectors,
        start=1,
    ):

        start = time.perf_counter()

        print(
            f"[{index:02d}/{len(sectors):02d}] "
            f"{sector:<35}",
            end="",
        )

        try:

            path = generate_sector_report(
                sector,
                company_metrics,
            )

            runtime = (
                time.perf_counter()
                - start
            )

            size_bytes = (
                path.stat().st_size
                if path.exists()
                else 0
            )

            status = (
                "PASS"
                if (
                    path.exists()
                    and size_bytes > 3000
                )
                else "FAIL"
            )

            print(
                f"{status:<6} "
                f"{size_bytes:>9,} bytes"
            )

            logs.append(
                {
                    "report_type":
                        "sector_report",
                    "company_id":
                        "",
                    "sector":
                        sector,
                    "output_file":
                        str(path),
                    "size_bytes":
                        size_bytes,
                    "runtime_seconds":
                        round(
                            runtime,
                            3,
                        ),
                    "status":
                        status,
                    "error":
                        "",
                }
            )

        except Exception as exc:

            runtime = (
                time.perf_counter()
                - start
            )

            print(
                f"FAILED {exc}"
            )

            logs.append(
                {
                    "report_type":
                        "sector_report",
                    "company_id":
                        "",
                    "sector":
                        sector,
                    "output_file":
                        "",
                    "size_bytes":
                        0,
                    "runtime_seconds":
                        round(
                            runtime,
                            3,
                        ),
                    "status":
                        "FAIL",
                    "error":
                        str(exc),
                }
            )

    return pd.DataFrame(
        logs
    )


# ============================================================
# FINAL VALIDATION
# ============================================================

def validate_day34(
    companies,
    eligible,
    skipped,
    company_log,
    sector_log,
):

    print(
        "\n"
        + "=" * 100
    )

    print(
        "SPRINT 5 — DAY 34 VALIDATION"
    )

    print(
        "=" * 100
    )

    expected_tearsheets = (
        len(companies)
        - len(skipped)
    )

    generated_tearsheets = int(
        (
            company_log[
                "status"
            ]
            == "PASS"
        ).sum()
    )

    failed_tearsheets = int(
        (
            company_log[
                "status"
            ]
            == "FAIL"
        ).sum()
    )

    generated_sector_reports = int(
        (
            sector_log[
                "status"
            ]
            == "PASS"
        ).sum()
    )

    failed_sector_reports = int(
        (
            sector_log[
                "status"
            ]
            == "FAIL"
        ).sum()
    )
    
    expected_sector_reports = int(
         sector_log["sector"]
        .replace("", np.nan)
        .dropna()
        .nunique()
    )

    print(
        f"\nOfficial companies      : "
        f"{len(companies)}"
    )

    print(
        f"Eligible companies      : "
        f"{len(eligible)}"
    )

    print(
        f"Skipped companies       : "
        f"{len(skipped)}"
    )

    print(
        f"Expected tearsheets     : "
        f"{expected_tearsheets}"
    )

    print(
        f"Generated tearsheets    : "
        f"{generated_tearsheets}"
    )

    print(
        f"Failed tearsheets       : "
        f"{failed_tearsheets}"
    )

    print(
        f"\nExpected sector reports : "
        f"{expected_sector_reports}"
    )

    print(
        f"Sector reports generated: "
        f"{generated_sector_reports}"
    )

    print(
        f"Sector reports failed   : "
        f"{failed_sector_reports}"
    )

    if not skipped.empty:

        print(
            "\nSKIPPED COMPANIES"
        )

        print(
            "-" * 100
        )

        print(
            skipped.to_string(
                index=False
            )
        )

    failed_company_rows = (
        company_log[
            company_log[
                "status"
            ]
            == "FAIL"
        ]
    )

    if not failed_company_rows.empty:

        print(
            "\nFAILED TEARSHEETS"
        )

        print(
            "-" * 100
        )

        print(
            failed_company_rows[
                [
                    "company_id",
                    "error",
                ]
            ].to_string(
                index=False
            )
        )

    failed_sector_rows = (
        sector_log[
            sector_log[
                "status"
            ]
            == "FAIL"
        ]
    )

    if not failed_sector_rows.empty:

        print(
            "\nFAILED SECTOR REPORTS"
        )

        print(
            "-" * 100
        )

        print(
            failed_sector_rows[
                [
                    "sector",
                    "error",
                ]
            ].to_string(
                index=False
            )
        )

    passed = (
        generated_tearsheets
        == expected_tearsheets
        and failed_tearsheets == 0
        and generated_sector_reports
        == expected_sector_reports
        and failed_sector_reports == 0
    )

    print(
        "\n"
        + "-" * 100
    )

    if passed:

        print(
            "DAY 34 VALIDATION PASSED"
        )

    else:

        print(
            "DAY 34 VALIDATION REQUIRES REVIEW"
        )

    print(
        "-" * 100
    )

    return passed


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=" * 100
    )

    print(
        "SPRINT 5 — DAY 34 "
        "BATCH REPORT GENERATION"
    )

    print(
        "=" * 100
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    TEARSHEET_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    SECTOR_REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "\nLoading project data..."
    )

    sources = load_sources()

    companies = load_official_companies()

    sectors = load_sector_mapping()

    print(
        f"Official companies loaded: "
        f"{len(companies)}"
    )

    print(
        f"Sector mappings loaded   : "
        f"{len(sectors)}"
    )

    # --------------------------------------------------------
    # Eligibility
    # --------------------------------------------------------

    (
        eligible,
        skipped,
    ) = determine_eligible_companies(
        companies,
        sources,
    )

    skipped.to_csv(
        SKIPPED_OUTPUT,
        index=False,
    )

    print(
        f"\nEligible for tearsheets : "
        f"{len(eligible)}"
    )

    print(
        f"Skipped                 : "
        f"{len(skipped)}"
    )

    # --------------------------------------------------------
    # Company reports
    # --------------------------------------------------------

    company_log = (
        generate_company_tearsheets(
            eligible,
            sources,
        )
    )

    # --------------------------------------------------------
    # Sector data / reports
    # --------------------------------------------------------

    company_metrics = (
        build_latest_company_metrics(
            companies,
            sectors,
            sources,
        )
    )

    sector_log = (
        generate_all_sector_reports(
            company_metrics
        )
    )

    # --------------------------------------------------------
    # Combined generation log
    # --------------------------------------------------------

    generation_log = pd.concat(
        [
            company_log,
            sector_log,
        ],
        ignore_index=True,
    )

    generation_log.to_csv(
        GENERATION_LOG_OUTPUT,
        index=False,
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    passed = validate_day34(
        companies,
        eligible,
        skipped,
        company_log,
        sector_log,
    )

    print(
        "\nOUTPUTS"
    )

    print(
        "-" * 100
    )

    print(
        f"Tearsheets:"
        f"\n{TEARSHEET_DIR}"
    )

    print(
        f"\nSector reports:"
        f"\n{SECTOR_REPORT_DIR}"
    )

    print(
        f"\nSkipped-company log:"
        f"\n{SKIPPED_OUTPUT}"
    )

    print(
        f"\nGeneration log:"
        f"\n{GENERATION_LOG_OUTPUT}"
    )

    print(
        "\n"
        + "=" * 100
    )

    if passed:

        print(
            "SPRINT 5 — DAY 34 COMPLETE"
        )

    else:

        print(
            "SPRINT 5 — DAY 34 "
            "COMPLETED WITH REVIEW ITEMS"
        )

    print(
        "=" * 100
    )

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()