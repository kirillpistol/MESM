from __future__ import annotations

from .state_machine import ContourState

ACTIVE_STATES = {ContourState.WARNING.value, ContourState.BREAK_CONFIRMED.value}

DUAL_STATE_BY_CODE = {
    0: "NORMAL",
    1: "EARLY_WARNING",
    2: "FISCAL_DIVERGENCE",
    3: "SYSTEMIC_STRESS",
}


def _is_active(state: str | ContourState | bool) -> bool:
    if isinstance(state, bool):
        return state
    value = state.value if isinstance(state, ContourState) else str(state)
    return value in ACTIVE_STATES


def dual_state_code(
    reference_state: str | ContourState | bool,
    predictive_state: str | ContourState | bool,
) -> int:
    """Код fusion: F = 2*R + P, где активный контур равен 1."""
    reference_active = int(_is_active(reference_state))
    predictive_active = int(_is_active(predictive_state))
    return 2 * reference_active + predictive_active


def dual_state(
    reference_state: str | ContourState | bool,
    predictive_state: str | ContourState | bool,
) -> str:
    """Rule-based fusion двух контуров.

    WARNING и BREAK_CONFIRMED считаются активными. NORMAL и OBSERVE — неактивными.
    """
    return DUAL_STATE_BY_CODE[dual_state_code(reference_state, predictive_state)]


def dual_fusion_score(reference_score: float, predictive_score: float) -> float:
    """Development-score для H3.

    Входы нормированы в [0, 1]. Noisy-OR используется как монотонный fusion score,
    а не как автоматически калиброванная вероятность события.
    """
    r = float(reference_score)
    p = float(predictive_score)
    if not 0.0 <= r <= 1.0 or not 0.0 <= p <= 1.0:
        raise ValueError("reference_score и predictive_score должны быть в диапазоне [0, 1]")
    return 1.0 - (1.0 - r) * (1.0 - p)


def probability_state(probabilities: dict[str, float], min_margin: float = 0.10) -> str:
    if not probabilities:
        return "UNCERTAIN"
    ordered = sorted(probabilities.items(), key=lambda kv: kv[1], reverse=True)
    if len(ordered) > 1 and ordered[0][1] - ordered[1][1] < min_margin:
        return "UNCERTAIN"
    return ordered[0][0]
