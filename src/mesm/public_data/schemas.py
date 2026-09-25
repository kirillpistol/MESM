from __future__ import annotations

from datetime import date
import pandas as pd
import pandera.pandas as pa

CATEGORIES = ["all", "food", "transport", "import_dependent"]

RAW = pa.DataFrameSchema({
    "oktmo": pa.Column(str, pa.Check.str_matches(r"^[0-9]{8}([0-9]{3})?$")),
    "period": pa.Column(str),
    "indicator": pa.Column(str),
    "value": pa.Column(float, pa.Check.ge(0)),
    "unit": pa.Column(str),
}, strict=False, coerce=True)

CANONICAL = pa.DataFrameSchema({
    "oktmo": pa.Column(str, pa.Check.str_matches(r"^[0-9]{8}([0-9]{3})?$")),
    "period": pa.Column(pa.DateTime),
    "category": pa.Column(str, pa.Check.isin(CATEGORIES)),
    "indicator": pa.Column(str),
    "value": pa.Column(float, pa.Check.ge(0)),
    "unit": pa.Column(str),
    "source": pa.Column(str),
    "available_at": pa.Column(pa.DateTime),
    "is_estimated": pa.Column(bool),
}, checks=[
    pa.Check(lambda df: (df.available_at >= df.period).all(), error="release precedes observation"),
], unique=["source", "oktmo", "period", "category", "indicator"], strict=True, coerce=True)

FEATURES = pa.DataFrameSchema({
    "oktmo": pa.Column(str, pa.Check.str_matches(r"^[0-9]{8}([0-9]{3})?$")),
    "prediction_date": pa.Column(pa.DateTime),
    "available_at": pa.Column(pa.DateTime),
    "category": pa.Column(str, pa.Check.isin(CATEGORIES)),
    "indicator": pa.Column(str),
    "value": pa.Column(float, pa.Check.ge(0)),
    "source": pa.Column(str),
}, checks=[pa.Check(lambda df: (df.available_at <= df.prediction_date).all(), error="future data leakage")],
    unique=["oktmo", "prediction_date", "category", "indicator", "source"], strict=True, coerce=True)


def validate_raw(frame: pd.DataFrame) -> pd.DataFrame:
    return RAW.validate(frame, lazy=True)


def validate_canonical(frame: pd.DataFrame) -> pd.DataFrame:
    return CANONICAL.validate(frame, lazy=True)


def features_as_of(frame: pd.DataFrame, prediction_date: str | date) -> pd.DataFrame:
    canonical = validate_canonical(frame)
    when = pd.Timestamp(prediction_date)
    eligible = canonical.loc[canonical.available_at <= when].copy()
    eligible["prediction_date"] = when
    return FEATURES.validate(eligible[["oktmo", "prediction_date", "available_at", "category", "indicator", "value", "source"]], lazy=True)
