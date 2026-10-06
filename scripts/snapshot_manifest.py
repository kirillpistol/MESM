#!/usr/bin/env python3
"""Записать или проверить манифест офлайн-снимка данных (SHA-256).

  python scripts/snapshot_manifest.py --write
  python scripts/snapshot_manifest.py --verify            # предупреждает, код 0
  python scripts/snapshot_manifest.py --verify --strict   # при расхождении код 1
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mesm.ingest.snapshot import MANIFEST_REL, verify_manifest, write_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--verify", action="store_true")
    parser.add_argument("--strict", action="store_true", help="выйти с кодом 1 при расхождении")
    args = parser.parse_args()

    if args.write:
        path = write_manifest(ROOT)
        print(f"Манифест снимка записан: {path.relative_to(ROOT)}")
        return 0

    try:
        report = verify_manifest(ROOT)
    except FileNotFoundError:
        print(f"ВНИМАНИЕ: нет {MANIFEST_REL}. Целостность снимка не проверена.")
        return 1 if args.strict else 0

    serious = len(report["missing"]) + len(report["changed"])
    if not serious and not report["unlisted"]:
        print("OK: файлы снимка совпадают с манифестом (SHA-256).")
        return 0
    labels = {"missing": "нет на диске", "changed": "изменён", "unlisted": "нет в манифесте"}
    if serious:
        print("ВНИМАНИЕ: снимок данных отличается от манифеста.")
    else:
        print("OK: файлы снимка совпадают с манифестом. Дополнительно (не ошибка):")
    for key in ("missing", "changed", "unlisted"):
        for rel in report[key]:
            print(f"  [{labels[key]}] {rel}")
    if serious:
        print("Если данные обновлялись намеренно, выполните: python scripts/snapshot_manifest.py --write")
    # Лишние файлы (unlisted) - только информация; ошибкой считаются пропавшие и изменённые.
    return 1 if (args.strict and serious) else 0


if __name__ == "__main__":
    raise SystemExit(main())
