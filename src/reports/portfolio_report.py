"""
Sprint 5 — Day 35
Portfolio Summary PDF

Generates:
    src/reports/portfolio/portfolio_summary.pdf

One page per official company, ordered alphabetically by ticker.

Each page contains:
- Company name
- Ticker
- Sector / sub-sector
- Six latest KPIs
- Trend direction for each KPI
- Cash-flow health
- Capital-allocation classification
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = (
    PROJECT_ROOT
    / "db"
    / "nifty100.db"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "src"
    / "reports"
    / "portfolio"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "portfolio_summary.pdf"
)

CASHFLOW_INTELLIGENCE_PATH = (
    PROJECT_ROOT
    / "output"
    / "cashflow_intelligence.csv"
)


# ============================================================
# PDF CONSTANTS
# ============================================================

PAGE_WIDTH, PAGE_HEIGHT = A4

LEFT_MARGIN = 14 * mm
RIGHT_MARGIN = 14 * mm
TOP_MARGIN = 14 * mm
BOTTOM_MARGIN = 14 * mm

CONTENT_WIDTH = (
    PAGE_WIDTH
    - LEFT_MARGIN
    - RIGHT_MARGIN
)


# ============================================================
# COLOURS
# ============================================================

NAVY = colors.HexColor("#0B1F3A")
BLUE = colors.HexColor("#1F4E78")
LIGHT_BLUE = colors.HexColor("#EAF2F8")

GREEN = colors.HexColor("#198754")
LIGHT_GREEN = colors.HexColor("#E8F5E9")

RED = colors.HexColor("#C0392B")
LIGHT_RED = colors.HexColor("#FDEDEC")

AMBER = colors.HexColor("#B9770E")
LIGHT_AMBER = colors.HexColor("#FEF5E7")

GREY = colors.HexColor("#666666")
LIGHT_GREY = colors.HexColor("#F4F6F7")
BORDER_GREY = colors.HexColor("#D5D8DC")

WHITE = colors.white
BLACK = colors.black


# ============================================================
# STYLES
# ============================================================

styles = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle(
    "PortfolioTitle",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=18,
    leading=21,
    textColor=WHITE,
    alignment=TA_LEFT,
)

SUBTITLE_STYLE = ParagraphStyle(
    "PortfolioSubtitle",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=9,
    leading=12,
    textColor=colors.HexColor("#D6EAF8"),
)

SECTION_STYLE = ParagraphStyle(
    "PortfolioSection",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=14,
    textColor=NAVY,
    spaceBefore=5,
    spaceAfter=5,
)

BODY_STYLE = ParagraphStyle(
    "PortfolioBody",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=8,
    leading=11,
    textColor=BLACK,
    wordWrap="CJK",
)

SMALL_STYLE = ParagraphStyle(
    "PortfolioSmall",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=7,
    leading=9,
    textColor=GREY,
    wordWrap="CJK",
)

KPI_LABEL_STYLE = ParagraphStyle(
    "PortfolioKPILabel",
    parent=SMALL_STYLE,
    fontName="Helvetica-Bold",
    alignment=TA_CENTER,
)

KPI_VALUE_STYLE = ParagraphStyle(
    "PortfolioKPIValue",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=12,
    leading=15,
    textColor=NAVY,
    alignment=TA_CENTER,
)

TREND_STYLE = ParagraphStyle(
    "PortfolioTrend",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=13,
    alignment=TA_CENTER,
)


# ============================================================
# GENERIC HELPERS
# ============================================================

def clean_text(value):
    if value is None or pd.isna(value):
        return ""

    return (
        str(value)
        .replace("\n", " ")
        .strip()
    )


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


def extract_year(value):
    if value is None or pd.isna(value):
        return np.nan

    text = str(value).strip()

    four_digit = re.search(
        r"(19|20)\d{2}",
        text,
    )

    if four_digit:
        return int(
            four_digit.group()
        )

    two_digit = re.search(
        r"(?<!\d)(\d{2})(?!\d)",
        text,
    )

    if two_digit:

        year = int(
            two_digit.group(1)
        )

        if year <= 50:
            return 2000 + year

        return 1900 + year

    return np.nan


def format_pct(value):
    value = safe_numeric(value)

    if pd.isna(value):
        return "N/A"

    return f"{value:,.2f}%"


def format_number(value):
    value = safe_numeric(value)

    if pd.isna(value):
        return "N/A"

    return f"{value:,.2f}"


def format_crore(value):
    value = safe_numeric(value)

    if pd.isna(value):
        return "N/A"

    return f"Rs. {value:,.0f} Cr"


# ============================================================
# DATABASE HELPERS
# ============================================================

def load_table(
    connection,
    table_name,
):
    return pd.read_sql_query(
        f'SELECT * FROM "{table_name}"',
        connection,
    )


def repair_embedded_header(df):
    if df.empty:
        return df.copy()

    first_row = df.iloc[0]

    first_values = [
        normalize_column(value)
        if pd.notna(value)
        else ""
        for value in first_row
    ]

    if (
        "company_id" in first_values
        and "year" in first_values
    ):

        repaired = df.iloc[1:].copy()

        repaired.columns = [
            normalize_column(value)
            if pd.notna(value)
            else f"column_{i}"
            for i, value in enumerate(
                first_row
            )
        ]

        return repaired.reset_index(
            drop=True
        )

    repaired = df.copy()

    repaired.columns = [
        normalize_column(column)
        for column in repaired.columns
    ]

    return repaired


def load_project_data():

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    with sqlite3.connect(
        DB_PATH
    ) as connection:

        companies = load_table(
            connection,
            "companies",
        )

        ratios = load_table(
            connection,
            "financial_ratios",
        )

        market = load_table(
            connection,
            "market_cap",
        )

        sectors = load_table(
            connection,
            "sectors",
        )

        pnl = load_table(
            connection,
            "profitandloss",
        )

    pnl = repair_embedded_header(
        pnl
    )

    companies.columns = [
        normalize_column(column)
        for column in companies.columns
    ]

    ratios.columns = [
        normalize_column(column)
        for column in ratios.columns
    ]

    market.columns = [
        normalize_column(column)
        for column in market.columns
    ]

    sectors.columns = [
        normalize_column(column)
        for column in sectors.columns
    ]

    return (
        companies,
        ratios,
        market,
        sectors,
        pnl,
    )


# ============================================================
# PREPARE DATA
# ============================================================

def prepare_companies(df):

    df = df.copy()

    df["company_id"] = (
        df["id"]
        .apply(normalize_company_id)
    )

    df["company_name"] = (
        df["company_name"]
        .astype(str)
        .str.replace(
            "\n",
            " ",
            regex=False,
        )
        .str.strip()
    )

    for column in [
        "roce_percentage",
        "roe_percentage",
    ]:

        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    return (
        df
        .drop_duplicates(
            subset=["company_id"]
        )
        .sort_values(
            "company_id"
        )
        .reset_index(drop=True)
    )


def prepare_ratios(df):

    df = df.copy()

    df["company_id"] = (
        df["company_id"]
        .apply(normalize_company_id)
    )

    df["year_numeric"] = (
        df["year"]
        .apply(extract_year)
    )

    numeric_columns = [
        "return_on_equity_pct",
        "operating_profit_margin_pct",
        "debt_to_equity",
        "free_cash_flow_cr",
        "earnings_per_share",
    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    df = df[
        df["year_numeric"].notna()
    ].copy()

    df["year_numeric"] = (
        df["year_numeric"]
        .astype(int)
    )

    df["_complete"] = (
        df[
            [
                column
                for column in numeric_columns
                if column in df.columns
            ]
        ]
        .notna()
        .sum(axis=1)
    )

    df = (
        df
        .sort_values(
            [
                "company_id",
                "year_numeric",
                "_complete",
            ],
            ascending=[
                True,
                True,
                False,
            ],
        )
        .drop_duplicates(
            subset=[
                "company_id",
                "year_numeric",
            ],
            keep="first",
        )
        .drop(
            columns=["_complete"]
        )
        .reset_index(drop=True)
    )

    return df


def prepare_market(df):

    df = df.copy()

    df["company_id"] = (
        df["company_id"]
        .apply(normalize_company_id)
    )

    df["year_numeric"] = pd.to_numeric(
        df["year"],
        errors="coerce",
    )

    for column in [
        "pe_ratio",
        "pb_ratio",
        "market_cap_crore",
    ]:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    return df.sort_values(
        [
            "company_id",
            "year_numeric",
        ]
    )


def prepare_sectors(df):

    df = df.copy()

    df["company_id"] = (
        df["company_id"]
        .apply(normalize_company_id)
    )

    return (
        df[
            [
                "company_id",
                "broad_sector",
                "sub_sector",
            ]
        ]
        .drop_duplicates(
            subset=["company_id"]
        )
    )


def prepare_pnl(df):

    df = df.copy()

    df["company_id"] = (
        df["company_id"]
        .apply(normalize_company_id)
    )

    df["year_numeric"] = (
        df["year"]
        .apply(extract_year)
    )

    for column in [
        "sales",
        "net_profit",
        "eps",
    ]:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    df = df[
        df["year_numeric"].notna()
    ].copy()

    df["year_numeric"] = (
        df["year_numeric"]
        .astype(int)
    )

    return (
        df
        .sort_values(
            [
                "company_id",
                "year_numeric",
            ]
        )
        .drop_duplicates(
            subset=[
                "company_id",
                "year_numeric",
            ],
            keep="last",
        )
    )


# ============================================================
# TREND ENGINE
# ============================================================

def calculate_trend(
    current_value,
    previous_value,
    higher_is_better=True,
):
    """
    Trend rules:

    RIGHT:
        Change is within +/-2%

    UP:
        Metric improved by >2%

    DOWN:
        Metric worsened by >2%

    Improvement direction depends on KPI.
    """

    current = safe_numeric(
        current_value
    )

    previous = safe_numeric(
        previous_value
    )

    if (
        pd.isna(current)
        or pd.isna(previous)
    ):
        return {
            "symbol": "N/A",
            "label": "No comparison",
            "status": "na",
            "change_pct": np.nan,
        }

    if previous == 0:

        absolute_change = (
            current
            - previous
        )

        if abs(absolute_change) < 0.0001:

            return {
                "symbol": "RIGHT",
                "label": "Flat",
                "status": "flat",
                "change_pct": 0.0,
            }

        improved = (
            current > previous
            if higher_is_better
            else current < previous
        )

        return {
            "symbol":
                "UP"
                if improved
                else "DOWN",

            "label":
                "Improved"
                if improved
                else "Declined",

            "status":
                "up"
                if improved
                else "down",

            "change_pct":
                np.nan,
        }

    change_pct = (
        (
            current
            - previous
        )
        / abs(previous)
        * 100
    )

    if abs(change_pct) <= 2:

        return {
            "symbol": "RIGHT",
            "label": "Flat",
            "status": "flat",
            "change_pct": change_pct,
        }

    raw_direction_up = (
        change_pct > 0
    )

    if higher_is_better:

        improved = (
            raw_direction_up
        )

    else:

        improved = (
            not raw_direction_up
        )

    return {
        "symbol":
            "UP"
            if improved
            else "DOWN",

        "label":
            "Improved"
            if improved
            else "Declined",

        "status":
            "up"
            if improved
            else "down",

        "change_pct":
            change_pct,
    }


def latest_and_previous(
    df,
    column,
):

    if (
        df.empty
        or column not in df.columns
    ):

        return (
            np.nan,
            np.nan,
        )

    values = (
        df[
            [
                "year_numeric",
                column,
            ]
        ]
        .dropna(
            subset=[column]
        )
        .sort_values(
            "year_numeric"
        )
    )

    if values.empty:

        return (
            np.nan,
            np.nan,
        )

    latest = values.iloc[-1][
        column
    ]

    previous = (
        values.iloc[-2][column]
        if len(values) >= 2
        else np.nan
    )

    return (
        latest,
        previous,
    )


# ============================================================
# COMPANY SNAPSHOT
# ============================================================

def build_company_snapshot(
    company,
    ratios,
    market,
    sectors,
    pnl,
    cashflow_intelligence,
):

    ticker = company[
        "company_id"
    ]

    ratio_history = ratios[
        ratios[
            "company_id"
        ]
        == ticker
    ].copy()

    market_history = market[
        market[
            "company_id"
        ]
        == ticker
    ].copy()

    pnl_history = pnl[
        pnl[
            "company_id"
        ]
        == ticker
    ].copy()

    sector_row = sectors[
        sectors[
            "company_id"
        ]
        == ticker
    ]

    if sector_row.empty:

        broad_sector = "N/A"
        sub_sector = "N/A"

    else:

        broad_sector = clean_text(
            sector_row.iloc[0][
                "broad_sector"
            ]
        )

        sub_sector = clean_text(
            sector_row.iloc[0][
                "sub_sector"
            ]
        )

    # --------------------------------------------------------
    # Six KPIs
    # --------------------------------------------------------

    (
        roe_current,
        roe_previous,
    ) = latest_and_previous(
        ratio_history,
        "return_on_equity_pct",
    )

    (
        opm_current,
        opm_previous,
    ) = latest_and_previous(
        ratio_history,
        "operating_profit_margin_pct",
    )

    (
        de_current,
        de_previous,
    ) = latest_and_previous(
        ratio_history,
        "debt_to_equity",
    )

    (
        fcf_current,
        fcf_previous,
    ) = latest_and_previous(
        ratio_history,
        "free_cash_flow_cr",
    )

    (
        eps_current,
        eps_previous,
    ) = latest_and_previous(
        pnl_history,
        "eps",
    )

    (
        pe_current,
        pe_previous,
    ) = latest_and_previous(
        market_history,
        "pe_ratio",
    )

    latest_roce = safe_numeric(
        company.get(
            "roce_percentage"
        )
    )

    # --------------------------------------------------------
    # Latest cash-flow intelligence
    # --------------------------------------------------------

    allocation = "NOT_AVAILABLE"
    cashflow_health = "NOT_AVAILABLE"

    if (
        not cashflow_intelligence.empty
        and "company_id"
        in cashflow_intelligence.columns
    ):

        cf_history = (
            cashflow_intelligence[
                cashflow_intelligence[
                    "company_id"
                ]
                .astype(str)
                .str.upper()
                == ticker
            ]
            .copy()
        )

        if not cf_history.empty:

            if (
                "year_numeric"
                in cf_history.columns
            ):

                cf_history = (
                    cf_history
                    .sort_values(
                        "year_numeric"
                    )
                )

            latest_cf = (
                cf_history.iloc[-1]
            )

            allocation = clean_text(
                latest_cf.get(
                    "capital_allocation_pattern"
                )
            ) or "NOT_AVAILABLE"

            cashflow_health = clean_text(
                latest_cf.get(
                    "cashflow_health_label"
                )
            ) or "NOT_AVAILABLE"

    kpis = [
        {
            "label": "ROE",
            "value": roe_current,
            "display":
                format_pct(
                    roe_current
                ),
            "trend":
                calculate_trend(
                    roe_current,
                    roe_previous,
                    higher_is_better=True,
                ),
        },

        {
            "label": "ROCE",
            "value": latest_roce,
            "display":
                format_pct(
                    latest_roce
                ),
            "trend": {
                "symbol": "N/A",
                "label": "Current only",
                "status": "na",
                "change_pct": np.nan,
            },
        },

        {
            "label": "Operating Margin",
            "value": opm_current,
            "display":
                format_pct(
                    opm_current
                ),
            "trend":
                calculate_trend(
                    opm_current,
                    opm_previous,
                    higher_is_better=True,
                ),
        },

        {
            "label": "Debt / Equity",
            "value": de_current,
            "display":
                format_number(
                    de_current
                ),
            "trend":
                calculate_trend(
                    de_current,
                    de_previous,
                    higher_is_better=False,
                ),
        },

        {
            "label": "Free Cash Flow",
            "value": fcf_current,
            "display":
                format_crore(
                    fcf_current
                ),
            "trend":
                calculate_trend(
                    fcf_current,
                    fcf_previous,
                    higher_is_better=True,
                ),
        },

        {
            "label": "P/E Ratio",
            "value": pe_current,
            "display":
                format_number(
                    pe_current
                ),
            "trend":
                calculate_trend(
                    pe_current,
                    pe_previous,
                    higher_is_better=False,
                ),
        },
    ]

    return {
        "company_id":
            ticker,

        "company_name":
            clean_text(
                company[
                    "company_name"
                ]
            ),

        "broad_sector":
            broad_sector,

        "sub_sector":
            sub_sector,

        "kpis":
            kpis,

        "capital_allocation":
            allocation,

        "cashflow_health":
            cashflow_health,
    }


# ============================================================
# REPORT COMPONENTS
# ============================================================

def build_header(snapshot):

    subtitle = (
        f"{snapshot['company_id']} | "
        f"{snapshot['broad_sector']} | "
        f"{snapshot['sub_sector']}"
    )

    table = Table(
        [
            [
                Paragraph(
                    snapshot[
                        "company_name"
                    ],
                    TITLE_STYLE,
                )
            ],
            [
                Paragraph(
                    subtitle,
                    SUBTITLE_STYLE,
                )
            ],
        ],
        colWidths=[
            CONTENT_WIDTH
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    NAVY,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, 0),
                    9,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 1),
                    (-1, 1),
                    8,
                ),
            ]
        )
    )

    return table


def trend_display(trend):

    status = trend[
        "status"
    ]

    if status == "up":

        symbol = "▲"

        color = GREEN

    elif status == "down":

        symbol = "▼"

        color = RED

    elif status == "flat":

        symbol = "→"

        color = AMBER

    else:

        symbol = "—"

        color = GREY

    return Paragraph(
        (
            f'<font color="{color.hexval()}">'
            f"<b>{symbol}</b>"
            f"</font><br/>"
            f"{trend['label']}"
        ),
        TREND_STYLE,
    )


def build_kpi_tile(
    kpi,
):

    table = Table(
        [
            [
                Paragraph(
                    kpi[
                        "label"
                    ],
                    KPI_LABEL_STYLE,
                )
            ],
            [
                Paragraph(
                    kpi[
                        "display"
                    ],
                    KPI_VALUE_STYLE,
                )
            ],
            [
                trend_display(
                    kpi[
                        "trend"
                    ]
                )
            ],
        ],
        colWidths=[
            CONTENT_WIDTH / 3
            - 4
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    LIGHT_GREY,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    BORDER_GREY,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
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


def build_kpi_grid(
    snapshot,
):

    kpis = snapshot[
        "kpis"
    ]

    tiles = [
        build_kpi_tile(
            kpi
        )
        for kpi in kpis
    ]

    table = Table(
        [
            tiles[:3],
            tiles[3:],
        ],
        colWidths=[
            CONTENT_WIDTH / 3
        ] * 3,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
            ]
        )
    )

    return table


def build_status_table(
    snapshot,
):

    table = Table(
        [
            [
                Paragraph(
                    "<b>Capital Allocation</b>",
                    BODY_STYLE,
                ),
                Paragraph(
                    snapshot[
                        "capital_allocation"
                    ],
                    BODY_STYLE,
                ),
            ],
            [
                Paragraph(
                    "<b>Cash Flow Health</b>",
                    BODY_STYLE,
                ),
                Paragraph(
                    snapshot[
                        "cashflow_health"
                    ],
                    BODY_STYLE,
                ),
            ],
        ],
        colWidths=[
            CONTENT_WIDTH * 0.35,
            CONTENT_WIDTH * 0.65,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    LIGHT_BLUE,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    BORDER_GREY,
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
                    7,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    return table


def build_trend_legend():

    return Table(
        [
            [
                Paragraph(
                    "<b>▲ Improved</b>",
                    BODY_STYLE,
                ),
                Paragraph(
                    "<b>▼ Declined</b>",
                    BODY_STYLE,
                ),
                Paragraph(
                    "<b>→ Flat (within 2%)</b>",
                    BODY_STYLE,
                ),
                Paragraph(
                    "<b>— No comparison</b>",
                    BODY_STYLE,
                ),
            ]
        ],
        colWidths=[
            CONTENT_WIDTH / 4
        ] * 4,
        style=[
            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                LIGHT_BLUE,
            ),
            (
                "BOX",
                (0, 0),
                (-1, -1),
                0.5,
                BORDER_GREY,
            ),
            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER",
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
                7,
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                7,
            ),
        ],
    )


# ============================================================
# FOOTER
# ============================================================

def draw_footer(
    canvas,
    doc,
):

    canvas.saveState()

    canvas.setStrokeColor(
        BORDER_GREY
    )

    canvas.line(
        LEFT_MARGIN,
        8 * mm,
        PAGE_WIDTH - RIGHT_MARGIN,
        8 * mm,
    )

    canvas.setFont(
        "Helvetica",
        7,
    )

    canvas.setFillColor(
        GREY
    )

    canvas.drawString(
        LEFT_MARGIN,
        4.5 * mm,
        "Nifty 100 Financial Intelligence Platform",
    )

    canvas.drawRightString(
        PAGE_WIDTH - RIGHT_MARGIN,
        4.5 * mm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


# ============================================================
# PORTFOLIO PDF GENERATION
# ============================================================

def generate_portfolio_summary():

    print(
        "=" * 100
    )

    print(
        "SPRINT 5 — DAY 35 "
        "PORTFOLIO SUMMARY PDF"
    )

    print(
        "=" * 100
    )

    (
        companies_raw,
        ratios_raw,
        market_raw,
        sectors_raw,
        pnl_raw,
    ) = load_project_data()

    companies = prepare_companies(
        companies_raw
    )

    ratios = prepare_ratios(
        ratios_raw
    )

    market = prepare_market(
        market_raw
    )

    sectors = prepare_sectors(
        sectors_raw
    )

    pnl = prepare_pnl(
        pnl_raw
    )

    if (
        CASHFLOW_INTELLIGENCE_PATH
        .exists()
    ):

        cashflow_intelligence = (
            pd.read_csv(
                CASHFLOW_INTELLIGENCE_PATH
            )
        )

    else:

        cashflow_intelligence = (
            pd.DataFrame()
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    doc = BaseDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=14 * mm,
        title=(
            "Nifty 100 Portfolio Summary"
        ),
        author=(
            "Nifty 100 Financial "
            "Intelligence Platform"
        ),
    )

    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="portfolio",
    )

    template = PageTemplate(
        id="PortfolioTemplate",
        frames=[frame],
        onPage=draw_footer,
    )

    doc.addPageTemplates(
        [template]
    )

    story = []

    snapshot_rows = []

    print(
        f"\nCompanies to process: "
        f"{len(companies)}"
    )

    print(
        "-" * 100
    )

    for index, company in (
        companies.iterrows()
    ):

        snapshot = (
            build_company_snapshot(
                company=company,
                ratios=ratios,
                market=market,
                sectors=sectors,
                pnl=pnl,
                cashflow_intelligence=(
                    cashflow_intelligence
                ),
            )
        )

        print(
            f"[{index + 1:02d}/"
            f"{len(companies):02d}] "
            f"{snapshot['company_id']}"
        )

        story.append(
            build_header(
                snapshot
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
                "Latest Financial Snapshot",
                SECTION_STYLE,
            )
        )

        story.append(
            build_kpi_grid(
                snapshot
            )
        )

        story.append(
            Spacer(
                1,
                12,
            )
        )

        story.append(
            Paragraph(
                "Trend Interpretation",
                SECTION_STYLE,
            )
        )

        story.append(
            build_trend_legend()
        )

        story.append(
            Spacer(
                1,
                12,
            )
        )

        story.append(
            Paragraph(
                "Financial Intelligence",
                SECTION_STYLE,
            )
        )

        story.append(
            build_status_table(
                snapshot
            )
        )

        story.append(
            Spacer(
                1,
                12,
            )
        )

        story.append(
            Paragraph(
                (
                    "Trend arrows compare the latest "
                    "available observation with the "
                    "immediately preceding observation. "
                    "A metric is treated as flat when "
                    "the absolute percentage change is "
                    "within 2%. Historical ROCE is not "
                    "fabricated; where only the latest "
                    "ROCE is available it is shown as "
                    "a current-only metric."
                ),
                SMALL_STYLE,
            )
        )

        # Store validation snapshot
        snapshot_rows.append(
            {
                "company_id":
                    snapshot[
                        "company_id"
                    ],

                "company_name":
                    snapshot[
                        "company_name"
                    ],

                "broad_sector":
                    snapshot[
                        "broad_sector"
                    ],

                "capital_allocation":
                    snapshot[
                        "capital_allocation"
                    ],

                "cashflow_health":
                    snapshot[
                        "cashflow_health"
                    ],
            }
        )

        if (
            index
            < len(companies) - 1
        ):

            story.append(
                PageBreak()
            )

    doc.build(
        story
    )

    snapshots = pd.DataFrame(
        snapshot_rows
    )

    return snapshots


# ============================================================
# VALIDATION
# ============================================================

def validate_portfolio_pdf(
    snapshots,
):

    print(
        "\n"
        + "=" * 100
    )

    print(
        "SPRINT 5 — DAY 35 VALIDATION"
    )

    print(
        "=" * 100
    )

    pdf_exists = (
        OUTPUT_PATH.exists()
    )

    size_bytes = (
        OUTPUT_PATH.stat().st_size
        if pdf_exists
        else 0
    )

    company_count = len(
        snapshots
    )

    duplicate_companies = (
        snapshots[
            "company_id"
        ]
        .duplicated()
        .sum()
    )

    alphabetic = (
        snapshots[
            "company_id"
        ].tolist()
        ==
        sorted(
            snapshots[
                "company_id"
            ].tolist()
        )
    )

    print(
        f"\nPDF created             : "
        f"{pdf_exists}"
    )

    print(
        f"PDF size                : "
        f"{size_bytes:,} bytes"
    )

    print(
        f"Companies included      : "
        f"{company_count}"
    )

    print(
        f"Duplicate companies     : "
        f"{duplicate_companies}"
    )

    print(
        f"Alphabetical ticker order: "
        f"{alphabetic}"
    )

    no_allocation = int(
        (
            snapshots[
                "capital_allocation"
            ]
            == "NOT_AVAILABLE"
        ).sum()
    )

    no_cashflow_health = int(
        (
            snapshots[
                "cashflow_health"
            ]
            == "NOT_AVAILABLE"
        ).sum()
    )

    print(
        f"Missing capital allocation: "
        f"{no_allocation}"
    )

    print(
        f"Missing cash-flow health   : "
        f"{no_cashflow_health}"
    )

    passed = (
        pdf_exists
        and size_bytes > 10000
        and company_count == 92
        and duplicate_companies == 0
        and alphabetic
    )

    print(
        "\n"
        + "-" * 100
    )

    if passed:

        print(
            "DAY 35 PORTFOLIO VALIDATION PASSED"
        )

    else:

        print(
            "DAY 35 PORTFOLIO VALIDATION FAILED"
        )

    print(
        "-" * 100
    )

    return passed


# ============================================================
# MAIN
# ============================================================

def main():

    snapshots = (
        generate_portfolio_summary()
    )

    passed = (
        validate_portfolio_pdf(
            snapshots
        )
    )

    print(
        f"\nOutput:"
        f"\n{OUTPUT_PATH}"
    )

    print(
        "\n"
        + "=" * 100
    )

    if passed:

        print(
            "SPRINT 5 — DAY 35 "
            "PORTFOLIO REPORT COMPLETE"
        )

    else:

        print(
            "SPRINT 5 — DAY 35 "
            "REQUIRES REVIEW"
        )

    print(
        "=" * 100
    )

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()