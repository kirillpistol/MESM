"""Competition challenger models: Prophet and Grow."""
from __future__ import annotations

from dataclasses import dataclass
from math import cos, exp, log, pi, sin, sqrt
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ChallengerMetrics:
    model: str
    observations: int
    mae: float
    r2: float
    wape: float
    rmse: float
    mase: float


def score_forecast(
    actual: Iterable[float],
    predicted: Iterable[float],
    *,
    insample: Iterable[float],
) -> ChallengerMetrics:
    a=np.asarray(list(actual),dtype=float)
    p=np.asarray(list(predicted),dtype=float)
    hist=np.asarray(list(insample),dtype=float)
    if len(a)==0 or len(a)!=len(p):
        raise ValueError("actual/predicted must have the same non-zero length")
    err=a-p
    mae=float(np.mean(np.abs(err)))
    rmse=float(sqrt(float(np.mean(err**2))))
    mean=float(np.mean(a))
    sst=float(np.sum((a-mean)**2))
    r2=float(1.0-float(np.sum(err**2))/sst) if sst else float("nan")
    denom=float(np.sum(np.abs(a)))
    wape=float(np.sum(np.abs(err))/denom) if denom else float("nan")
    scale=float(np.mean(np.abs(np.diff(hist)))) if len(hist)>1 else 0.0
    mase=float(mae/scale) if scale else float("nan")
    return ChallengerMetrics("",len(a),mae,r2,wape,rmse,mase)


def prophet_expanding_forecast(
    series: pd.DataFrame,
    *,
    holdout_year: int=2024,
    changepoint_prior_scale: float=0.05,
) -> tuple[pd.DataFrame, ChallengerMetrics]:
    try:
        from prophet import Prophet
    except ImportError as exc:
        raise RuntimeError(
            'Prophet is not installed. Install MESM with: pip install -e ".[competition]"'
        ) from exc

    frame=series[["period","value"]].copy()
    frame["period"]=pd.to_datetime(frame["period"],errors="raise")
    frame["value"]=pd.to_numeric(frame["value"],errors="raise").astype(float)
    frame=frame.sort_values("period").drop_duplicates("period",keep="last").reset_index(drop=True)

    rows=[]
    for _,row in frame[frame["period"].dt.year==holdout_year].iterrows():
        period=row["period"]
        train=frame[frame["period"]<period].copy()
        if len(train)<12:
            raise ValueError("Prophet benchmark requires at least 12 prior monthly observations.")
        fit=train.rename(columns={"period":"ds","value":"y"})[["ds","y"]]
        model=Prophet(
            yearly_seasonality="auto",
            weekly_seasonality=False,
            daily_seasonality=False,
            seasonality_mode="additive",
            changepoint_prior_scale=changepoint_prior_scale,
        )
        model.fit(fit)
        yhat=float(model.predict(pd.DataFrame({"ds":[period]}))["yhat"].iloc[0])
        rows.append({"period":period,"actual":float(row["value"]),"prophet":yhat})

    forecasts=pd.DataFrame(rows)
    insample=frame[frame["period"].dt.year<holdout_year]["value"].astype(float).tolist()
    scored=score_forecast(
        forecasts["actual"],
        forecasts["prophet"],
        insample=insample,
    )
    metrics=ChallengerMetrics(
        model="Prophet",
        observations=scored.observations,
        mae=scored.mae,
        r2=scored.r2,
        wape=scored.wape,
        rmse=scored.rmse,
        mase=scored.mase,
    )
    return forecasts,metrics


def prepare_hmao_source_panel(
    frame: pd.DataFrame,
    *,
    peer_oktmo_map: dict[str, str],
) -> pd.DataFrame:
    required={"period","value","category_15","mo"}
    missing=required-set(frame.columns)
    if missing:
        raise ValueError("SberIndex source panel missing columns: "+", ".join(sorted(missing)))

    normalized_map={str(name).strip(): str(oktmo).strip() for name,oktmo in peer_oktmo_map.items()}
    if len(set(normalized_map.values())) != len(normalized_map):
        raise ValueError("Each HMAO training peer must map to a unique OKTMO.")
    data=frame[frame["mo"].astype(str).str.strip().isin(normalized_map)].copy()
    data["period"]=pd.to_datetime(data["period"],errors="raise")
    data["value"]=pd.to_numeric(data["value"],errors="raise").astype(float)
    data["mo"]=data["mo"].astype(str).str.strip()
    data["category_15"]=data["category_15"].astype(str).str.strip()
    data["oktmo"]=data["mo"].map(normalized_map)

    counts=data.groupby(["mo","period","category_15"]).size()
    collisions=counts[counts>1]
    if not collisions.empty:
        names=sorted(set(index[0] for index in collisions.index))
        raise ValueError(
            "HMAO source-local training aliases are not unique in the export: "
            + ", ".join(names[:10])
        )
    if data["oktmo"].isna().any():
        raise ValueError("Unresolved HMAO peer OKTMO after source mapping.")
    return data.sort_values(["oktmo","category_15","period"]).reset_index(drop=True)


def _grow_features(panel: pd.DataFrame) -> tuple[pd.DataFrame,list[str]]:
    data=panel.copy()
    keys=["oktmo","category_15"]
    data["month"]=data["period"].dt.month.astype(int)
    data["month_sin"]=data["month"].map(lambda m: sin(2*pi*m/12))
    data["month_cos"]=data["month"].map(lambda m: cos(2*pi*m/12))
    grouped=data.groupby(keys,sort=False)["value"]
    for lag in (1,2,3,6,12):
        data[f"lag_{lag}"]=grouped.shift(lag)
    shifted=grouped.shift(1)
    for window in (3,6):
        data[f"rolling_mean_{window}"]=(
            shifted.groupby([data["oktmo"],data["category_15"]])
            .transform(lambda s:s.rolling(window,min_periods=1).mean())
        )
        data[f"rolling_std_{window}"]=(
            shifted.groupby([data["oktmo"],data["category_15"]])
            .transform(lambda s:s.rolling(window,min_periods=2).std())
        )
    data["lag1_delta"]=data["lag_1"]-data["lag_2"]
    data["lag1_pct"]=data["lag_1"]/data["lag_2"].replace(0,np.nan)-1
    data["yoy_lag"]=data["lag_1"]/data["lag_12"].replace(0,np.nan)-1
    features=[
        "oktmo","category_15","month","month_sin","month_cos",
        "lag_1","lag_2","lag_3","lag_6","lag_12",
        "rolling_mean_3","rolling_std_3","rolling_mean_6","rolling_std_6",
        "lag1_delta","lag1_pct","yoy_lag",
    ]
    return data,features


def grow_hmao_forecast(
    raw_frame: pd.DataFrame,
    *,
    peer_oktmo_map: dict[str, str],
    target_oktmo: str="71876000",
    target_category: str="Все категории",
    holdout_year: int=2024,
    iterations: int=120,
    depth: int=4,
    learning_rate: float=0.05,
    l2_leaf_reg: float=8.0,
    random_seed: int=42,
) -> tuple[pd.DataFrame, ChallengerMetrics]:
    try:
        from catboost import CatBoostRegressor as GrowRegressor
    except ImportError as exc:
        raise RuntimeError(
            'Grow dependency is not installed. Install MESM with: pip install -e ".[competition]"'
        ) from exc

    panel=prepare_hmao_source_panel(raw_frame,peer_oktmo_map=peer_oktmo_map)
    data,features=_grow_features(panel)
    target=data[
        (data["oktmo"]==str(target_oktmo))
        & (data["category_15"]==target_category)
    ].copy()
    months=target[target["period"].dt.year==holdout_year]["period"].tolist()
    if not months:
        raise ValueError("No target holdout observations found.")

    rows=[]
    for period in months:
        train=data[data["period"]<period].copy()
        test=data[
            (data["period"]==period)
            & (data["oktmo"]==str(target_oktmo))
            & (data["category_15"]==target_category)
        ].copy()
        growth=np.log(train["value"]/train["lag_1"])
        ok=np.isfinite(growth)
        train=train.loc[ok].copy()
        growth=growth.loc[ok]
        model=GrowRegressor(
            iterations=iterations,
            depth=depth,
            learning_rate=learning_rate,
            l2_leaf_reg=l2_leaf_reg,
            loss_function="MAE",
            verbose=False,
            random_seed=random_seed,
            allow_writing_files=False,
            thread_count=2,
        )
        model.fit(train[features],growth,cat_features=[0,1])
        predicted_growth=float(model.predict(test[features])[0])
        lag1=float(test["lag_1"].iloc[0])
        prediction=lag1*exp(predicted_growth)
        rows.append({
            "period":period,
            "actual":float(test["value"].iloc[0]),
            "grow_prediction":prediction,
        })

    forecasts=pd.DataFrame(rows)
    hist=target[target["period"].dt.year<holdout_year]["value"].astype(float).tolist()
    scored=score_forecast(
        forecasts["actual"],
        forecasts["grow_prediction"],
        insample=hist,
    )
    metrics=ChallengerMetrics(
        model="Grow",
        observations=scored.observations,
        mae=scored.mae,
        r2=scored.r2,
        wape=scored.wape,
        rmse=scored.rmse,
        mase=scored.mase,
    )
    return forecasts,metrics
