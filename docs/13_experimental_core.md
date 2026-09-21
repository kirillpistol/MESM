# Экспериментальное ядро MESM

## Состояние одного контура

Каждый контур проходит через NORMAL → OBSERVE → WARNING → BREAK_CONFIRMED.

Сигнал включается по верхнему порогу и снимается только после устойчивого выхода ниже отдельного нижнего порога. BREAK_CONFIRMED требует persistence и независимого подтверждения.

## Dual-contour fusion

Активным считается контур в WARNING или BREAK_CONFIRMED.

R_t = 1[Reference active]
P_t = 1[Predictive active]

Категориальный код fusion:

F_t = 2 * R_t + P_t

| Reference | Predictive | F | MESM |
|---|---|---:|---|
| inactive | inactive | 0 | NORMAL |
| inactive | active | 1 | EARLY_WARNING |
| active | inactive | 2 | FISCAL_DIVERGENCE |
| active | active | 3 | SYSTEMIC_STRESS |

Для H3 нужен и continuous score. Development default:

S_D = 1 - (1 - S_R) * (1 - S_P)

где S_R,S_P находятся в [0,1]. Это симметричный monotonic noisy-OR score без обучаемых весов. Он используется как ranking score для PR-AUC/ROC-AUC, но не объявляется вероятностью без отдельной calibration.

Rule-based fusion намеренно прост: его можно воспроизвести, проверить и сравнить с будущим stacking/Bayesian challenger.

## Event registry

Для оценки используется отдельный event_registry. Label может быть external_event, realized_outcome или fiscal_confirmation.

Бюджетное уточнение может подтверждать LeadTime, но не должно автоматически быть независимым label для оценки того же Fiscal contour. Для этого есть evaluation_eligible и circularity_note.

## Dual-model value

Основная метрика для редких событий — PR-AUC. Дополнительно используются ROC-AUC, precision, recall, false alarms per municipality-year и LeadTime при фиксированном false-alarm budget.

Delta PR-AUC = PR-AUC(R+P) - max(PR-AUC(R), PR-AUC(P))

## Temporal backtest

Predictive Layer по умолчанию проверяется на месячной частоте: expanding window, минимум 24 месяца обучения, горизонт 1 месяц, последние 12 месяцев — закрытый holdout. Random split запрещен, as-of semantics обязательна.

## YTD

CUSUM/PELT не применяются напрямую к несовместимым накопительным бюджетным срезам. Разность YTD считается только при совпадении муниципалитета, показателя, методики, классификации, scope и единицы измерения.

## Power analysis

Для оценки чувствительности в residuals добавляются контролируемые шоки. Threshold сначала калибруется на null-paths до target path-level FPR=0.10, затем измеряется detection power.

Synthetic power analysis тестирует механику детектора и не является доказательством качества на реальных муниципальных данных.
