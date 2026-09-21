# Official Source Pipeline

MESM supports a reproducible public-data path for the Surgut budget baseline:

`official web page -> raw official files -> SHA-256 manifest -> parser -> processed CSV -> formulas/dashboard`.

## Configured sources

`config/official_sources.json` contains the adopted budget 2025–2027 (Decision No. 713-VII DG dated 23.12.2024) and the 2025 execution page (Decision No. 1052-VII DG dated 04.06.2026).

The fetcher discovers `.xls`, `.xlsx` and `.docx` links directly on the official page instead of embedding budget values in Python code.

## Rebuild

```bash
python scripts/fetch_official_sources.py surgut_budget_adopted_2025_2027
python scripts/build_surgut_official_budget.py
```

On Windows run `UPDATE_OFFICIAL_DATA.bat` after the first installation.

Raw binaries are stored under `data/raw/official/<source_id>/` and excluded from Git. The generated manifest stores URL, publication/download time, byte size and SHA-256. If the authority replaces a file at the same URL, the local old copy is preserved and the new copy receives a hash suffix.

The parser uses semantic row labels and year headers, not fixed cell addresses. It derives revenue, tax/non-tax revenue, transfers, expenditure, deficit, financing, eligible special sources, debt service, debt limit from the official decision DOCX and expenditure sections.

No budget amount is hard-coded in the fetcher or parser.
