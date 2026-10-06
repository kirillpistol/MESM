"""Целостность офлайн-снимка данных.

Снимок (processed/reference/external) - то, на чём работает демонстрация без
интернета. Манифест хранит SHA-256 каждого файла, чтобы любая незаметная правка
или порча файла была видна до начала расчёта.

Хеш считается после нормализации переводов строк (CRLF -> LF): один и тот же
файл на Windows и Linux даёт одинаковую сумму.
"""
from __future__ import annotations

import csv
import fnmatch
import hashlib
from pathlib import Path

MANIFEST_REL = "data/manifest/snapshot_manifest.csv"
INCLUDE_DIRS = ("data/processed", "data/reference", "data/external")
INCLUDE_FILES = ("config/official_sources.json",)
# Производный файл: пересобирается при каждом запуске из остальных, в снимок не входит.
EXCLUDE = frozenset({"data/processed/fiscal_reference_panel.csv"})
# Локальные артефакты, которые по .gitignore в репозиторий не попадают.
EXCLUDE_PATTERNS = (
    "data/processed/official_quality_inputs_long_*.csv",
    "data/processed/sberindex_spending_monthly.csv",
    "data/processed/public_aggregates.*",
    "data/processed/grow_features_asof.csv",
    "data/processed/cache/*",
)
EXTENSIONS = frozenset({".csv", ".json"})
FIELDS = ["path", "sha256", "size_bytes"]


def file_digest(path: str | Path) -> tuple[str, int]:
    data = Path(path).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest(), len(data)


def collect_files(root: str | Path) -> list[str]:
    root = Path(root)
    found: set[str] = set()
    for rel_dir in INCLUDE_DIRS:
        base = root / rel_dir
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in EXTENSIONS:
                found.add(path.relative_to(root).as_posix())
    for rel_file in INCLUDE_FILES:
        if (root / rel_file).is_file():
            found.add(rel_file)
    found -= EXCLUDE
    found = {rel for rel in found if not any(fnmatch.fnmatch(rel, pat) for pat in EXCLUDE_PATTERNS)}
    return sorted(found)


def build_manifest(root: str | Path) -> list[dict[str, str]]:
    root = Path(root)
    rows = []
    for rel in collect_files(root):
        digest, size = file_digest(root / rel)
        rows.append({"path": rel, "sha256": digest, "size_bytes": str(size)})
    return rows


def write_manifest(root: str | Path) -> Path:
    root = Path(root)
    target = root / MANIFEST_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = build_manifest(root)
    with target.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return target


def read_manifest(root: str | Path) -> dict[str, str]:
    path = Path(root) / MANIFEST_REL
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return {row["path"]: row["sha256"] for row in csv.DictReader(fh)}


def verify_manifest(root: str | Path) -> dict[str, list[str]]:
    """Сравнить файлы на диске с манифестом.

    Возвращает списки missing (нет на диске), changed (хеш не совпал) и
    unlisted (файл есть, в манифесте его нет). Если манифеста нет вообще,
    поднимается FileNotFoundError.
    """
    root = Path(root)
    expected = read_manifest(root)
    missing, changed = [], []
    for rel, digest in expected.items():
        target = root / rel
        if not target.is_file():
            missing.append(rel)
        elif file_digest(target)[0] != digest:
            changed.append(rel)
    unlisted = [rel for rel in collect_files(root) if rel not in expected]
    return {"missing": sorted(missing), "changed": sorted(changed), "unlisted": sorted(unlisted)}
