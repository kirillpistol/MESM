"""Машина состояний одного контура MESM.

Пороговые значения в репозитории служат стартовыми настройками. Перед финальным
holdout их нужно откалибровать на development-периоде и зафиксировать.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ContourState(str, Enum):
    NORMAL = "NORMAL"
    OBSERVE = "OBSERVE"
    WARNING = "WARNING"
    BREAK_CONFIRMED = "BREAK_CONFIRMED"


@dataclass(frozen=True)
class StateMachineConfig:
    on_threshold: float = 2.0
    off_threshold: float = 1.0
    k_on: int = 2
    k_off: int = 2
    break_persistence: int = 3
    min_confirmations: int = 2

    def __post_init__(self) -> None:
        if not self.off_threshold < self.on_threshold:
            raise ValueError("off_threshold должен быть ниже on_threshold")
        if min(self.k_on, self.k_off, self.break_persistence, self.min_confirmations) < 1:
            raise ValueError("параметры persistence/confirmation должны быть >= 1")
        if self.break_persistence < self.k_on:
            raise ValueError("break_persistence должен быть >= k_on")


@dataclass(frozen=True)
class StateUpdate:
    state: ContourState
    score: float
    above_streak: int
    below_streak: int
    confirmations: int
    reason: str


class HysteresisStateMachine:
    """Переходы NORMAL → OBSERVE → WARNING → BREAK_CONFIRMED.

    Hysteresis не дает сигналу дрожать около одного порога. Для BREAK_CONFIRMED
    нужна устойчивость и подтверждение независимыми детекторами.
    """

    def __init__(self, config: StateMachineConfig | None = None) -> None:
        self.config = config or StateMachineConfig()
        self.state = ContourState.NORMAL
        self.above_streak = 0
        self.below_streak = 0

    def reset(self) -> None:
        self.state = ContourState.NORMAL
        self.above_streak = 0
        self.below_streak = 0

    def update(self, score: float, confirmations: int = 0) -> StateUpdate:
        c = self.config
        confirmations = max(0, int(confirmations))

        if score >= c.on_threshold:
            self.above_streak += 1
            self.below_streak = 0

            if self.state == ContourState.NORMAL:
                self.state = ContourState.OBSERVE

            if self.above_streak >= c.k_on and self.state in {
                ContourState.NORMAL,
                ContourState.OBSERVE,
            }:
                self.state = ContourState.WARNING

            if (
                self.above_streak >= c.break_persistence
                and confirmations >= c.min_confirmations
            ):
                self.state = ContourState.BREAK_CONFIRMED
                reason = "устойчивый сигнал подтвержден независимыми детекторами"
            elif self.state == ContourState.WARNING:
                reason = "устойчивое превышение порога"
            else:
                reason = "кандидат на аномалию, продолжаем наблюдение"

        elif score < c.off_threshold:
            self.below_streak += 1
            self.above_streak = 0
            if self.below_streak >= c.k_off:
                self.state = ContourState.NORMAL
                reason = "сигнал снят после выполнения hysteresis rule"
            else:
                reason = "ниже порога снятия, ждем подтверждения по времени"
        else:
            self.below_streak = 0
            # WARNING/BREAK держим до полноценного выполнения правила снятия сигнала.
            if self.state == ContourState.NORMAL:
                reason = "внутри hysteresis band"
            elif self.state == ContourState.OBSERVE:
                reason = "кандидат остается внутри hysteresis band"
            else:
                reason = "активный сигнал сохраняется внутри hysteresis band"

        return StateUpdate(
            state=self.state,
            score=float(score),
            above_streak=self.above_streak,
            below_streak=self.below_streak,
            confirmations=confirmations,
            reason=reason,
        )
