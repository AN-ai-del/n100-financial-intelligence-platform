from src.analytics.cagr import (
    calculate_cagr,
    revenue_cagr,
    pat_cagr,
    eps_cagr,
)


def test_normal_cagr():

    value, flag = calculate_cagr(
        100,
        200,
        5
    )

    assert flag == "OK"


def test_zero_base():

    value, flag = calculate_cagr(
        0,
        200,
        5
    )

    assert flag == "ZERO_BASE"


def test_turnaround():

    value, flag = calculate_cagr(
        -100,
        200,
        5
    )

    assert flag == "TURNAROUND"


def test_decline():

    value, flag = calculate_cagr(
        100,
        -200,
        5
    )

    assert flag == "DECLINE_TO_LOSS"


def test_both_negative():

    value, flag = calculate_cagr(
        -100,
        -200,
        5
    )

    assert flag == "BOTH_NEGATIVE"


def test_invalid_years():

    value, flag = calculate_cagr(
        100,
        200,
        0
    )

    assert flag == "INVALID_YEARS"


def test_revenue():

    value, flag = revenue_cagr(
        100,
        200,
        5
    )

    assert flag == "OK"


def test_pat():

    value, flag = pat_cagr(
        50,
        100,
        5
    )

    assert flag == "OK"


def test_eps():

    value, flag = eps_cagr(
        10,
        20,
        5
    )

    assert flag == "OK"


def test_return_type():

    value, flag = calculate_cagr(
        100,
        200,
        5
    )

    assert isinstance(flag, str)