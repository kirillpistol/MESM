# Канонические контракты данных

Форматы источников могут меняться, но внутри MESM используется небольшой набор стабильных схем.

Каждая каноническая запись по возможности несет `source_id`, `source_file`, `source_sha256`, `source_version`, `parser_id`, `parser_version`, `schema_version`, `as_of_date`, `publication_date`, `ingested_at` и `validation_status`.

Основные наборы:

- `budget_execution` — муниципалитет, период, бюджетная классификация, initial/approved/revised plan, fact, единица измерения;
- `interbudget_transfer` — муниципалитет, период, тип трансферта, уровень источника, коды, состояния плана и факт;
- `budget_provision` — официальные и модельные значения хранятся отдельно (`bo_official`, `bo_model`, `tax_potential_official`, `tax_potential_model`);
- `article136_status` — режим и исходные показатели для ограничений по статье 136;
- `classification_mapping` — связи бюджетных кодов между версиями методологии;
- `official_quality_input` — официальные входные показатели и id индикатора;
- `model_signal` — состояние модели, confidence, disagreement и версия модели.
