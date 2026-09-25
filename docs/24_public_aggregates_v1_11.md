# MESM v1.11: public aggregate input for Grow

Install: `pip install -e '.[public-data,dev]'`.

Copy `config/public_aggregate_sources.example.json`, inspect the actual FNS CSV and its published structure, then fill the **real column names**, observation period end, units, and publication date. Enable the entry only after verifying its territorial resolution. Run:

`python -m mesm.public_data.ingest --config config/my_sources.json --as-of 2026-09-25`

Output is `data/processed/public_aggregates.csv` and `data/processed/grow_features_asof.csv`. The second file excludes observations published after the prediction date. Add verified public KKT or Rosstat CSV sources with their own mapping in the same config. 5-NDFL and 7-NDFL are annual income features, category `all`; do not interpolate to months or treat them as category spending. The open FNS source may be national or regional rather than municipal: verify OKTMO coverage before enabling. No public raw receipt feed or live Geochecks API is assumed. Existing Grow consumption estimates are not replaced by income figures.

The cache uses a per-run memory lookup, persistent metadata and immutable SHA-256 raw payloads, with bounded concurrent HTTPS downloads, retries and a size limit. Existing snapshots remain reproducible until explicit refresh. Pandera validates raw, canonical and as-of feature tables; duplicates, negative amounts, invalid territories and future releases fail validation. The existing official budget web pipeline remains independent.

## Fault handling and schema changes

Each enabled source is fetched and checked independently. A broken download, wrong mapping, negative value, duplicate or invalid release date marks that source `quarantined` in `data/processed/public_aggregates.status.json`. The source payload remains in the immutable raw cache for inspection. By default, a partial or fully failed run leaves the previous canonical and as-of CSVs untouched; inspect the `partial` or `stale` status before using those older values. `allow_partial_publish: true` is available only when a downstream consumer deliberately accepts incomplete coverage. A successful run publishes staged CSVs and the status report together, with rollback if publication fails.

The contract registry next to the output records a fingerprint of column mapping, format and category for each source and `schema_version`. To change the source layout, inspect its published data contract, update the mapping and increment `schema_version`; using the old version with changed fields is quarantined. The source period and publication date must describe the specific downloaded snapshot. No automatic guess repairs malformed source values.
