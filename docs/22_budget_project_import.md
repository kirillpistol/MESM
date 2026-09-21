# Импорт проекта бюджета

## Канонический формат

Проект бюджета загружается через «Ввод данных» как dataset budget_project.

Обязательные поля: year, municipality_name, budget_side, group, item_name, amount.

budget_side: REVENUE, EXPENDITURE, FINANCING, EXCEPTION.

Опциональные признаки: is_transfer, is_recurring, is_subvention, is_debt_service, is_borrowing, flexibility.

flexibility: FIXED, PARTIAL, FLEXIBLE, UNKNOWN.

## Автоматический расчет

После загрузки MESM агрегирует revenue base, transfers, expenditure, recurring revenue/expenditure, financing sources, eligible exceptions, planned net borrowing, debt service и expenditure excluding subventions.

Значения автоматически подставляются во вкладку «Бюджет».

## Структура статей

MESM показывает структуру доходов и расходов по группам, механическую экспозицию NormalizationGap по доле расходов и доступную емкость сокращения только по явно размеченной flexibility.

gap_exposure не является причинным вкладом статьи в дефицит.

mechanical_cut не является рекомендацией сокращать конкретную статью. Это технический расчет доступной емкости при заданной пользователем классификации гибкости.

## Demo

data/synthetic/budget_project_demo.csv — синтетический файл для проверки pipeline.