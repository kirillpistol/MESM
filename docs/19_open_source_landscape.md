# Open-source landscape around MESM

Дата обзора: 2026-09-20.

Этот документ нужен не для заявления «MESM лучше», а чтобы зафиксировать соседние классы решений и точнее определить научный вопрос MESM.

## predicao-despesas-prefeitura

Repository:
https://github.com/Dealice2003/predicao-despesas-prefeitura

Публичный README описывает прогноз расходов Prefeitura de Salto Grande (SP):
- данные 2020–2024;
- 89,212 платежей;
- target: Valor Pago;
- ARIMA, Prophet, Random Forest;
- отдельное сравнение forecast vs actual за Jan–Jun 2025.

Сильная сторона для MESM как ориентира — явный Forecast vs Actual на реальных данных.

Отличие MESM: задача не ограничивается прогнозом уровня расходов. MESM исследует момент появления устойчивого structural shift и LeadTime относительно официального Reference confirmation.

## Municipal Fiscal Intelligence MCP

Repository:
https://github.com/apifyforge/municipal-fiscal-intelligence-mcp

Публичный README описывает hosted MCP workflow на американских федеральных источниках:
USAspending, FRED, BLS, FEMA, Data.gov, Nominatim и Congress.gov.

Выходы включают:
- Municipal Fiscal Stress Index;
- funding cliff;
- economic resilience;
- disaster exposure;
- peer comparison;
- composite credit rating.

Сильная сторона для MESM как ориентира — автоматическая интеграция нескольких внешних источников и структурированный risk output.

Отличие MESM: основной объект — temporal structural change detection, persistence, change-point confirmation и measured LeadTime, а не composite credit score.

## Fundamenta

Specification:
https://github.com/openarsenalspecs/Civic-Tech/blob/main/Fundamenta.md

Fundamenta описана как широкая financial-governance platform:
- accounting;
- budget management;
- anomaly detection;
- predictive budgeting;
- procurement;
- audit;
- transparency;
- AI recommendations.

Это более широкий target product scope. Публичный артефакт, который анализировался здесь, является module specification.

Отличие MESM: более узкий reproducible research framework с реальными public fiscal rows, state machine, change-point detectors, hypothesis gates, power simulation и CI tests.

## MayorGPT

Repository:
https://github.com/BrianPillmore/MayorGPT

Особенно релевантны:
- skills/finance/revenue-forecast-scenario/SKILL.md
- skills/finance/budget-variance-analysis/SKILL.md
- evals/financial-analysis-rubric.md

MayorGPT сильнее показывает user workflow: assumptions, scenarios, one-time vs recurring, plain-language memo and next steps.

Отличие MESM: вычислительное ядро строится вне LLM — deterministic metrics, temporal backtest, CUSUM/PELT, event evaluation and dual-contour fusion.

## Что MESM взял из сравнения

Не копируя архитектуру других проектов, MESM добавил три практики:

1. External Data Layer — чтобы внешние факторы подключались как versioned temporal data.
2. Forecast vs Actual benchmark — чтобы прогноз можно было проверять против факта.
3. Decision-ready summary — чтобы статистический результат переводился в понятный аналитический вывод с ограничениями.

## Текущая позиция MESM

Research question:

> Can a two-level model combining normative/fiscal municipal state and higher-frequency economic signals detect structural changes earlier than traditional reporting while maintaining an acceptable false-alarm rate?

Уникальность проекта должна доказываться экспериментом, а не сравнительной рекламной формулировкой.
