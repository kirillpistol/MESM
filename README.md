# MESM

**Municipal Economic Shock Monitor**

Я собираю MESM как исследовательский проект для мониторинга муниципальной экономики. Основная идея простая: сопоставлять официальный бюджетный контур с более частыми экономическими и потребительскими сигналами и проверять, можно ли заметить устойчивое изменение раньше следующей официальной отчетной точки.

Пилотный регион — Ханты-Мансийский автономный округ — Югра. Первый муниципальный кейс — Сургут.

MESM — это система поддержки решений. Проект не должен автоматически принимать бюджетные, кредитные или другие управленческие решения.

## Что уже есть

Сейчас собран и нормализуется реальный публичный бюджетный контур:

- исполнение бюджета за 2022–2025 годы;
- промежуточные срезы по муниципалитетам;
- перспективные финансовые планы 2026–2031;
- межбюджетные трансферты;
- реестры расходных обязательств;
- расчеты по статье 136 БК РФ;
- сопоставительные таблицы бюджетной классификации;
- муниципальные показатели качества управления финансами.

В код уже добавлены два реальных исторических набора для 22 верхнеуровневых муниципалитетов:

- Fiscal Reference Panel за 2023–2025 годы;
- Q3-срезы бюджетной обеспеченности за 2021 и 2023 годы.

Высокочастотный потребительский слой пока не подключен к реальным банковским данным. Для проверки pipeline и алгоритмов используются только данные, которые явно помечены как синтетические.

## Реальные данные и synthetic evidence

Сейчас в репозитории есть:

- 66 municipality-year строк Fiscal Reference Panel: 22 МО × 2023–2025;
- 44 municipality-period строки Budget Provision: 22 МО × два Q3-среза, 2021 и 2023.

Этого достаточно для описательного Reference-скрининга, проверки формул, peer-сравнения и data pipeline, но недостаточно для обучения сложной predictive ML-модели.

Разделение фиксируется так:

~~~text
REAL PUBLIC DATA
→ Reference features
→ fiscal screening / validation / peer context

SYNTHETIC DATA
→ detector mechanics
→ injected-shock power simulation
→ pipeline tests

FUTURE REAL HIGH-FREQUENCY DATA
→ Predictive model training
→ temporal backtest
→ confirmatory H1–H3
~~~

SyntheticPerformance не считается RealWorldPerformance.

## Как устроен MESM

```text
Источник
  ↓
manifest + SHA-256
  ↓
определение типа документа
  ↓
парсер конкретного семейства таблиц
  ↓
каноническая схема
  ↓
валидация и сверка
  ↓
признаки
  ↓
Reference / Predictive
  ↓
CUSUM / PELT / state machine
  ↓
Dual State
  ↓
backtest / stress test / decision support
```

Если структура исходного файла изменилась и обязательные поля больше не распознаются, данные не проходят дальше автоматически — источник уходит в `data/quarantine/`.

## Два контура

**Reference / Fiscal** — официальный бюджетный контур: план, уточнение, факт, трансферты, долговая нагрузка, бюджетная обеспеченность, расходные обязательства и другие публичные показатели.

**Predictive / Observed** — более частые сигналы: потребительская активность, топливо, инфляция, доходы, транспорт, занятость и допустимые агрегированные банковские показатели.

Я не привожу эти источники к одной частоте на уровне raw-данных. Бюджетные данные могут оставаться `QUARTER`, `HALF_YEAR`, `YEAR` или `EVENT`, а прогнозный слой — `WEEK` или `MONTH`.

## Состояния модели

Для каждого контура используется простая машина состояний:

```text
NORMAL → OBSERVE → WARNING → BREAK_CONFIRMED
```

Чтобы сигнал не переключался туда-сюда около одного порога, используется hysteresis: порог включения и порог снятия различаются. `BREAK_CONFIRMED` требует устойчивости сигнала и независимого подтверждения.

Комбинация двух контуров теперь специфицирована явно. Активным считается контур в WARNING или BREAK_CONFIRMED.

F = 2 * ReferenceActive + PredictiveActive

| F | Reference | Predictive | Итог MESM |
|---:|---|---|---|
| 0 | inactive | inactive | NORMAL |
| 1 | inactive | active | EARLY_WARNING |
| 2 | active | inactive | FISCAL_DIVERGENCE |
| 3 | active | active | SYSTEMIC_STRESS |

Для H3 continuous fusion score фиксирован как:

S_D = 1 - (1 - S_R) * (1 - S_P)

Оба score нормированы в [0,1]. Это development noisy-OR score, а не автоматически калиброванная вероятность.

## Критерии успеха гипотез

Критерии зафиксированы в config/evaluation.yaml и docs/14_hypothesis_tests.md.

- H1: MASE < 1.0, улучшение forecast loss ≥ 5% против baseline, alpha=0.05.
- H2: median LeadTime > 0 и нижняя граница 95% bootstrap CI > 0 при false alarms ≤ 0.10 на municipality-year.
- H3: delta PR-AUC > 0 и delta Utility > 0 с положительной нижней границей 95% bootstrap CI.
- H4: NetEconomicEffect > 0 и нижняя граница 95% bootstrap/Monte Carlo CI > 0.
- H5: adaptive OOS loss ниже frozen OOS loss с положительной нижней границей 95% CI.

Diebold–Mariano используется для H1 только при достаточном числе paired forecast errors. DeLong применяется только к ROC-AUC при достаточной структуре событий. CUSUM по коэффициентам — trigger для recalibration, а не самостоятельный тест H5.

## Проверка качества

Для прогнозов используются `WAPE`, `MASE`, `RMSE`. Для детекции — `PR-AUC`, `ROC-AUC`, precision/recall, число ложных тревог и `LeadTime`.

Backtest выполняется только по времени: expanding window, минимум 24 месяца истории, горизонт 1 месяц, последние 12 месяцев блокируются как финальный holdout. Данные, опубликованные позже даты прогноза, не должны попадать в расчет.

## Synthetic power benchmark

Для development CUSUM threshold откалиброван на bootstrap null-paths до path-level FPR≈0.10. Это не реальный результат Predictive Layer и не operational false alarms/entity-year.

Protocol: 60 synthetic residuals, 5000 null runs, 5000 power runs на ячейку, warmup=12, drift=0.5. Получено threshold=12.0, null path-FPR=0.0992.

| Shock, sigma | 1 period | 2 periods | 3 periods | 6 periods | Min duration при power ≥ 0.80 |
|---:|---:|---:|---:|---:|---:|
| 0.5 | 0.010 | 0.012 | 0.019 | 0.037 | >6 |
| 1.0 | 0.013 | 0.020 | 0.033 | 0.090 | >6 |
| 1.5 | 0.012 | 0.025 | 0.051 | 0.216 | >6 |
| 2.0 | 0.014 | 0.046 | 0.097 | 0.424 | >6 |
| 2.5 | 0.021 | 0.068 | 0.161 | 0.628 | >6 |
| 3.0 | 0.029 | 0.095 | 0.258 | 0.821 | 6 |
| 4.0 | 0.045 | 0.201 | 0.516 | 0.955 | 6 |

Полный protocol и ограничения: docs/17_power_simulation_results.md.

## Нормализация бюджета

В MESM добавлен отдельный расчетный контур для дефицита и сценариев нормализации.

Основные показатели:

~~~text
Deficit
DeficitRatio
AllowedDeficit
NormalizationGap
StructuralGap
FinancingGap
DebtRatio
DebtServiceRatio
~~~

Базовая логика:

~~~text
TotalRevenue = RevenueBase + Transfers
Deficit = max(Expenditure - TotalRevenue, 0)
AllowedDeficit = DeficitLimitRatio * RevenueBase + EligibleExceptions
NormalizationGap = max(Deficit - AllowedDeficit, 0)
~~~

Отдельно считаются структурный разрыв регулярного бюджета и разрыв финансирования. Заимствования не уменьшают сам дефицит: они относятся к источникам его финансирования.

Пороговые параметры вынесены в `config/budget_normalization.yaml` и должны подтверждаться для конкретного муниципалитета и бюджетного года.

### Декомпозиция и автосценарии

MESM отдельно показывает структурную часть разрыва, прочий остаток, критерии дефицита/финансирования/долга и три нейтральных сценария закрытия NormalizationGap: через доходы, расходы или сбалансированную комбинацию.

### Импорт проекта бюджета

Baseline бюджетного модуля теперь строится без ручного ввода. В репозитории подключены официальные параметры бюджета Сургута на 2025 год и плановый период 2026–2027 годов из решения Думы № 713-VII ДГ, включая доходы, безвозмездные поступления, расходы, дефицит, источники финансирования, специальные источники превышения базового лимита, верхний предел долга и обслуживание долга. Структура расходов берется из приложения 3 по разделам бюджетной классификации.

## External Data Layer и Forecast vs Actual

MESM теперь принимает отдельный канонический временной слой:

~~~text
period
geography_name
geography_level
variable
value
unit
source
publication_date
as_of_date
~~~

Через визуальный ввод можно загружать CPI, fuel, FX, oil, income, employment и другие разрешенные агрегаты.

Если по одной географии и переменной есть минимум 25 наблюдений, Shock Monitor строит expanding one-step **Forecast vs Actual benchmark**:

- Seasonal Naive;
- Linear Trend challenger;
- WAPE;
- RMSE;
- MASE.

Это не финальная ML-модель. Benchmark нужен, чтобы прозрачно проверить temporal pipeline до появления полноценного Predictive target.

В итоговом отчете появился **Decision-ready summary**: что изменилось, какая сила evidence, какие данные доступны, что можно интерпретировать и что требуется проверить дальше.

Для локального smoke-test в репозитории есть:

`data/synthetic/external_monthly_demo.csv`

Он синтетический и не используется как evidence качества MESM.

## Быстрый запуск

Нужен Python 3.11+.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -e ".[dev,yaml,research,changepoint]"

python scripts/build_fiscal_reference_panel.py
python -m pytest
python scripts/validate_project.py
python examples/reference_demo.py
python examples/state_machine_demo.py
```

Те же тесты автоматически запускаются в GitHub Actions после push и в pull request.

## Визуальный интерфейс

Для просмотра текущего Reference Layer есть Streamlit dashboard. Он не присваивает фиктивный `NORMAL/WARNING`: пока ReferenceScore не откалиброван, интерфейс показывает только реальные признаки и их динамику.

```bash
pip install -e ".[dashboard]"
streamlit run dashboard/app.py
```

На первом экране можно выбрать муниципалитет, посмотреть доходные отклонения, долю программных расходов, изменения бюджета, долговую нагрузку, официальный ранг и историю бюджетной обеспеченности.

## Структура

```text
config/      настройки модели, формул и парсеров
data/        manifest, обработанные, синтетические и карантинные данные
dashboard/   Streamlit-интерфейс
docs/        методология и описание решений
examples/    небольшие запускаемые примеры
schemas/     JSON Schema для канонических данных
scripts/     сборка и проверка датасетов
src/mesm/    основной код
tests/       автоматические тесты
```

## Что для меня важно в коде

Я стараюсь не превращать проект в «черный ящик» и не комментировать каждую очевидную строку. Комментарии оставляю там, где важно понять причину решения: почему запись ушла в quarantine, почему сигнал не снимается сразу, почему два похожих бюджетных показателя выбираются явно.

Для каждого результата должен сохраняться понятный путь назад:

```text
результат модели
→ признак
→ нормализованная запись
→ строка исходного документа
→ исходный файл
```

## Публичная и закрытая часть

В публичный репозиторий не должны попадать клиентские данные, сырые банковские транзакции, номера счетов, идентификаторы клиентов, секреты, токены и закрытые банковские пороги.

Банковская интеграция должна работать через отдельный адаптер, который преобразует разрешенные агрегированные данные в каноническую схему MESM.

## Статус

MESM сейчас является исследовательским прототипом. Уже есть воспроизводимый бюджетный Reference Layer, базовые формулы, state machine, temporal backtest, проверки утечки будущих данных, автоматические тесты и реальные публичные муниципальные данные.

Следующий основной этап — расширить историческую панель до максимально полного окна 2020–2026, восстановить `publication_date/as_of_date`, подключить внешние факторы и после этого переходить к полноценному backtest двух контуров.


## Shock Monitor и отчет

Интерфейс теперь разделяет реальные Reference-сигналы и демонстрацию механики детектора.

Во вкладке `Shock Monitor` показана цепочка:

```text
Forecast → Residual → Z-score → Persistence → Confirmation → State
```

Пока реального месячного Predictive Layer нет, CUSUM/PELT демонстрируются на явно помеченном стресс-сценарии. Эта симуляция не считается реальным сигналом по муниципалитету.

Во вкладке `Отчет` MESM формирует интерпретацию по выбранному муниципалитету и позволяет скачать HTML-отчет и CSV с Reference-данными. HTML выбран как переносимый формат без внешнего PDF-движка.


## Визуальный ввод данных

Во вкладке `Ввод данных` MESM показывает последовательность входов и объясняет, для какого расчета нужен каждый файл.

Загрузчик принимает канонические `.csv`, `.xlsx` и `.xlsm`:

1. **Reference Core** → доходное отклонение, доля программных расходов, изменения бюджета, долговая нагрузка.
2. **Quality Rankings** → официальный ранг и Article 136 flag.
3. **Budget Provision** → фактическая/расчетная БО и фискальный контекст.
4. **Predictive Layer** будет подключен следующим этапом.

Перед заменой активного набора MESM показывает preview, проверяет обязательные колонки и типовые ошибки. После подтверждения файл версионируется локально, получает SHA-256 и расчет автоматически выполняется заново.

Пользовательские загрузки сохраняются в `data/intake/` и исключены из GitHub.


## Автоматическое получение официального бюджета

Бюджетный baseline можно полностью пересобрать из официальных файлов администрации Сургута без ручного ввода сумм:

\`\`\`bash
python scripts/fetch_official_sources.py surgut_budget_adopted_2025_2027
python scripts/build_surgut_official_budget.py
python scripts/build_fiscal_reference_panel.py
\`\`\`

На Windows после первого запуска можно использовать \`UPDATE_OFFICIAL_DATA.bat\`.

MESM открывает официальную страницу, обнаруживает XLS/XLSX/DOCX, сохраняет исходные файлы в локальный \`data/raw/official/\`, записывает URL и SHA-256 в \`data/manifest/source_manifest.csv\` и только после этого пересобирает processed-таблицы. Бюджетные суммы в fetcher/parser не захардкожены.

## Control Room UI

Интерфейс использует отдельный UI-layer поверх Streamlit: левая навигация, системная строка состояния, KPI cards, status banners, budget normalization path и source lineage card. Расчетное ядро MESM отделено от визуального слоя, поэтому UI можно развивать без изменения формул и data contracts.


## Visual Analytics

Dashboard использует собственный визуальный слой MESM поверх Plotly: Reference trend, бюджетный waterfall, структуру расходов, Forecast vs Actual, Shock Monitor и динамику бюджетной обеспеченности. Цвета и подписи согласованы с Control Room UI, а графики отделены от расчетного ядра в `dashboard/charts.py`.

## Источники и pipeline

Отдельный экран `Источники` показывает настроенные официальные страницы, наличие локального raw-manifest, готовность processed budget snapshot и Fiscal Reference Panel. Raw-файлы по-прежнему не хранятся в Git; их URL и SHA-256 появляются локально после запуска `UPDATE_OFFICIAL_DATA.bat`.


## Competition Core

Для конкурсной задачи основной target-layer MESM — публичные муниципальные данные СберИндекса по безналичным потребительским расходам. Pipeline читает исходный `.csv.zip`, контролирует идентичность муниципалитетов, отправляет неоднозначные названия в quarantine и формирует canonical monthly panel для rolling-origin forecasting и shock detection.

Запуск:

```bash
python scripts/build_sberindex_spending.py path/to/sberindex_export.csv.zip
```

Основная конкурсная метрика прогнозирования — **MAE**. Random split запрещён; все модели сравниваются по времени.


## Географическая идентичность: ОКТМО

ОКТМО является единственным primary geographic key для model-ready муниципальных данных MESM. Название муниципалитета используется только для отображения и source aliases.

```text
официальный ОКТМО Росстата
        ↓
municipality_registry
        ↓
source-specific aliases
        ↓
СберИндекс / Росстат / бюджет / погода / новости
        ↓
OKTMO × period × feature
```

Модель не принимает строку без подтвержденного 8-значного муниципального ОКТМО. Неоднозначные и неразрешенные названия уходят в quarantine/review. Fuzzy matching не может автоматически присвоить код.

Для СберИндекса:

```bash
python scripts/build_sberindex_spending.py path/to/export.csv.zip
```

использует `data/reference/municipality_registry.csv` и `data/reference/sberindex_municipality_aliases.csv`.


## Конкурсный географический scope

Конкурсный кейс MESM сознательно ограничен:

- **Сургут, ОКТМО 71876000** — главный объект прогнозирования, shock detection и экономической интерпретации;
- **ХМАО — Югра** — максимальная обучающая и peer-сетка;
- остальные муниципалитеты России не входят в основной model-ready scope;
- полный исходный экспорт СберИндекса сохраняется только как immutable raw source.

Для фактической проверки качества основной holdout — **2024 год**. Наблюдения 2023 года дают историческую базу, а периоды после конца доступных фактических данных могут показываться только как forecast/context, пока не появятся actuals.

Фильтрация зафиксирована в `config/competition_scope.yaml` и `mesm.data.competition_scope`.


## Первый конкурсный benchmark

До Prophet и ML-моделей MESM фиксирует простые baselines на том же temporal holdout:

```bash
python scripts/run_surgut_baselines.py
```

Протокол: 2023 — начальная история, 2024 — expanding one-step OOS для Сургута (ОКТМО 71876000). Сравниваются Last Value, Seasonal Naive 12 и Linear Trend. Основная метрика — MAE; R², WAPE, RMSE и MASE сохраняются как дополнительные.

Feature matrix для следующих challenger-моделей строится в `mesm.features.competition_matrix`. Все лаги и rolling-признаки вычисляются только из значений, доступных до прогнозируемого месяца.


## Prophet + Grow

Второй конкурсный цикл добавляет две модели на том же holdout 2024:

- Prophet — локальный expanding one-step benchmark по Сургуту;
- Grow — модель роста MESM; глобальная региональная модель, обучающаяся на безопасной source-local peer-сетке ХМАО и прогнозирующая логарифмический месячный рост.

Competition dependencies:

```bash
pip install -e ".[competition]"
```

Prophet запускается на компактном публичном фактическом ряде
`data/processed/competition/surgut_all_2023_2024.csv`.

Grow запускается на исходной выгрузке:

```bash
python scripts/run_competition_tournament.py path/to/sberindex_export.csv.zip
```

Текущий benchmark на 2024:

- Prophet: **MAE 2404.56 ₽**, R² = **0.330**;
- Linear Trend: **MAE 2391.05 ₽**, R² = **0.334**;
- Grow (OKTMO network): **MAE 2067.48 ₽**, R² = **0.347**.

Grow снижает MAE примерно на **14.0% относительно Prophet** на тех же 12 OOS-месяцах. В обучающей сетке 19 безопасных рядов ХМАО уже переведены на 8-значные ОКТМО; три неоднозначных названия СберИндекса исключены fail-closed. Prophet результат воспроизводится отдельным GitHub Actions workflow. Финальный статус Grow остаётся development до row-level сверки этих кодов с текущим CSV Росстата.

В Control Room добавлена вкладка **«Модели»** с текущим tournament и gate до финального champion.


## Shock Tournament

После forecast tournament residual текущего Grow challenger используется
только как эмпирическая база масштаба шума. На bootstrap-paths MESM сравнивает:

- CUSUM — online detector;
- Page-Hinkley — второй online detector;
- PELT — offline confirmation/localization.

Все online thresholds и PELT penalty калибруются под одинаковый target null-path
false positive rate 10%. Benchmark отдельно считает краткие `TRANSIENT_SHOCK` (1–3 месяца) и устойчивые
`REGIME_SHIFT` (6–12 месяцев), причём для роста и падения потребления. Synthetic
injection не выдается за реальное экономическое событие.

```bash
python scripts/run_shock_tournament.py
```


## Control Room visual refresh

Dashboard переработан в формат аналитического control room:

- competition hero на главном экране;
- явный акцент на Сургут / ОКТМО / Grow vs Prophet;
- Actual vs Forecast для основных моделей;
- отдельный visual benchmark CUSUM / Page-Hinkley / PELT;
- calibration chart с единым false-alarm budget;
- более плотная институциональная визуальная иерархия без декоративного перегруза.


## Упрощённый интерфейс для обсуждения с администрацией

Интерфейс MESM сознательно упрощён: стандартные системные шрифты, минимум декоративных эффектов и русский язык во всех пользовательских блоках. На первом экране логика сведена к трём этапам: **Данные → Прогноз → Изменение**. Английские обозначения оставлены только там, где это собственные названия методов и метрик: MAE, R², Grow, Prophet, CUSUM, Page-Hinkley, PELT, OKTMO.
