from __future__ import annotations
from pathlib import Path

SIGNATURES = {
    b"PK\x03\x04": "ZIP_OR_XLSX",
    b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1": "OLE_COMPOUND",
    b"Rar!\x1a\x07": "RAR",
    b"%PDF": "PDF",
}

def detect_signature(path: str | Path) -> str:
    with open(path, "rb") as fh:
        head = fh.read(16)
    for signature, label in SIGNATURES.items():
        if head.startswith(signature):
            return label
    return "UNKNOWN"
