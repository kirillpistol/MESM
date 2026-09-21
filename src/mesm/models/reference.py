"""Сборка признаков Reference-контура.

Финальный ReferenceScore пока не зашит в код: веса нужно калибровать только на
временном backtest, а не выбирать вручную после просмотра holdout.
"""
from __future__ import annotations

FEATURES = (
    "revision_magnitude",
    "execution_gap",
    "coverage_gap",
    "transfer_dependency",
    "budget_provision_change",
    "debt_burden",
    "article136_regime",
)

def reference_feature_vector(**kwargs) -> dict:
    return {name: kwargs.get(name) for name in FEATURES}
