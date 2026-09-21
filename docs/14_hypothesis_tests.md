# Проверка гипотез и критерии успеха

Критерии ниже фиксируют development gates проекта. Это не универсальные нормативы для муниципальной экономики. Порог калибруется только на development-периоде и затем замораживается до финального holdout.

## H1. Forecasting

Гипотеза: challenger прогнозирует целевой ряд лучше простого baseline.

Основные метрики: MASE, WAPE, RMSE.

Критерии:
- MASE < 1.0;
- снижение forecast loss минимум на 5% против baseline;
- alpha = 0.05.

Тест:
- Diebold–Mariano при не менее 30 сопоставимых forecast errors и разумных предпосылках;
- иначе block bootstrap CI разницы loss.

WAPE < 0.15 не фиксируется как универсальный научный порог: он зависит от ряда и частоты. WAPE публикуется, но H1 принимается по относительному улучшению и MASE.

## H2. Early detection

Гипотеза: Predictive Layer дает полезный сигнал раньше официального Reference confirmation.

LeadTime = t_reference_confirmation - t_predictive_signal

Критерии:
- median LeadTime > 0 периодов;
- нижняя граница 95% bootstrap CI > 0;
- false alarms <= 0.10 на municipality-year.

Основной тест — bootstrap CI по matched events.

PR-AUC/ROC-AUC с CI публикуются как вторичная проверка discrimination. ROC-анализ сам по себе не проверяет «раньше», поэтому не заменяет LeadTime test.

## H3. Dual-contour value

Гипотеза: комбинация Reference + Predictive дает дополнительную ценность относительно каждого контура отдельно.

Reference active:
R_t = 1, если ReferenceState принадлежит {WARNING, BREAK_CONFIRMED}; иначе 0.

Predictive active:
P_t = 1, если PredictiveState принадлежит {WARNING, BREAK_CONFIRMED}; иначе 0.

Категориальный fusion:
F_t = 2 * R_t + P_t

| F | Dual State |
|---:|---|
| 0 | NORMAL |
| 1 | EARLY_WARNING |
| 2 | FISCAL_DIVERGENCE |
| 3 | SYSTEMIC_STRESS |

Для ranking-метрик используется development fusion score:

S_D = 1 - (1 - S_R) * (1 - S_P)

где S_R и S_P нормированы в [0,1]. Это deterministic noisy-OR score, а не автоматически калиброванная вероятность.

Критерии:
- delta PR-AUC > 0;
- delta Utility > 0;
- нижняя граница 95% bootstrap CI для improvement > 0.

Delta ROC-AUC — secondary metric. DeLong применяется только к ROC-AUC при достаточной независимости и минимум 20 positive + 20 negative событий; иначе основной вывод строится по bootstrap.

## H4. Economic utility

Гипотеза: экономическая ценность раннего сигнала превышает стоимость ложных тревог и эксплуатации.

NetEconomicEffect = Benefit_early - Cost_FP - Cost_FN - ModelCost

Критерии:
- NetEconomicEffect > 0;
- нижняя граница 95% bootstrap / Monte Carlo CI > 0;
- минимум 2000 resamples в confirmatory replay.

Historical replay и shadow period не дают права заявлять причинный эффект. Для causal claim нужен controlled deployment.

## H5. Adaptation

Гипотеза: адаптивная модель имеет меньший out-of-sample loss, чем frozen model, на одном temporal protocol.

Критерии:
- Loss_frozen - Loss_adaptive > 0;
- нижняя граница 95% bootstrap CI > 0.

CUSUM по коэффициентам используется только как trigger для возможной recalibration. Он не является статистическим тестом H5.

## Что считается confirmatory

Hypothesis result становится confirmatory только если:
- event labels независимы от тестируемого детектора;
- thresholds заморожены до holdout;
- as-of/publication semantics соблюдены;
- нет случайного train/test split;
- размер выборки достаточен для выбранного теста.

При недостаточной выборке результат маркируется exploratory.
