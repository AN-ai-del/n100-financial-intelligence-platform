from src.analytics.ratios import (
    calculate_net_profit_margin,
    calculate_operating_profit_margin,
    check_opm_mismatch,
    calculate_roe,
    calculate_roce,
    calculate_roa,
)


def test_net_profit_margin_normal_case():
    assert calculate_net_profit_margin(100, 1000) == 10


def test_net_profit_margin_zero_sales():
    assert calculate_net_profit_margin(100, 0) is None


def test_operating_profit_margin_normal_case():
    assert calculate_operating_profit_margin(200, 1000) == 20


def test_operating_profit_margin_zero_sales():
    assert calculate_operating_profit_margin(200, 0) is None


def test_opm_mismatch_true():
    assert check_opm_mismatch(20, 17) is True


def test_opm_mismatch_false():
    assert check_opm_mismatch(20, 19.5) is False


def test_roe_normal_case():
    assert calculate_roe(100, 400, 600) == 10


def test_roe_negative_equity():
    assert calculate_roe(100, -500, 100) is None


def test_roce_normal_case():
    result = calculate_roce(
        operating_profit=300,
        depreciation=50,
        equity_capital=500,
        reserves=500,
        borrowings=250
    )

    assert result == 20


def test_roa_normal_case():
    assert calculate_roa(100, 2000) == 5


def test_roa_zero_assets():
    assert calculate_roa(100, 0) is None


from src.analytics.ratios import (
    calculate_debt_to_equity,
    high_leverage_flag,
    calculate_interest_coverage,
    icr_label,
    icr_warning,
    calculate_net_debt,
    calculate_asset_turnover,
)


def test_debt_to_equity_normal():
    assert calculate_debt_to_equity(
        500,
        250,
        250
    ) == 1


def test_debt_to_equity_debt_free():
    assert calculate_debt_to_equity(
        0,
        250,
        250
    ) == 0


def test_debt_to_equity_negative_equity():
    assert calculate_debt_to_equity(
        500,
        -100,
        50
    ) is None


def test_high_leverage():
    assert high_leverage_flag(
        6,
        "IT"
    ) is True


def test_financial_sector_not_flagged():
    assert high_leverage_flag(
        10,
        "Financials"
    ) is False


def test_interest_coverage():
    assert calculate_interest_coverage(
        100,
        20,
        10
    ) == 12


def test_interest_zero():
    assert calculate_interest_coverage(
        100,
        20,
        0
    ) is None


def test_icr_label():
    assert icr_label(None) == "Debt Free"


def test_icr_warning():
    assert icr_warning(1.2) is True


def test_net_debt():
    assert calculate_net_debt(
        100,
        20
    ) == 80


def test_asset_turnover():
    assert calculate_asset_turnover(
        1000,
        500
    ) == 2


def test_asset_turnover_zero():
    assert calculate_asset_turnover(
        1000,
        0
    ) is None