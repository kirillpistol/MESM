# Безопасность и доступ

Базовый принцип — `DENY BY DEFAULT`.

\[
CanRead = RolePermission \cap DatasetPermission \cap ColumnPermission \cap PurposePermission
\]

В публичный репозиторий попадают только открытые источники и явно синтетические данные.

В закрытом банковском контуре могут использоваться классы `PUBLIC`, `INTERNAL`, `RESTRICTED`, `BANK_CONFIDENTIAL`, `HIGHLY_RESTRICTED`. Роль не должна автоматически открывать все строки и поля.

Переобучение создает Challenger. Автоматический promotion в production по умолчанию запрещен. Для модели сохраняются artifact, feature schema, data hash, Git commit и rollback target. При конфликте детекторов или низкой уверенности система возвращает `OBSERVE` / `UNCERTAIN`.
