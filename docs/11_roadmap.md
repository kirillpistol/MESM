# План работы

## Уже сделано

Каркас репозитория, manifest источников, inventory архивов, канонические схемы, parser contracts, первые реальные публичные извлечения, formula registry, security model, state machine, базовый temporal backtest и тесты.

## Следующий этап

Собрать исторический Fiscal Reference Dataset для 22 верхнеуровневых муниципалитетов, свести plan/revision/actual за доступные годы и отдельно построить историю Сургута.

После этого подключаются внешние факторы: топливо, CPI, нефть, FX, доходы и занятость. Затем — банковский агрегированный consumer contract, когда доступ станет возможен.

Дальнейшая последовательность: forecasting → residuals → CUSUM/PELT → dual-state experiment → walk-forward backtest → dashboard → Champion/Challenger → stress tests → economic effect → независимая проверка.
