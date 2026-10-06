#!/usr/bin/env python3
"""Печатает SHA-256 pyproject.toml: по нему START_MESM.bat решает, нужна ли доустановка."""
import hashlib
from pathlib import Path

data = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_bytes().replace(b"\r\n", b"\n")
print(hashlib.sha256(data).hexdigest()[:16])
