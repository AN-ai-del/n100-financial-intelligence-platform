from src.etl.normaliser import normalize_year, normalize_ticker


def test_normalize_year_with_integer():
    assert normalize_year(2024) == 2024


def test_normalize_year_with_string():
    assert normalize_year("2024") == 2024


def test_normalize_year_with_text():
    assert normalize_year("FY 2024") == 2024


def test_normalize_year_invalid():
    assert normalize_year("abc") is None


def test_normalize_ticker_basic():
    assert normalize_ticker("tcs") == "TCS"


def test_normalize_ticker_with_spaces():
    assert normalize_ticker("  infy  ") == "INFY"


def test_normalize_ticker_none():
    assert normalize_ticker(None) is None