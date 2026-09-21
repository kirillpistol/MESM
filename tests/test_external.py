import pandas as pd

from mesm.predictive.external import coverage, extract_series


def sample():
    return pd.DataFrame([
        {
            "period": "2025-01-01",
            "geography_name": "ХМАО",
            "geography_level": "REGION",
            "variable": "cpi",
            "value": 100.0,
            "unit": "index",
            "source": "test",
            "publication_date": "2025-02-10",
            "as_of_date": "2025-02-10",
        },
        {
            "period": "2025-02-01",
            "geography_name": "ХМАО",
            "geography_level": "REGION",
            "variable": "cpi",
            "value": 101.0,
            "unit": "index",
            "source": "test",
            "publication_date": "2025-03-10",
            "as_of_date": "2025-03-10",
        },
    ])


def test_external_coverage():
    result = coverage(sample())
    assert result.rows == 2
    assert result.geographies == 1
    assert result.variables == 1


def test_extract_series():
    result = extract_series(sample(), "ХМАО", "cpi")
    assert len(result) == 2
    assert float(result.iloc[-1]["value"]) == 101.0
