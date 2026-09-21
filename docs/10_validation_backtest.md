# Валидация и backtest

Для временных рядов случайный train/test split не используется.

\[
Train_{1:t}\rightarrow Forecast_{t+1}
\]

Forecast metrics: `WAPE`, `MASE`, `RMSE/MAE`.

Detection metrics: precision, recall, false alarms, detection delay и LeadTime.

Модель может видеть только информацию, которая реально была доступна на дату прогноза. Поэтому экономический период, `as_of_date` и `publication_date` хранятся отдельно.

Для официальных таблиц проверяются итоги, план/уточнение/факт, единицы измерения, муниципальные идентификаторы, mapping классификации, hash источника и дубликаты business key.

Stress tests включают экономические шоки (fuel, FX, income, transport, combined) и системные ошибки: пропавший источник, stale data, новая колонка, ошибка единиц ×1000, дубликаты, конфликт детекторов, пропавший банковский признак и смена классификации.
