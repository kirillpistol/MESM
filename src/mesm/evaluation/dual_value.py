from __future__ import annotations

from dataclasses import dataclass

from .metrics import average_precision, roc_auc


@dataclass(frozen=True)
class DualValueResult:
    roc_auc_reference: float
    roc_auc_predictive: float
    roc_auc_dual: float
    delta_roc_auc: float
    pr_auc_reference: float
    pr_auc_predictive: float
    pr_auc_dual: float
    delta_pr_auc: float


def compare_dual_value(y_true: list[int], reference_scores: list[float], predictive_scores: list[float], dual_scores: list[float]) -> DualValueResult:
    r_roc = roc_auc(y_true, reference_scores)
    p_roc = roc_auc(y_true, predictive_scores)
    d_roc = roc_auc(y_true, dual_scores)
    r_pr = average_precision(y_true, reference_scores)
    p_pr = average_precision(y_true, predictive_scores)
    d_pr = average_precision(y_true, dual_scores)
    return DualValueResult(
        r_roc,
        p_roc,
        d_roc,
        d_roc - max(r_roc, p_roc),
        r_pr,
        p_pr,
        d_pr,
        d_pr - max(r_pr, p_pr),
    )
