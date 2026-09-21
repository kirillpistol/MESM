# External Layer, Forecast Benchmark и Decision Memo

Этот блок появился после сравнения MESM с открытыми municipal-finance проектами.

## 1. External Data Layer

MESM принимает длинный канонический формат:

- period
- geography_name
- geography_level
- variable
- value
- unit
- source
- publication_date
- as_of_date

Опционально: source_url, oktmo, notes.

Типичные переменные: CPI, fuel, FX, oil, income, employment и агрегированный consumer target, если он законно доступен.

External Layer не равен Predictive State. Загрузка факторов только делает временные ряды доступными для benchmark и будущей модели.

## 2. Forecast vs Actual

Для каждого geography + variable с минимум 25 наблюдениями интерфейс строит expanding one-step benchmark:

- Seasonal Naive;
- Linear Trend challenger.

Это прозрачная проверка цепочки Actual → Forecast → Error.

Для confirmatory H1 финальная модель должна сравниваться с baseline по заранее зафиксированному temporal protocol. Linear Trend в интерфейсе — не финальный ML claim.

## 3. Decision-ready output

Отчет теперь разделяет:

1. что изменилось;
2. сила evidence;
3. доступность External Layer;
4. что можно интерпретировать сейчас;
5. что проверить дальше;
6. ограничения.

MESM не превращает correlation в causality и не выдает отсутствие данных за NORMAL.

## 4. Следующий шаг

Когда появится реальный consumer target или разрешенный банковский агрегат:

External factors + consumer target → walk-forward forecast → residual → CUSUM/PELT → Predictive State → Dual Fusion → LeadTime.
