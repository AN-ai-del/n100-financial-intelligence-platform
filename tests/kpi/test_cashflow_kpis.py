from src.analytics.cashflow_kpis import (
    calculate_free_cash_flow,
    calculate_cfo_quality_score,
    calculate_capex_intensity,
    calculate_fcf_conversion_rate,
    classify_capital_allocation,
    build_capital_allocation_record,
)


def test_free_cash_flow_positive():
    assert calculate_free_cash_flow(100, -40) == 60


def test_free_cash_flow_negative_allowed():
    assert calculate_free_cash_flow(50, -100) == -50


def test_cfo_quality_high():
    ratio, label = calculate_cfo_quality_score(120, 100)
    assert ratio == 1.2
    assert label == "High Quality"


def test_cfo_quality_moderate():
    ratio, label = calculate_cfo_quality_score(70, 100)
    assert ratio == 0.7
    assert label == "Moderate"


def test_cfo_quality_accrual_risk():
    ratio, label = calculate_cfo_quality_score(30, 100)
    assert ratio == 0.3
    assert label == "Accrual Risk"


def test_cfo_quality_pat_zero():
    ratio, label = calculate_cfo_quality_score(100, 0)
    assert ratio is None
    assert label == "NOT_AVAILABLE"


def test_capex_asset_light():
    value, label = calculate_capex_intensity(-20, 1000)
    assert value == 2
    assert label == "Asset Light"


def test_capex_moderate():
    value, label = calculate_capex_intensity(-50, 1000)
    assert value == 5
    assert label == "Moderate"


def test_capex_capital_intensive():
    value, label = calculate_capex_intensity(-100, 1000)
    assert value == 10
    assert label == "Capital Intensive"


def test_fcf_conversion_rate():
    assert calculate_fcf_conversion_rate(50, 100) == 50


def test_fcf_conversion_zero_operating_profit():
    assert calculate_fcf_conversion_rate(50, 0) is None


def test_capital_allocation_reinvestor():
    assert classify_capital_allocation(100, -50, -20) == "Reinvestor"


def test_capital_allocation_shareholder_returns():
    assert classify_capital_allocation(
        100,
        -50,
        -20,
        "High Quality"
    ) == "Shareholder Returns"


def test_capital_allocation_liquidating_assets():
    assert classify_capital_allocation(100, 50, -20) == "Liquidating Assets"


def test_capital_allocation_distress_signal():
    assert classify_capital_allocation(-100, 50, 20) == "Distress Signal"


def test_capital_allocation_growth_funded_by_debt():
    assert classify_capital_allocation(-100, -50, 20) == "Growth Funded by Debt"


def test_capital_allocation_cash_accumulator():
    assert classify_capital_allocation(100, 50, 20) == "Cash Accumulator"


def test_capital_allocation_pre_revenue():
    assert classify_capital_allocation(-100, -50, -20) == "Pre-Revenue"


def test_capital_allocation_mixed():
    assert classify_capital_allocation(100, -50, 20) == "Mixed"


def test_build_capital_allocation_record():
    record = build_capital_allocation_record(
        company_id=1,
        year=2024,
        cfo=100,
        cfi=-50,
        cff=-20,
        cfo_quality_label="High Quality"
    )

    assert record["company_id"] == 1
    assert record["year"] == 2024
    assert record["cfo_sign"] == "+"
    assert record["cfi_sign"] == "-"
    assert record["cff_sign"] == "-"
    assert record["pattern_label"] == "Shareholder Returns"