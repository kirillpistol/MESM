#!/usr/bin/env python3
"""Безопасное обновление официальных данных.

Сохранённый снимок data/processed не заменяется наполовину: перед обновлением
делается копия, и при любой ошибке сборки она возвращается на место.

Коды выхода:
  0 - данные обновлены, манифест снимка перезаписан;
  1 - сайт ответил, но пересборка не прошла проверки; прежний снимок восстановлен;
  2 - официальный сайт недоступен; прежний снимок не тронут.
"""
from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mesm.ingest.snapshot import write_manifest

PROCESSED = ROOT / "data" / "processed"
GUARDED_TABLES = (
    "official_budget_plan_surgut_2025_2027.csv",
    "official_budget_project_surgut_2025.csv",
)
# Новая сборка не должна быть заметно "тоньше" прежней: так отсекаем случай,
# когда страница сайта изменилась и парсер молча вытащил часть строк.
MIN_ROW_RATIO = 0.8


def _run(*args: str) -> int:
    return subprocess.run([sys.executable, *args], cwd=ROOT).returncode


def _row_counts() -> dict[str, int]:
    counts = {}
    for name in GUARDED_TABLES:
        path = PROCESSED / name
        if path.exists():
            with path.open(encoding="utf-8-sig", newline="") as fh:
                counts[name] = sum(1 for _ in csv.DictReader(fh))
    return counts


def _restore(backup: Path) -> None:
    if PROCESSED.exists():
        shutil.rmtree(PROCESSED)
    shutil.copytree(backup, PROCESSED)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_id", nargs="?", default="surgut_budget_adopted_2025_2027")
    args = parser.parse_args()

    backup_root = Path(tempfile.mkdtemp(prefix="mesm_backup_"))
    backup = backup_root / "processed"
    try:
        if PROCESSED.exists():
            shutil.copytree(PROCESSED, backup)
        before = _row_counts()

        print("[1/5] Загрузка официальных файлов...")
        if _run("scripts/fetch_official_sources.py", args.source_id) != 0:
            print("Источник недоступен или страница изменилась. Сохранённый снимок не тронут.")
            return 2

        print("[2/5] Пересборка бюджетных таблиц...")
        if _run("scripts/build_surgut_official_budget.py") != 0:
            _restore(backup)
            print("Пересборка не удалась. Прежний снимок восстановлен.")
            return 1

        print("[3/5] Пересборка Fiscal Reference Panel...")
        if _run("scripts/build_fiscal_reference_panel.py") != 0:
            _restore(backup)
            print("Сборка панели не удалась. Прежний снимок восстановлен.")
            return 1

        print("[4/5] Проверка результата...")
        problems = []
        if _run("scripts/validate_project.py") != 0:
            problems.append("validate_project.py не пройден")
        after = _row_counts()
        for name, old in before.items():
            new = after.get(name, 0)
            if old and new < old * MIN_ROW_RATIO:
                problems.append(f"{name}: было {old} строк, стало {new}")
        if problems:
            _restore(backup)
            print("Новая сборка отклонена, прежний снимок восстановлен:")
            for item in problems:
                print("  - " + item)
            return 1

        print("[5/5] Обновление манифеста снимка (SHA-256)...")
        write_manifest(ROOT)
        print("Готово: данные обновлены.")
        return 0
    finally:
        shutil.rmtree(backup_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
