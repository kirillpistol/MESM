# MESM Project Maturity

Дата: 2026-09-20.

## Текущий уровень

MESM — reproducible research prototype, переходящий к pilot-grade analytical system.

Это уже выше уровня notebook/demo, потому что проект содержит:

- versioned data contracts and schemas;
- real public municipal fiscal panel;
- controlled intake and SHA-256 lineage;
- temporal backtest rules and as-of semantics;
- CUSUM/PELT/state machine;
- dual-contour specification;
- pre-registered hypothesis gates;
- synthetic power benchmark;
- external temporal layer;
- forecast-vs-actual benchmark;
- budget normalization and scenario engine;
- automated tests and CI;
- Windows build and dashboard.

## Что пока не позволяет назвать MESM production-ready

- нет полноценного реального high-frequency Predictive Layer;
- нет confirmatory event-level backtest на независимых labels;
- нет длительного shadow deployment;
- нормативные режимы бюджета требуют подтверждения для конкретного МО и года;
- нет production authentication, monitoring, SLA, incident process;
- нет независимого model validation / external audit.

## Уровни зрелости

1. Concept — пройден.
2. Notebook demo — пройден.
3. Reproducible research prototype — текущий подтвержденный уровень.
4. Pilot-grade analytical system — частично достигнут по архитектуре; нужен реальный predictive feed и shadow test.
5. Production decision-support — следующий большой уровень после data validation, event backtest, governance and operations.

Главный переход теперь не UI → UI, а evidence → pilot.
