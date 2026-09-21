# Competition Core: СберИндекс → Forecast → Shock

## Роль данных

Основной прогнозируемый ряд — публичная выгрузка СберИндекса
«Потребительские безналичные расходы на уровне муниципальных образований».

СберИндекс является target-layer, а официальные муниципальные данные, Росстат,
мобильность, календарь, погода, макроэкономика и новости используются только как
доступные на момент прогноза признаки или как Reference Layer для интерпретации.

## Канонизация

Исходный CSV читается напрямую из `.csv` или `.csv.zip`.

```text
SberIndex export
    ↓
schema check
    ↓
exact duplicate removal
    ↓
municipality identity control
    ↓
ambiguous-name quarantine
    ↓
canonical monthly panel
    ↓
rolling temporal backtest
```

В публичной выгрузке название МО не всегда является глобально уникальным.
Если один и тот же `mo` дает более одной строки для одинаковых
`period + category`, весь такой name-key исключается из model-training до
восстановления региона/ОКТМО. Искусственно нумеровать эти строки запрещено,
потому что это может смешать разные муниципалитеты во времени.

## Запуск

```bash
python scripts/build_sberindex_spending.py path/to/sberindex_export.csv.zip
```

Скрипт создаёт локально:

- `data/processed/sberindex_spending_monthly.csv` — model-eligible panel;
- `data/quarantine/sberindex_spending_ambiguous.csv` — неоднозначные МО;
- `data/reports/sberindex_spending_profile.json` — data-quality profile;
- `data/manifest/competition_dataset_manifest.csv` — URL, SHA-256 и provenance.

Эти файлы генерируются из публичного источника и не коммитятся как тяжелые
runtime artifacts.

## Протокол прогноза

Основная метрика конкурса — **MAE**. R² сохраняется как вторичная.
Random split запрещён. Используется rolling-origin evaluation по времени,
а модели обучаются как global panel models по множеству муниципалитетов.

Первый model tournament:

1. Last Value;
2. Seasonal Naive 12;
3. Prophet;
4. Grow — модель роста MESM;
5. LightGBM global;
6. N-HiTS;
7. PatchTST;
8. одна современная foundation time-series model.

Победитель выбирается по holdout MAE, а не по качеству на train.

## Shock detection

После выбора champion model:

```text
Actual
  − Forecast
  = Residual
      ↓
robust Z-score
      ↓
persistence
      ↓
CUSUM / BOCPD
      ↓
PELT confirmation
      ↓
NORMAL → OBSERVE → WARNING → BREAK_CONFIRMED
```

Синтетическая инъекция шоков используется только для controlled benchmark.
Реальные выводы маркируются отдельно и не смешиваются с synthetic evidence.


## ОКТМО как единый ключ

В model-ready данных ключ муниципалитета — только официальный 8-значный ОКТМО.
`municipality_name` и исходное поле `mo` не используются для join между источниками.

Реестр строится из открытого классификатора Росстата:

```bash
python scripts/build_oktmo_registry.py path/to/official_oktmo.csv --source-version YYYY-MM-DD
```

Затем source-specific aliases связывают подписи СберИндекса с ОКТМО.
Автоматически разрешается только точное нормализованное имя, уникальное в
официальном реестре. Fuzzy matching формирует только review-кандидаты.

Итоговый ключ model matrix:

```text
OKTMO + period_start + category_code
```

Это исключает смешивание одноименных муниципалитетов из разных субъектов.


## Географический scope конкурса

MESM не строит федеральную модель ради максимального покрытия. Главный кейс —
**Сургут (ОКТМО 71876000)**. Сетка ХМАО используется как обучающий и сравнительный
контекст, чтобы глобальная модель видела больше временных рядов, но итоговые
конкурсные выводы и визуализация фокусируются на Сургуте.

```text
RAW СберИндекс: полный экспорт
        ↓
identity / OKTMO
        ↓
HMAO training network
        ↓
global model
        ↓
SURGUT 71876000
        ↓
2024 out-of-sample forecast
        ↓
Residual → Early Warning → Structural Change
```

Основной фактический holdout — 2024 год. Это позволяет рассчитывать MAE и R²
только по известным actuals. Периоды после доступной истории не используются
для подтверждения качества модели.


## Цикл разработки и benchmark

Каждый следующий блок MESM проходит один и тот же цикл:

```text
данные → контракт → код → тест → OOS-метрики → интерпретация → корректировка
```

Первый зафиксированный benchmark для Сургута использует 2023 как стартовую
историю и 2024 как фактический expanding one-step holdout. Простые модели
Last Value, Seasonal Naive 12 и Linear Trend нужны как нижняя граница:
Prophet, Grow и последующие модели считаются улучшением только если
снижают MAE на том же наборе прогнозных дат.

Model Matrix содержит calendar features, лаги 1/2/3/6/12 и rolling statistics.
Текущий target никогда не попадает в признаки текущего периода.


## Сравнение: Prophet и Grow

Prophet и Grow оцениваются на тех же 12 фактических месяцах 2024 года.
Нельзя выбирать для них другой holdout.

Grow использует target transformation:

```text
g_t = log(y_t / y_(t-1))
```

и восстанавливает прогноз:

```text
y_hat_t = y_(t-1) * exp(g_hat_t)
```

Это позволяет региональной модели обучаться на МО и категориях разного масштаба.
В признаки входят только известные к моменту прогноза значения: calendar,
lag 1/2/3/6/12 и rolling 3/6.

На текущей source-local peer-сетке ХМАО development benchmark:

- Linear Trend MAE = 2391.05 ₽;
- Grow (OKTMO network) MAE = 2067.48 ₽, R² = 0.347;
- Prophet MAE = 2404.56 ₽, R² = 0.330;
- относительное снижение Grow MAE к Prophet ≈ 14.0%;
- относительное снижение Grow MAE к Linear Trend ≈ 13.5%.

19 безопасных peer-рядов ХМАО теперь переводятся в официальный формат 8-значного
ОКТМО до построения признаков; три source-name collision исключены. Prophet
воспроизводится в GitHub Actions на компактном фактическом ряде Сургута.
До row-level сверки peer-кодов с текущим CSV Росстата 2026 Grow результат
считается development evidence, а не финальным конкурсным результатом. Финальный gate
зафиксирован в `config/competition_model_gate.yaml`.


## Shock detector tournament

Раннее предупреждение и подтверждение структурного сдвига оцениваются раздельно.

```text
real forecast residual pool
        ↓
robust standardization
        ↓
bootstrap null paths
        ↓
controlled UP/DOWN changes
        ↓
TRANSIENT_SHOCK 1–3 мес. / REGIME_SHIFT 6–12 мес.
        ↓
CUSUM vs Page-Hinkley
        ↓
detection rate / false early alarms / delay
        ↓
PELT
        ↓
offline localization / confirmation
```

PELT не интерпретируется как early-warning detector: он оценивается как offline
метод локализации точки изменения. Все методы калибруются к единому бюджету
ложных тревог до сравнения мощности.


Короткое отклонение и структурный режим оцениваются отдельно: высокий detection
rate на длительном сдвиге не должен маскировать неспособность найти одиночный
аномальный месяц, и наоборот.
