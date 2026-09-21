# Synthetic External Layer demo

Файл external_monthly_demo.csv предназначен только для тестирования интерфейса и pipeline.

Он содержит 36 месяцев по четырем synthetic-переменным для ХМАО:

- cpi_index
- fuel_price_index
- income_index
- consumer_spending_real_proxy

В consumer_spending_real_proxy искусственно внесен устойчивый сдвиг в конце ряда. Это не реальные данные ХМАО и не evidence качества MESM.

Как проверить:

1. Вкладка «Ввод данных».
2. Шаг «External / Predictive Proxy».
3. Загрузить data/synthetic/external_monthly_demo.csv.
4. Принять файл.
5. Открыть Shock Monitor.
6. Выбрать ХМАО и consumer_spending_real_proxy.
7. Проверить Forecast vs Actual benchmark.

Файл нужен только для smoke/integration test.
