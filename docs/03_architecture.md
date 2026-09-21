# Архитектура

```text
Raw source
  ↓
manifest + lineage
  ↓
parse / normalize
  ↓
validation / reconciliation
  ↓
canonical feature store
  ↓
model layer
  ↓
decision-support output
```

Raw-файл не переписывается. Для него сохраняются hash, источник, время получения и доступные `publication_date` / `as_of_date`.

Парсер выбирается не только по имени файла или листа. Учитываются fingerprint документа, ожидаемые ключевые слова и обязательные смысловые поля.

Перед моделью выполняются проверки типов, итогов, дубликатов, временной доступности, идентификаторов муниципалитетов и mapping бюджетной классификации.

Модель получает канонические записи, а не исходные Excel-файлы.

Поддерживаемые частоты: `DAY | WEEK | MONTH | QUARTER | HALF_YEAR | YEAR | EVENT`. Источник хранится в исходной частоте; resampling делается только в воспроизводимом feature-builder.

## Schema drift

```text
известная структура → parse
совместимый alias → parse + warning
неизвестная обязательная структура → QUARANTINE
```
