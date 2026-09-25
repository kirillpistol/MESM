# Evidence register for Surgut cash and municipal sources

Status checked 2026-09-25. This page records public evidence and what the MESM pilot may infer from it. It does not authorize access to internal treasury data or certify that the monthly source exists in the public domain.

| Source | Evidence | Role | Access and limitation |
| --- | --- | --- | --- |
| Annual execution 2024 | [Draft published 2025-04-05](https://docsurgut.ru/Document/View/6253); [approved resolution 805-VII DG published 2025-05-31](https://docsurgut.ru/Document/View/6647) | Historical benchmark for KBK revenue, expenditure and financing | Supplied `проект (1).pdf` is the 107-page draft, not a standalone 0503117. Use approved resolution for final totals after cross-check. |
| Monthly 0503117 | Financial department, requested XLSX | Monthly reporting bridge | Not supplied; obtain schema, month-end and release dates, YTD basis and revisions. |
| UFK cash movements | Internal treasury/financial office export | Earliest signal by KBK | Access and sampling schedule unconfirmed; never equate raw cash with normalized trend. |
| RRO order and register | [Order 4058](https://base.garant.ru/29125624/); [official 2026–2028 register](https://admsurgut.ru/gorodskaya-vlast/administratsiya/strukturnye-podrazdeleniya/departament-finansov/byudzhet-i-finansy/byudzhet-goroda-surguta-/reestr-raskhodnykh-obyazatelstv-/2026-1402/reestr-raskhodnykh-obyazatelstv-goroda-surguta-na-2026-2028-gody/) | Obligation/planned demand; bridge to Reference | Published XLSX is available; current legal form and coding mapping need review. It is not cash expenditure. |
| 5/7-NDFL | [FNS regional municipal 7-NDFL releases for 2025](https://www.nalog.gov.ru/rn86/related_activities/statistics_and_analytics/forms/16431815/); [Tochno.st harmonized Parquet](https://tochno.st/datasets/ndfl) | Annual/quarterly income context | Verify metric definition, OCTMO and as-of release date against FNS. Tax income statistics do not equal municipal budget cash receipts. |
| EMISS / PMO | [Rosstat municipal database](https://74.rosstat.gov.ru/data_base_mun) | Peer group and contextual features | Select explicit indicator codes, frequency and geographic coverage; do not presume stable API access. |

## Supplied historical sample

The draft decision for 2024 lists revenue 46,723,332,361.98 RUB, expenditure 43,102,449,621.00 RUB, surplus 3,620,882,740.98 RUB; tax and non-tax revenue 20,838,422,127.10 RUB, personal income tax 14,573,574,783.13 RUB, USN tax 3,320,227,805.61 RUB and sales of material/intangible assets 147,373,108.05 RUB. SHA-256 of the supplied 107-page draft: `74da8ad8f49bc6b033176c6c2043f0923483b2a85f4ff4e060f6710d0d740320`. A second supplied 25-page explanatory note has an incomplete-download suffix; its table mentions a negative 45,050.6 thousand RUB return of earmarked interbudget transfers from past years, but its completeness is not verified. These figures are evidence of component structure, not observed monthly timing or a forecast result.

## Integration decision

Use public annual execution and RRO for historical Reference reconciliation; use municipal tax and PMO tables as dated context. Request the monthly 0503117 and controlled UFK export before claiming a live early-warning system. Existing `mesm.budget.cash_execution` keeps raw cash separate from dated, approved analyst adjustments, and never inserts those adjustments into the statutory `normalization_gap` inputs.

For a shadow pilot, require at least 24 comparable monthly observations, publication timestamps, KBK mapping and reconciled annual totals. Compare raw cash, corrected cash and the existing Reference on identical as-of dates; report coverage, lag, false alerts, lead time and manual effort. The 5–10 working day and 1–1.5 month delays are planning assumptions until measured from real releases.
