# Реестр формул

Формулы MESM и формулы официальных источников хранятся отдельно.

## Производные MESM

\[
RevisionRate = \frac{Revised-Initial}{Initial}
\]

\[
RevisionMagnitude = \frac{|Revised-Initial|}{|Initial|}
\]

\[
ExecutionRate = \frac{Actual}{Revised}
\]

\[
ExecutionGap = \frac{Actual-Revised}{Revised}
\]

\[
CoverageGap = \frac{PlannedResources}{EstimatedCostOfObligations}-1
\]

\[
e_t=Y_t-\hat{Y}_t, \qquad z_t=\frac{e_t}{\sigma_e}
\]

\[
LeadTime=t_{ReferenceSignal}-t_{PredictiveSignal}
\]

\[
Margin=P_{(1)}-P_{(2)}
\]

Если margin меньше установленного порога уверенности, MESM возвращает `UNCERTAIN`, а не форсирует класс.

## Официальные показатели

Формулы из официальных муниципальных таблиц сохраняются отдельно в `data/processed/official_quality_formulas_2024_2025.csv` и `config/formulas/official_quality_formulas.yaml`.

Если внешний движок не может пересчитать Excel-формулу, это не трактуется как отсутствие официального показателя. Для поддерживаемых формул MESM пересчитывает значение из исходных переменных и сравнивает результат с источником, когда это возможно.
