from src.etl.validator import add_failure


def test_add_failure():
    failures = []

    add_failure(
        failures,
        "DQ-01",
        "CRITICAL",
        "companies.xlsx",
        "Company Name",
        "Required column is missing"
    )

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-01"
    assert failures[0]["severity"] == "CRITICAL"
    assert failures[0]["file_name"] == "companies.xlsx"