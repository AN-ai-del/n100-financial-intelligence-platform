"""
Sprint 2 Day 11

Cash Flow KPIs and Capital Allocation Engine
"""


def safe_divide(numerator, denominator):
    if denominator is None or denominator == 0:
        return None

    try:
        return numerator / denominator
    except (TypeError, ZeroDivisionError):
        return None


def calculate_free_cash_flow(operating_activity, investing_activity):
    """
    Free Cash Flow = Operating Cash Flow + Investing Cash Flow

    Negative value is allowed.
    """
    return operating_activity + investing_activity


def calculate_cfo_quality_score(cfo, pat):
    """
    CFO Quality Score = CFO / PAT

    Returns:
        None if PAT = 0
        High Quality if > 1.0
        Moderate if 0.5 to 1.0
        Accrual Risk if < 0.5
    """
    ratio = safe_divide(cfo, pat)

    if ratio is None:
        return None, "NOT_AVAILABLE"

    if ratio > 1.0:
        return ratio, "High Quality"

    if ratio >= 0.5:
        return ratio, "Moderate"

    return ratio, "Accrual Risk"


def calculate_capex_intensity(investing_activity, sales):
    """
    CapEx Intensity = abs(investing_activity) / sales * 100
    """
    ratio = safe_divide(abs(investing_activity), sales)

    if ratio is None:
        return None, "NOT_AVAILABLE"

    value = ratio * 100

    if value < 3:
        return value, "Asset Light"

    if value <= 8:
        return value, "Moderate"

    return value, "Capital Intensive"


def calculate_fcf_conversion_rate(free_cash_flow, operating_profit):
    """
    FCF Conversion Rate = FCF / Operating Profit * 100
    """
    ratio = safe_divide(free_cash_flow, operating_profit)

    if ratio is None:
        return None

    return ratio * 100


def get_sign(value):
    if value > 0:
        return "+"

    if value < 0:
        return "-"

    return "0"


def classify_capital_allocation(cfo, cfi, cff, cfo_quality_label=None):
    """
    Classifies capital allocation using signs of:
    CFO, CFI, CFF
    """

    cfo_sign = get_sign(cfo)
    cfi_sign = get_sign(cfi)
    cff_sign = get_sign(cff)

    pattern = (cfo_sign, cfi_sign, cff_sign)

    if pattern == ("+", "-", "-"):
        if cfo_quality_label == "High Quality":
            return "Shareholder Returns"
        return "Reinvestor"

    if pattern == ("+", "+", "-"):
        return "Liquidating Assets"

    if pattern == ("-", "+", "+"):
        return "Distress Signal"

    if pattern == ("-", "-", "+"):
        return "Growth Funded by Debt"

    if pattern == ("+", "+", "+"):
        return "Cash Accumulator"

    if pattern == ("-", "-", "-"):
        return "Pre-Revenue"

    if pattern == ("+", "-", "+"):
        return "Mixed"

    return "Other"


def build_capital_allocation_record(company_id, year, cfo, cfi, cff, cfo_quality_label=None):
    return {
        "company_id": company_id,
        "year": year,
        "cfo_sign": get_sign(cfo),
        "cfi_sign": get_sign(cfi),
        "cff_sign": get_sign(cff),
        "pattern_label": classify_capital_allocation(
            cfo,
            cfi,
            cff,
            cfo_quality_label
        )
    }