# Budget Normalization

## Цель

Модуль разделяет четыре разных вопроса:

1. фактический/плановый дефицит;
2. предел дефицита по выбранной нормативной настройке;
3. разрыв нормализации;
4. возможность финансирования дефицита.

## Формулы

TotalRevenue = RevenueBase + Transfers

Deficit = max(Expenditure - TotalRevenue, 0)

DeficitRatio = Deficit / RevenueBase

BaseDeficitLimit = DeficitLimitRatio * RevenueBase

AllowedDeficit = BaseDeficitLimit + EligibleExceptions

NormalizationGap = max(Deficit - AllowedDeficit, 0)

RecurringBalance = RecurringRevenue - RecurringExpenditure

StructuralGap = max(-RecurringBalance, 0)

FinancingGap = max(Deficit - FinancingSources, 0)

DebtAfter = CurrentDebt + PlannedNetBorrowing

DebtRatio = DebtAfter / RevenueBase

DebtServiceRatio = DebtService / ExpenditureExSubventions

## Важное разделение

- Рост трансфертов уменьшает дефицит, но не увеличивает собственную revenue base для базового лимита.
- Eligible exceptions увеличивают допустимый размер дефицита, но сами по себе не улучшают структурный баланс.
- Заимствования финансируют дефицит, но не уменьшают сам дефицит.
- StructuralGap показывает устойчивый разрыв между регулярными доходами и регулярными расходами.
- FinancingGap показывает, покрыт ли дефицит указанными источниками финансирования.

## Нормативные параметры

Конфигурация находится в config/budget_normalization.yaml.

Research defaults на 2026-09-20:
- общий municipal deficit ratio: 10%;
- restricted ratio: 5%;
- general municipal debt ratio: 100%;
- restricted debt ratio: 50%;
- debt service ratio: 15%.

Применимый режим и специальные исключения 2026 года должны подтверждаться перед использованием результата как юридического заключения.

## Сценарии

Интерфейс строит Base и Scenario.

Параметры сценария:
- изменение revenue base;
- изменение трансфертов;
- изменение расходов;
- изменение verified eligible exceptions;
- изменение источников финансирования;
- изменение net borrowing.

Сценарий — инструмент анализа, а не автоматическая рекомендация по бюджету.


## Структура разрыва

MESM не пытается причинно разложить дефицит без данных по статьям бюджета.

Автоматически рассчитывается безопасная механическая структура:

- StructuralOverlap = min(StructuralGap, NormalizationGap)
- NonStructuralRemainder = NormalizationGap - StructuralOverlap
- RevenueBaseToClose = NormalizationGap / (1 + DeficitLimitRatio)
- TransfersToClose = NormalizationGap
- ExpenditureCutToClose = NormalizationGap

Это показывает масштаб требуемого изменения параметров, а не утверждает причину дефицита.

## Критерии

Каждый расчет получает независимые статусы:

- deficit: OK / BREACH
- recurring balance: OK / WATCH
- financing: OK / WATCH
- debt: OK / BREACH
- debt service: OK / BREACH

Так юридический/настроечный предел дефицита не смешивается со структурным и финансовым риском.

## Автосценарии

Три нейтральных механических сценария закрывают текущий NormalizationGap:

- Доходы — только рост revenue base;
- Расходы — только снижение expenditure;
- Сбалансированный — треть эффекта через revenue base, треть через transfers, треть через expenditure.

Это не рекомендации по бюджетной политике. Они показывают необходимый масштаб изменения.


## Реальный расчет Сургута 2025–2027

В baseline больше нет ручного ввода.

Источник: решение Думы города Сургута от 23.12.2024 № 713-VII ДГ.

MESM берет из официального документа:
- общий объем доходов;
- безвозмездные поступления;
- расходы;
- дефицит;
- источники финансирования;
- изменение остатков / продажу долей как проверенные специальные источники;
- верхний предел муниципального долга;
- расходы на обслуживание долга;
- структуру расходов по разделам бюджетной классификации.

RevenueBase = TotalRevenue - GratuitousReceipts.

RawNormalizationGap = max(Deficit - 10% * RevenueBase, 0).

AllowedDeficit = 10% * RevenueBase + EligibleExceptions.

NormalizationGap = max(Deficit - AllowedDeficit, 0).

Для 2025 и 2026 RawNormalizationGap положительный, но после учета прямо указанных в приложении 2 специальных источников итоговый NormalizationGap равен нулю. Для 2027 дефицит укладывается в базовый 10%-ный предел без дополнительных исключений.

Это расчет по официальным плановым данным, а не оценка на синтетике.
