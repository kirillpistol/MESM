from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import yaml

from mesm.ingest.sberindex_spending import read_sberindex_export
from mesm.models.competition_challengers import grow_hmao_forecast

ROOT=Path(__file__).resolve().parents[1]
NETWORK=ROOT/"config"/"hmao_training_network.yaml"


def main() -> None:
    parser=argparse.ArgumentParser(description="Run MESM Grow model on the public SberIndex export.")
    parser.add_argument("input",type=Path,help="Original SberIndex .csv or .csv.zip export")
    parser.add_argument("--network",type=Path,default=NETWORK)
    args=parser.parse_args()

    raw=read_sberindex_export(args.input)
    cfg=yaml.safe_load(args.network.read_text(encoding="utf-8"))
    forecasts,metrics=grow_hmao_forecast(
        raw,
        peer_oktmo_map=cfg["peer_oktmo_map"],
        target_oktmo=cfg["target_oktmo"],
    )
    print("GROW_METRICS="+json.dumps(asdict(metrics),ensure_ascii=False))
    print(forecasts.to_csv(index=False))


if __name__=="__main__":
    main()
