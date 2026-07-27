from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


# ============================================================
# PATH CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "db" / "nifty100.db"

OUTPUT_DIR = BASE_DIR / "reports" / "tearsheets"
TEST_OUTPUT_DIR = OUTPUT_DIR / "day33_test"

PROS_CONS_PATH = BASE_DIR / "output" / "pros_cons_generated.csv"
CASHFLOW_INTELLIGENCE_PATH = (
    BASE_DIR / "output" / "cashflow_intelligence.csv"
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

GOLD = colors.HexColor("#D4A017")
LIGHT_GOLD = colors.HexColor("#FFF8DC")

GREY = colors.HexColor("#666666")
LIGHT_GREY = colors.HexColor("#F4F6F7")
BORDER_GREY = colors.HexColor("#D5D8DC")

WHITE = colors.white
BLACK = colors.black


# ============================================================
# PDF CONFIGURATION
# ============================================================

PAGE_WIDTH, PAGE_HEIGHT = A4

LEFT_MARGIN = 12 * mm
RIGHT_MARGIN = 12 * mm
TOP_MARGIN = 12 * mm
BOTTOM_MARGIN = 12 * mm

CONTENT_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN


# ============================================================
# STYLES
# ============================================================

styles = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle(
    "TearsheetTitle",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=18,
    leading=21,
    textColor=WHITE,
    alignment=TA_LEFT,
)

SUBTITLE_STYLE = ParagraphStyle(
    "TearsheetSubtitle",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=9,
    leading=12,
    textColor=colors.HexColor("#D6EAF8"),
)

SECTION_STYLE = ParagraphStyle(
    "Section",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=14,
    textColor=NAVY,
    spaceBefore=4,
    spaceAfter=5,
)

BODY_STYLE = ParagraphStyle(
    "Body",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=8,
    leading=11,
    textColor=BLACK,
    wordWrap="CJK",
)

SMALL_STYLE = ParagraphStyle(
    "Small",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=7,
    leading=9,
    textColor=GREY,
    wordWrap="CJK",
)

PRO_STYLE = ParagraphStyle(
    "Pro",
    parent=BODY_STYLE,
    textColor=colors.HexColor("#145A32"),
    leftIndent=5,
    bulletIndent=0,
)

CON_STYLE = ParagraphStyle(
    "Con",
    parent=BODY_STYLE,
    textColor=colors.HexColor("#922B21"),
    leftIndent=5,
    bulletIndent=0,
)

KPI_LABEL_STYLE = ParagraphStyle(
    "KPILabel",
    parent=SMALL_STYLE,
    alignment=TA_CENTER,
    fontName="Helvetica-Bold",
    textColor=GREY,
)

KPI_VALUE_STYLE = ParagraphStyle(
    "KPIValue",
    parent=styles["Normal"],
    alignment=TA_CENTER,
    fontName="Helvetica-Bold",
    fontSize=13,
    leading=16,
    textColor=NAVY,
)


# ============================================================
# GENERIC HELPERS
# ============================================================

def clean_text(value) -> str:
    if value is None:
        return ""

    if pd.isna(value):
        return ""

    return str(value).replace("\n", " ").strip()


def safe_float(value):
    try:
        if value is None or pd.isna(value):
            return None

        return float(value)

    except (TypeError, ValueError):
        return None


def format_number(value, decimals=2):
    value = safe_float(value)

    if value is None:
        return "N/A"

    return f"{value:,.{decimals}f}"


def format_pct(value, decimals=2):
    value = safe_float(value)

    if value is None:
        return "N/A"

    return f"{value:,.{decimals}f}%"


def format_crore(value, decimals=0):
    value = safe_float(value)

    if value is None:
        return "N/A"

    return f"Rs. {value:,.{decimals}f} Cr"


def extract_year(value):
    if value is None:
        return None

    text = str(value)

    match = pd.Series([text]).str.extract(r"(\d{4})").iloc[0, 0]

    if pd.isna(match):
        return None

    return int(match)


def numeric_series(series):
    return pd.to_numeric(
        series,
        errors="coerce",
    )


# ============================================================
# DATABASE HELPERS
# ============================================================

def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    return sqlite3.connect(DB_PATH)


def load_table(table_name):
    with get_connection() as conn:
        return pd.read_sql_query(
            f'SELECT * FROM "{table_name}"',
            conn,
        )


def repair_embedded_header(df):
    """
    Raw imported tables such as profitandloss, balancesheet,
    and cashflow contain the real column names in the first row.
    """

    if df.empty:
        return df.copy()

    first_row = df.iloc[0].astype(str).str.strip()

    first_values = {
        value.lower()
        for value in first_row.tolist()
    }

    if "company_id" not in first_values:
        return df.copy()

    repaired = df.iloc[1:].copy()

    repaired.columns = [
        clean_text(column).lower().replace(" ", "_")
        for column in first_row
    ]

    repaired = repaired.reset_index(drop=True)

    return repaired


# ============================================================
# LOAD SOURCE DATA
# ============================================================

def load_sources():

    companies = load_table("companies")

    pnl = repair_embedded_header(
        load_table("profitandloss")
    )

    balance_sheet = repair_embedded_header(
        load_table("balancesheet")
    )

    cashflow = repair_embedded_header(
        load_table("cashflow")
    )

    ratios = load_table("financial_ratios")

    market_cap = load_table("market_cap")

    if PROS_CONS_PATH.exists():
        pros_cons = pd.read_csv(PROS_CONS_PATH)
    else:
        pros_cons = pd.DataFrame(
            columns=[
                "company_id",
                "type",
                "rule_id",
                "text",
                "confidence_pct",
            ]
        )

    if CASHFLOW_INTELLIGENCE_PATH.exists():
        cashflow_intelligence = pd.read_csv(
            CASHFLOW_INTELLIGENCE_PATH
        )
    else:
        cashflow_intelligence = pd.DataFrame()

    return {
        "companies": companies,
        "pnl": pnl,
        "balance_sheet": balance_sheet,
        "cashflow": cashflow,
        "ratios": ratios,
        "market_cap": market_cap,
        "pros_cons": pros_cons,
        "cashflow_intelligence": cashflow_intelligence,
    }


# ============================================================
# COMPANY DATA
# ============================================================

def prepare_company_data(
    ticker,
    sources,
):

    ticker = ticker.upper().strip()

    companies = sources["companies"]
    pnl = sources["pnl"]
    balance_sheet = sources["balance_sheet"]
    cashflow = sources["cashflow"]
    ratios = sources["ratios"]
    market_cap = sources["market_cap"]
    pros_cons = sources["pros_cons"]
    cashflow_intelligence = sources["cashflow_intelligence"]

    # --------------------------------------------------------
    # Company
    # --------------------------------------------------------

    company = companies[
        companies["id"].astype(str).str.upper() == ticker
    ].copy()

    if company.empty:
        raise ValueError(
            f"Company not found: {ticker}"
        )

    company = company.iloc[0]

    # --------------------------------------------------------
    # P&L
    # --------------------------------------------------------

    company_pnl = pnl[
        pnl["company_id"].astype(str).str.upper() == ticker
    ].copy()

    if not company_pnl.empty:

        company_pnl["year_numeric"] = (
            company_pnl["year"].apply(extract_year)
        )

        for column in [
            "sales",
            "expenses",
            "operating_profit",
            "opm_percentage",
            "other_income",
            "interest",
            "depreciation",
            "profit_before_tax",
            "tax_percentage",
            "net_profit",
            "eps",
            "dividend_payout",
        ]:
            if column in company_pnl.columns:
                company_pnl[column] = numeric_series(
                    company_pnl[column]
                )

        company_pnl = company_pnl.sort_values(
            "year_numeric"
        )

    # --------------------------------------------------------
    # Balance sheet
    # --------------------------------------------------------

    company_bs = balance_sheet[
        balance_sheet["company_id"]
        .astype(str)
        .str.upper()
        == ticker
    ].copy()

    if not company_bs.empty:

        company_bs["year_numeric"] = (
            company_bs["year"].apply(extract_year)
        )

        for column in [
            "equity_capital",
            "reserves",
            "borrowings",
            "other_liabilities",
            "total_liabilities",
            "fixed_assets",
            "cwip",
            "investments",
            "other_asset",
            "total_assets",
        ]:
            if column in company_bs.columns:
                company_bs[column] = numeric_series(
                    company_bs[column]
                )

        company_bs = company_bs.sort_values(
            "year_numeric"
        )

        company_bs["shareholders_equity"] = (
            company_bs.get(
                "equity_capital",
                pd.Series(
                    0,
                    index=company_bs.index,
                ),
            ).fillna(0)
            +
            company_bs.get(
                "reserves",
                pd.Series(
                    0,
                    index=company_bs.index,
                ),
            ).fillna(0)
        )

    # --------------------------------------------------------
    # Cash flow
    # --------------------------------------------------------

    company_cf = cashflow[
        cashflow["company_id"]
        .astype(str)
        .str.upper()
        == ticker
    ].copy()

    if not company_cf.empty:

        company_cf["year_numeric"] = (
            company_cf["year"].apply(extract_year)
        )

        for column in [
            "operating_activity",
            "investing_activity",
            "financing_activity",
            "net_cash_flow",
        ]:
            if column in company_cf.columns:
                company_cf[column] = numeric_series(
                    company_cf[column]
                )

        company_cf = company_cf.sort_values(
            "year_numeric"
        )

    # --------------------------------------------------------
    # Ratios
    # --------------------------------------------------------

    company_ratios = ratios[
        ratios["company_id"]
        .astype(str)
        .str.upper()
        == ticker
    ].copy()

    if not company_ratios.empty:

        company_ratios["year_numeric"] = (
            company_ratios["year"].apply(extract_year)
        )

        company_ratios = company_ratios.sort_values(
            "year_numeric"
        )

    # --------------------------------------------------------
    # Valuation
    # --------------------------------------------------------

    company_market = market_cap[
        market_cap["company_id"]
        .astype(str)
        .str.upper()
        == ticker
    ].copy()

    if not company_market.empty:
        company_market = company_market.sort_values(
            "year"
        )

    # --------------------------------------------------------
    # Pros / Cons
    # --------------------------------------------------------

    company_signals = pros_cons[
        pros_cons["company_id"]
        .astype(str)
        .str.upper()
        == ticker
    ].copy()

    if not company_signals.empty:

        company_signals["confidence_pct"] = pd.to_numeric(
            company_signals["confidence_pct"],
            errors="coerce",
        )

        company_signals = company_signals.sort_values(
            "confidence_pct",
            ascending=False,
        )

    # --------------------------------------------------------
    # Cash-flow intelligence
    # --------------------------------------------------------

    if (
        not cashflow_intelligence.empty
        and "company_id" in cashflow_intelligence.columns
    ):

        company_intelligence = cashflow_intelligence[
            cashflow_intelligence["company_id"]
            .astype(str)
            .str.upper()
            == ticker
        ].copy()

        if (
            not company_intelligence.empty
            and "year_numeric"
            in company_intelligence.columns
        ):
            company_intelligence = (
                company_intelligence.sort_values(
                    "year_numeric"
                )
            )

    else:
        company_intelligence = pd.DataFrame()

    return {
        "ticker": ticker,
        "company": company,
        "pnl": company_pnl,
        "balance_sheet": company_bs,
        "cashflow": company_cf,
        "ratios": company_ratios,
        "market_cap": company_market,
        "signals": company_signals,
        "cashflow_intelligence": company_intelligence,
    }


# ============================================================
# LATEST RECORD HELPERS
# ============================================================

def latest_row(df):
    if df is None or df.empty:
        return None

    return df.iloc[-1]


def get_latest_metrics(data):

    company = data["company"]

    ratio = latest_row(
        data["ratios"]
    )

    valuation = latest_row(
        data["market_cap"]
    )

    pnl = latest_row(
        data["pnl"]
    )

    intelligence = latest_row(
        data["cashflow_intelligence"]
    )

    metrics = {
        "roe": None,
        "roce": safe_float(
            company.get("roce_percentage")
        ),
        "opm": None,
        "de": None,
        "fcf": None,
        "pe": None,
        "market_cap": None,
        "net_profit": None,
        "allocation": "NOT_AVAILABLE",
        "cashflow_health": "NOT_AVAILABLE",
    }

    if ratio is not None:

        metrics["roe"] = safe_float(
            ratio.get(
                "return_on_equity_pct"
            )
        )

        metrics["opm"] = safe_float(
            ratio.get(
                "operating_profit_margin_pct"
            )
        )

        metrics["de"] = safe_float(
            ratio.get(
                "debt_to_equity"
            )
        )

        metrics["fcf"] = safe_float(
            ratio.get(
                "free_cash_flow_cr"
            )
        )

    if metrics["roe"] is None:
        metrics["roe"] = safe_float(
            company.get("roe_percentage")
        )

    if valuation is not None:

        metrics["pe"] = safe_float(
            valuation.get("pe_ratio")
        )

        metrics["market_cap"] = safe_float(
            valuation.get(
                "market_cap_crore"
            )
        )

    if pnl is not None:
        metrics["net_profit"] = safe_float(
            pnl.get("net_profit")
        )

    if intelligence is not None:

        metrics["allocation"] = clean_text(
            intelligence.get(
                "capital_allocation_pattern"
            )
        ) or "NOT_AVAILABLE"

        metrics["cashflow_health"] = clean_text(
            intelligence.get(
                "cashflow_health_label"
            )
        ) or "NOT_AVAILABLE"

    return metrics


# ============================================================
# CHART HELPERS
# ============================================================

def save_figure(
    fig,
    path,
):
    fig.savefig(
        path,
        dpi=160,
        bbox_inches="tight",
    )

    plt.close(fig)


def create_revenue_profit_chart(
    data,
    path,
):

    pnl = data["pnl"].copy()

    if pnl.empty:
        return False

    pnl = pnl.dropna(
        subset=["year_numeric"]
    ).tail(10)

    if pnl.empty:
        return False

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(9, 3.2),
    )

    years = (
        pnl["year_numeric"]
        .astype(int)
        .astype(str)
    )

    axes[0].bar(
        years,
        pnl["sales"],
    )

    axes[0].set_title(
        "Revenue — 10 Year Trend",
        fontsize=10,
        fontweight="bold",
    )

    axes[0].set_ylabel(
        "Rs. Crore",
        fontsize=8,
    )

    axes[0].tick_params(
        axis="x",
        rotation=45,
        labelsize=7,
    )

    axes[0].tick_params(
        axis="y",
        labelsize=7,
    )

    axes[0].grid(
        axis="y",
        alpha=0.2,
    )

    axes[1].bar(
        years,
        pnl["net_profit"],
    )

    axes[1].set_title(
        "Net Profit — 10 Year Trend",
        fontsize=10,
        fontweight="bold",
    )

    axes[1].set_ylabel(
        "Rs. Crore",
        fontsize=8,
    )

    axes[1].tick_params(
        axis="x",
        rotation=45,
        labelsize=7,
    )

    axes[1].tick_params(
        axis="y",
        labelsize=7,
    )

    axes[1].grid(
        axis="y",
        alpha=0.2,
    )

    fig.tight_layout()

    save_figure(
        fig,
        path,
    )

    return True


def create_roe_roce_chart(
    data,
    path,
):

    ratios = data["ratios"].copy()

    company = data["company"]

    if ratios.empty:
        return False

    ratios = ratios.dropna(
        subset=["year_numeric"]
    ).copy()

    ratios = ratios.drop_duplicates(
        subset=["year_numeric"],
        keep="last",
    )

    ratios = ratios.tail(10)

    if ratios.empty:
        return False

    years = ratios[
        "year_numeric"
    ].astype(int)

    roe = pd.to_numeric(
        ratios["return_on_equity_pct"],
        errors="coerce",
    )

    # The source company master contains current ROCE only.
    # Until historical ROCE is available, display the latest
    # master ROCE as a reference line rather than fabricating
    # historical values.

    latest_roce = safe_float(
        company.get(
            "roce_percentage"
        )
    )

    fig, ax1 = plt.subplots(
        figsize=(8.8, 2.7)
    )

    ax1.plot(
        years,
        roe,
        marker="o",
        linewidth=2,
        label="ROE",
    )

    ax1.set_ylabel(
        "ROE (%)",
        fontsize=8,
    )

    ax1.tick_params(
        axis="both",
        labelsize=7,
    )

    ax1.grid(
        alpha=0.2,
    )

    if latest_roce is not None:

        ax2 = ax1.twinx()

        roce_values = np.repeat(
            latest_roce,
            len(years),
        )

        ax2.plot(
            years,
            roce_values,
            linestyle="--",
            linewidth=1.7,
            label="ROCE Reference",
        )

        ax2.set_ylabel(
            "ROCE (%)",
            fontsize=8,
        )

        ax2.tick_params(
            axis="y",
            labelsize=7,
        )

        lines1, labels1 = (
            ax1.get_legend_handles_labels()
        )

        lines2, labels2 = (
            ax2.get_legend_handles_labels()
        )

        ax1.legend(
            lines1 + lines2,
            labels1 + labels2,
            loc="best",
            fontsize=7,
        )

    else:

        ax1.legend(
            loc="best",
            fontsize=7,
        )

    ax1.set_title(
        "Return on Equity & ROCE Reference",
        fontsize=10,
        fontweight="bold",
    )

    fig.tight_layout()

    save_figure(
        fig,
        path,
    )

    return True


def create_balance_sheet_chart(
    data,
    path,
):

    bs = data["balance_sheet"].copy()

    if bs.empty:
        return False

    bs = bs.dropna(
        subset=["year_numeric"]
    ).tail(10)

    if bs.empty:
        return False

    years = (
        bs["year_numeric"]
        .astype(int)
        .astype(str)
    )

    equity = pd.to_numeric(
        bs["shareholders_equity"],
        errors="coerce",
    ).fillna(0)

    borrowings = pd.to_numeric(
        bs["borrowings"],
        errors="coerce",
    ).fillna(0)

    other_liabilities = pd.to_numeric(
        bs["other_liabilities"],
        errors="coerce",
    ).fillna(0)

    fig, ax = plt.subplots(
        figsize=(8.8, 3.0)
    )

    ax.bar(
        years,
        equity,
        label="Equity + Reserves",
    )

    ax.bar(
        years,
        borrowings,
        bottom=equity,
        label="Borrowings",
    )

    ax.bar(
        years,
        other_liabilities,
        bottom=equity + borrowings,
        label="Other Liabilities",
    )

    ax.set_title(
        "Balance Sheet Composition",
        fontsize=10,
        fontweight="bold",
    )

    ax.set_ylabel(
        "Rs. Crore",
        fontsize=8,
    )

    ax.tick_params(
        axis="x",
        rotation=45,
        labelsize=7,
    )

    ax.tick_params(
        axis="y",
        labelsize=7,
    )

    ax.legend(
        fontsize=7,
        ncol=3,
        loc="upper left",
    )

    ax.grid(
        axis="y",
        alpha=0.2,
    )

    fig.tight_layout()

    save_figure(
        fig,
        path,
    )

    return True


def create_cashflow_chart(
    data,
    path,
):

    cf = data["cashflow"].copy()

    if cf.empty:
        return False

    cf = cf.dropna(
        subset=["year_numeric"]
    )

    if cf.empty:
        return False

    latest = cf.iloc[-1]

    labels = [
        "CFO",
        "CFI",
        "CFF",
        "Net Cash",
    ]

    values = [
        safe_float(
            latest.get(
                "operating_activity"
            )
        ) or 0,
        safe_float(
            latest.get(
                "investing_activity"
            )
        ) or 0,
        safe_float(
            latest.get(
                "financing_activity"
            )
        ) or 0,
        safe_float(
            latest.get(
                "net_cash_flow"
            )
        ) or 0,
    ]

    fig, ax = plt.subplots(
        figsize=(8.8, 2.5)
    )

    ax.bar(
        labels,
        values,
    )

    ax.axhline(
        0,
        linewidth=0.8,
    )

    ax.set_title(
        f"Cash Flow — Latest Year ({int(latest['year_numeric'])})",
        fontsize=10,
        fontweight="bold",
    )

    ax.set_ylabel(
        "Rs. Crore",
        fontsize=8,
    )

    ax.tick_params(
        axis="both",
        labelsize=7,
    )

    ax.grid(
        axis="y",
        alpha=0.2,
    )

    fig.tight_layout()

    save_figure(
        fig,
        path,
    )

    return True


# ============================================================
# PDF COMPONENTS
# ============================================================

def build_header(
    data,
):

    company = data["company"]
    ticker = data["ticker"]

    company_name = clean_text(
        company.get("company_name")
    )

    ratios = data["ratios"]

    if not ratios.empty:

        latest_ratio = ratios.iloc[-1]

        sector = clean_text(
            latest_ratio.get(
                "broad_sector"
            )
        )

        sub_sector = clean_text(
            latest_ratio.get(
                "sub_sector"
            )
        )

    else:
        sector = ""
        sub_sector = ""

    subtitle_parts = [
        part
        for part in [
            ticker,
            sector,
            sub_sector,
        ]
        if part
    ]

    header_data = [
        [
            Paragraph(
                company_name,
                TITLE_STYLE,
            ),
            Paragraph(
                ticker,
                ParagraphStyle(
                    "Ticker",
                    parent=TITLE_STYLE,
                    alignment=TA_CENTER,
                    fontSize=15,
                ),
            ),
        ],
        [
            Paragraph(
                " | ".join(
                    subtitle_parts
                ),
                SUBTITLE_STYLE,
            ),
            "",
        ],
    ]

    table = Table(
        header_data,
        colWidths=[
            CONTENT_WIDTH * 0.78,
            CONTENT_WIDTH * 0.22,
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
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
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
                    8,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 1),
                    (-1, 1),
                    7,
                ),
                (
                    "SPAN",
                    (0, 1),
                    (1, 1),
                ),
            ]
        )
    )

    return table


def kpi_tile(
    label,
    value,
):

    data = [
        [
            Paragraph(
                label,
                KPI_LABEL_STYLE,
            )
        ],
        [
            Paragraph(
                value,
                KPI_VALUE_STYLE,
            )
        ],
    ]

    table = Table(
        data,
        colWidths=[
            CONTENT_WIDTH / 3 - 4
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
    metrics,
):

    tiles = [
        kpi_tile(
            "Return on Equity",
            format_pct(
                metrics["roe"]
            ),
        ),
        kpi_tile(
            "ROCE",
            format_pct(
                metrics["roce"]
            ),
        ),
        kpi_tile(
            "Operating Margin",
            format_pct(
                metrics["opm"]
            ),
        ),
        kpi_tile(
            "Debt / Equity",
            format_number(
                metrics["de"]
            ),
        ),
        kpi_tile(
            "Free Cash Flow",
            format_crore(
                metrics["fcf"]
            ),
        ),
        kpi_tile(
            "P/E Ratio",
            format_number(
                metrics["pe"]
            ),
        ),
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
                    "MIDDLE",
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


def image_or_message(
    path,
    width,
    height,
):

    if path.exists():

        return Image(
            str(path),
            width=width,
            height=height,
        )

    return Table(
        [
            [
                Paragraph(
                    "Data not available for this chart.",
                    SMALL_STYLE,
                )
            ]
        ],
        colWidths=[width],
        rowHeights=[height],
        style=[
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
        ],
    )


def build_pros_cons(
    data,
):

    signals = data["signals"]

    if signals.empty:

        pros = [
            "No automated positive signal available."
        ]

        cons = [
            "No automated risk signal available."
        ]

    else:

        pros = (
            signals[
                signals["type"]
                .astype(str)
                .str.lower()
                == "pro"
            ]
            .head(4)["text"]
            .astype(str)
            .tolist()
        )

        cons = (
            signals[
                signals["type"]
                .astype(str)
                .str.lower()
                == "con"
            ]
            .head(4)["text"]
            .astype(str)
            .tolist()
        )

        if not pros:
            pros = [
                "No automated positive signal available."
            ]

        if not cons:
            cons = [
                "No automated risk signal available."
            ]

    pro_elements = [
        Paragraph(
            "<b>Financial Strengths</b>",
            ParagraphStyle(
                "ProHeading",
                parent=SECTION_STYLE,
                textColor=GREEN,
            ),
        )
    ]

    for text in pros:

        pro_elements.append(
            Paragraph(
                clean_text(text),
                PRO_STYLE,
                bulletText="•",
            )
        )

        pro_elements.append(
            Spacer(
                1,
                2,
            )
        )

    con_elements = [
        Paragraph(
            "<b>Financial Risks</b>",
            ParagraphStyle(
                "ConHeading",
                parent=SECTION_STYLE,
                textColor=RED,
            ),
        )
    ]

    for text in cons:

        con_elements.append(
            Paragraph(
                clean_text(text),
                CON_STYLE,
                bulletText="•",
            )
        )

        con_elements.append(
            Spacer(
                1,
                2,
            )
        )

    table = Table(
        [
            [
                pro_elements,
                con_elements,
            ]
        ],
        colWidths=[
            CONTENT_WIDTH / 2 - 3,
            CONTENT_WIDTH / 2 - 3,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, 0),
                    LIGHT_GREEN,
                ),
                (
                    "BACKGROUND",
                    (1, 0),
                    (1, 0),
                    LIGHT_RED,
                ),
                (
                    "BOX",
                    (0, 0),
                    (0, 0),
                    0.5,
                    GREEN,
                ),
                (
                    "BOX",
                    (1, 0),
                    (1, 0),
                    0.5,
                    RED,
                ),
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


def build_allocation_badge(
    metrics,
):

    allocation = (
        metrics["allocation"]
        or "NOT_AVAILABLE"
    )

    health = (
        metrics["cashflow_health"]
        or "NOT_AVAILABLE"
    )

    content = [
        [
            Paragraph(
                "<b>Capital Allocation</b>",
                BODY_STYLE,
            ),
            Paragraph(
                allocation,
                ParagraphStyle(
                    "Allocation",
                    parent=BODY_STYLE,
                    fontName="Helvetica-Bold",
                    alignment=TA_CENTER,
                    textColor=NAVY,
                ),
            ),
            Paragraph(
                "<b>Cash Flow Health</b>",
                BODY_STYLE,
            ),
            Paragraph(
                health,
                ParagraphStyle(
                    "Health",
                    parent=BODY_STYLE,
                    fontName="Helvetica-Bold",
                    alignment=TA_CENTER,
                    textColor=NAVY,
                ),
            ),
        ]
    ]

    table = Table(
        content,
        colWidths=[
            CONTENT_WIDTH * 0.20,
            CONTENT_WIDTH * 0.30,
            CONTENT_WIDTH * 0.20,
            CONTENT_WIDTH * 0.30,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    LIGHT_GOLD,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.8,
                    GOLD,
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
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
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    return table


# ============================================================
# PAGE FOOTER
# ============================================================

def draw_page_footer(
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
# TEARSHEET GENERATOR
# ============================================================

def generate_tearsheet(
    ticker,
    sources=None,
    output_dir=None,
):

    ticker = ticker.upper().strip()

    if sources is None:
        sources = load_sources()

    if output_dir is None:
        output_dir = OUTPUT_DIR

    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = prepare_company_data(
        ticker,
        sources,
    )

    metrics = get_latest_metrics(
        data
    )

    output_path = (
        output_dir
        / f"{ticker}_tearsheet.pdf"
    )

    with tempfile.TemporaryDirectory() as temp_dir:

        temp_dir = Path(temp_dir)

        revenue_profit_path = (
            temp_dir
            / "revenue_profit.png"
        )

        roe_roce_path = (
            temp_dir
            / "roe_roce.png"
        )

        balance_sheet_path = (
            temp_dir
            / "balance_sheet.png"
        )

        cashflow_path = (
            temp_dir
            / "cashflow.png"
        )

        if create_revenue_profit_chart(
            data,
            revenue_profit_path,
        ) is False:
            revenue_profit_path = (
                temp_dir
                / "missing_revenue.png"
            )

        if create_roe_roce_chart(
            data,
            roe_roce_path,
        ) is False:
            roe_roce_path = (
                temp_dir
                / "missing_roe.png"
            )

        if create_balance_sheet_chart(
            data,
            balance_sheet_path,
        ) is False:
            balance_sheet_path = (
                temp_dir
                / "missing_bs.png"
            )

        if create_cashflow_chart(
            data,
            cashflow_path,
        ) is False:
            cashflow_path = (
                temp_dir
                / "missing_cf.png"
            )

        doc = BaseDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=LEFT_MARGIN,
            rightMargin=RIGHT_MARGIN,
            topMargin=TOP_MARGIN,
            bottomMargin=14 * mm,
            title=(
                f"{ticker} Company Tearsheet"
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
            id="normal",
        )

        template = PageTemplate(
            id="Tearsheet",
            frames=[frame],
            onPage=draw_page_footer,
        )

        doc.addPageTemplates(
            [template]
        )

        story = []

        # ====================================================
        # PAGE 1
        # ====================================================

        story.append(
            build_header(data)
        )

        story.append(
            Spacer(1, 6)
        )

        story.append(
            Paragraph(
                "Financial Snapshot",
                SECTION_STYLE,
            )
        )

        story.append(
            build_kpi_grid(
                metrics
            )
        )

        story.append(
            Spacer(1, 6)
        )

        story.append(
            Paragraph(
                "Revenue & Profit Performance",
                SECTION_STYLE,
            )
        )

        story.append(
            image_or_message(
                revenue_profit_path,
                CONTENT_WIDTH,
                64 * mm,
            )
        )

        story.append(
            Spacer(1, 4)
        )

        story.append(
            Paragraph(
                "Return Metrics",
                SECTION_STYLE,
            )
        )

        story.append(
            image_or_message(
                roe_roce_path,
                CONTENT_WIDTH,
                49 * mm,
            )
        )

        story.append(
            PageBreak()
        )

        # ====================================================
        # PAGE 2
        # ====================================================

        story.append(
            build_header(data)
        )

        story.append(
            Spacer(1, 5)
        )

        story.append(
            Paragraph(
                "Balance Sheet Composition",
                SECTION_STYLE,
            )
        )

        story.append(
            image_or_message(
                balance_sheet_path,
                CONTENT_WIDTH,
                52 * mm,
            )
        )

        story.append(
            Spacer(1, 4)
        )

        story.append(
            Paragraph(
                "Cash Flow Intelligence",
                SECTION_STYLE,
            )
        )

        story.append(
            image_or_message(
                cashflow_path,
                CONTENT_WIDTH,
                40 * mm,
            )
        )

        story.append(
            Spacer(1, 5)
        )

        story.append(
            KeepTogether(
                [
                    build_pros_cons(
                        data
                    ),
                    Spacer(
                        1,
                        6,
                    ),
                    build_allocation_badge(
                        metrics
                    ),
                ]
            )
        )

        doc.build(
            story
        )

    return output_path


# ============================================================
# DAY 33 VALIDATION
# ============================================================

TEST_COMPANIES = [
    "TCS",
    "HDFCBANK",
    "RELIANCE",
    "SUNPHARMA",
    "TATASTEEL",
]


def validate_test_tearsheets(
    generated_files,
):

    print(
        "\n"
        + "=" * 100
    )

    print(
        "SPRINT 5 — DAY 33 "
        "PDF TEARSHEET VALIDATION"
    )

    print(
        "=" * 100
    )

    passed = True

    results = []

    for ticker, path in generated_files.items():

        exists = path.exists()

        size_bytes = (
            path.stat().st_size
            if exists
            else 0
        )

        valid_size = (
            size_bytes > 5000
        )

        status = (
            "PASS"
            if exists and valid_size
            else "FAIL"
        )

        if status == "FAIL":
            passed = False

        results.append(
            {
                "company_id": ticker,
                "pdf_created": exists,
                "size_bytes": size_bytes,
                "status": status,
            }
        )

    validation_df = pd.DataFrame(
        results
    )

    print(
        "\n"
        + validation_df.to_string(
            index=False
        )
    )

    print(
        "\n"
        + "-" * 100
    )

    print(
        f"Companies tested : "
        f"{len(validation_df)}"
    )

    print(
        "PDFs created     : "
        f"{validation_df['pdf_created'].sum()}"
    )

    print(
        "PASS             : "
        f"{(validation_df['status'] == 'PASS').sum()}"
    )

    print(
        "FAIL             : "
        f"{(validation_df['status'] == 'FAIL').sum()}"
    )

    print(
        "-" * 100
    )

    if passed:

        print(
            "\n"
            + "=" * 100
        )

        print(
            "DAY 33 VALIDATION PASSED — "
            "ALL TEST TEARSHEETS GENERATED"
        )

        print(
            "=" * 100
        )

    else:

        print(
            "\n"
            + "=" * 100
        )

        print(
            "DAY 33 VALIDATION FAILED"
        )

        print(
            "=" * 100
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
        "SPRINT 5 — DAY 33 "
        "PDF TEARSHEET TEMPLATE"
    )

    print(
        "=" * 100
    )

    TEST_OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "\nLoading project data..."
    )

    sources = load_sources()

    print(
        "Data loaded successfully."
    )

    generated_files = {}

    print(
        "\nGenerating test tearsheets..."
    )

    print(
        "-" * 100
    )

    for ticker in TEST_COMPANIES:

        try:

            print(
                f"{ticker:<15}",
                end="",
            )

            path = generate_tearsheet(
                ticker=ticker,
                sources=sources,
                output_dir=TEST_OUTPUT_DIR,
            )

            generated_files[
                ticker
            ] = path

            print(
                f"CREATED  {path.name}"
            )

        except Exception as exc:

            print(
                f"FAILED   {exc}"
            )

            generated_files[
                ticker
            ] = (
                TEST_OUTPUT_DIR
                / f"{ticker}_tearsheet.pdf"
            )

    passed = validate_test_tearsheets(
        generated_files
    )

    print(
        "\nOutput directory:"
    )

    print(
        TEST_OUTPUT_DIR
    )

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()