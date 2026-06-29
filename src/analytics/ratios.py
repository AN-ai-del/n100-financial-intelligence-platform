"""
Financial Ratio Engine - Sprint 2 Day 08

This module contains profitability ratio calculations for the
N100 Financial Intelligence Platform.
"""


def safe_divide(numerator, denominator):
    """
    Safely divide two numbers.

    Returns None when denominator is zero, None, or invalid.
    """
    if denominator is None or denominator == 0:
        return None

    try:
        return numerator / denominator
    except (TypeError, ZeroDivisionError):
        return None


def calculate_net_profit_margin(net_profit, sales):
    """
    Net Profit Margin = net_profit / sales * 100

    Returns None if sales is zero or invalid.
    """
    result = safe_divide(net_profit, sales)

    if result is None:
        return None

    return result * 100


def calculate_operating_profit_margin(operating_profit, sales):
    """
    Operating Profit Margin = operating_profit / sales * 100

    Returns None if sales is zero or invalid.
    """
    result = safe_divide(operating_profit, sales)

    if result is None:
        return None

    return result * 100


def check_opm_mismatch(computed_opm, source_opm, tolerance=1.0):
    """
    Check if computed OPM differs from source OPM by more than tolerance.

    Returns True when mismatch is greater than tolerance.
    """
    if computed_opm is None or source_opm is None:
        return False

    return abs(computed_opm - source_opm) > tolerance


def calculate_roe(net_profit, equity_capital, reserves):
    """
    Return on Equity = net_profit / (equity_capital + reserves) * 100

    Returns None if equity + reserves <= 0.
    """
    equity = equity_capital + reserves

    if equity <= 0:
        return None

    result = safe_divide(net_profit, equity)

    if result is None:
        return None

    return result * 100


def calculate_roce(operating_profit, depreciation, equity_capital, reserves, borrowings):
    """
    Return on Capital Employed = EBIT / Capital Employed * 100

    EBIT = operating_profit - depreciation
    Capital Employed = equity_capital + reserves + borrowings
    """
    ebit = operating_profit - depreciation
    capital_employed = equity_capital + reserves + borrowings

    if capital_employed <= 0:
        return None

    result = safe_divide(ebit, capital_employed)

    if result is None:
        return None

    return result * 100


def calculate_roa(net_profit, total_assets):
    """
    Return on Assets = net_profit / total_assets * 100

    Returns None if total_assets is zero or invalid.
    """
    result = safe_divide(net_profit, total_assets)

    if result is None:
        return None

    return result * 100

def calculate_debt_to_equity(borrowings, equity_capital, reserves):
    """
    Debt-to-Equity Ratio

    D/E = Borrowings / (Equity + Reserves)

    Returns:
        0 when borrowings = 0
        None when denominator <= 0
    """

    if borrowings == 0:
        return 0

    equity = equity_capital + reserves

    if equity <= 0:
        return None

    return borrowings / equity


def high_leverage_flag(de_ratio, sector):
    """
    Returns True when:
        D/E > 5
        AND company is NOT Financials
    """

    if de_ratio is None:
        return False

    if sector == "Financials":
        return False

    return de_ratio > 5


def calculate_interest_coverage(
        operating_profit,
        other_income,
        interest):

    """
    Interest Coverage Ratio

    (Operating Profit + Other Income)
/ Interest
    """

    if interest == 0:
        return None

    return (operating_profit + other_income) / interest


def icr_label(icr):

    if icr is None:
        return "Debt Free"

    return ""


def icr_warning(icr):

    if icr is None:
        return False

    return icr < 1.5


def calculate_net_debt(
        borrowings,
        investments):

    """
    Net Debt

    Borrowings - Investments
    """

    return borrowings - investments


def calculate_asset_turnover(
        sales,
        total_assets):

    """
    Asset Turnover

    Sales / Total Assets
    """

    if total_assets == 0:
        return None

    return sales / total_assets