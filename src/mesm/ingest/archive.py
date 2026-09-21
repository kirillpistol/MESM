from __future__ import annotations
import zipfile
from pathlib import Path, PurePosixPath

class UnsafeArchiveMember(ValueError):
    pass

def _safe_member(name: str) -> bool:
    p = PurePosixPath(name.replace("\\", "/"))
    return not p.is_absolute() and ".." not in p.parts

def list_zip(path: str | Path) -> list[dict]:
    rows = []
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            if not _safe_member(info.filename):
                raise UnsafeArchiveMember(info.filename)
            rows.append({
                "member_name": info.filename,
                "size_bytes": info.file_size,
                "compressed_bytes": info.compress_size,
            })
    return rows

def safe_extract_zip(path: str | Path, destination: str | Path) -> list[Path]:
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    outputs = []
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            if not _safe_member(info.filename):
                raise UnsafeArchiveMember(info.filename)
            target = destination / PurePosixPath(info.filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                while True:
                    block = src.read(1024 * 1024)
                    if not block:
                        break
                    dst.write(block)
            outputs.append(target)
    return outputs
