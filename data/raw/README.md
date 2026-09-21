# data/raw

This directory is populated automatically from official public sources.

```bash
python scripts/fetch_official_sources.py surgut_budget_adopted_2025_2027
python scripts/build_surgut_official_budget.py
```

Downloaded binary files are intentionally not committed to Git. Their source URL, publication date, byte size and SHA-256 fingerprint are recorded in `data/manifest/source_manifest.csv`.
