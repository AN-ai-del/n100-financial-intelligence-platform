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