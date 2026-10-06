# Манифесты данных

- `snapshot_manifest.csv` — SHA-256 файлов офлайн-снимка (processed, reference,
  external, `config/official_sources.json`). Создаётся и проверяется
  `scripts/snapshot_manifest.py` (`--write`, `--verify`, `--strict`); после
  успешного `UPDATE_OFFICIAL_DATA.bat` перезаписывается автоматически. Хеш считается
  после нормализации CRLF -> LF, поэтому совпадает на Windows и Linux.
  `fiscal_reference_panel.csv` в снимок не входит: он производный и пересобирается
  при каждом запуске.
- `source_manifest.csv` — появляется после `scripts/fetch_official_sources.py`
  (или `UPDATE_OFFICIAL_DATA.bat`): URL страницы и файла, даты, локальный путь,
  размер и SHA-256 скачанных официальных документов. Сами raw-файлы в Git не хранятся.
