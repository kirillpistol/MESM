from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from mesm.models.competition_challengers import prophet_expanding_forecast

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"processed"/"competition"/"surgut_all_2023_2024.csv"


def main() -> None:
    frame=pd.read_csv(DATA,encoding="utf-8-sig")[["period","value"]]
    forecasts,metrics=prophet_expanding_forecast(frame,holdout_year=2024)
    print("PROPHET_METRICS="+json.dumps(asdict(metrics),ensure_ascii=False))
    print(forecasts.to_csv(index=False))


if __name__=="__main__":
    main()
