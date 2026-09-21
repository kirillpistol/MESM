from __future__ import annotations
import hashlib
from pathlib import Path

def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def lineage_record(path: str | Path, source_id: str) -> dict:
    p = Path(path)
    return {
        "source_id": source_id,
        "source_file": p.name,
        "source_sha256": sha256_file(p),
        "size_bytes": p.stat().st_size,
    }
