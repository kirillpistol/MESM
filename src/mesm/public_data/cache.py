from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import random
from urllib.parse import urlparse


@dataclass(frozen=True)
class Snapshot:
    source: str
    url: str
    requested_at: str
    available_at: str
    period: str
    sha256: str
    etag: str | None
    last_modified: str | None
    status: int
    schema_version: str
    path: str


class AsyncSnapshotCache:
    def __init__(self, root: str | Path, *, concurrency: int = 4, timeout: float = 40,
                 retries: int = 2, max_bytes: int = 100_000_000):
        if concurrency < 1 or timeout <= 0 or retries < 0 or max_bytes < 1:
            raise ValueError("Invalid download settings")
        self.root = Path(root)
        self.semaphore = asyncio.Semaphore(concurrency)
        self.timeout = timeout
        self.retries = retries
        self.max_bytes = max_bytes
        self.memory: dict[str, Snapshot] = {}
        self.locks: dict[str, asyncio.Lock] = {}

    async def fetch(self, source: str, url: str, *, period: str, available_at: str,
                    schema_version: str = "1", refresh: bool = False) -> Snapshot:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Only HTTPS public source URLs are supported")
        key = sha256(json.dumps([source, url, period, available_at, schema_version]).encode()).hexdigest()
        async with self.locks.setdefault(key, asyncio.Lock()):
            manifest = self.root / "metadata" / f"{key}.json"
            cached = self.memory.get(key)
            if cached is None and manifest.exists():
                try:
                    cached = Snapshot(**json.loads(manifest.read_text(encoding="utf-8")))
                except (OSError, ValueError, TypeError):
                    cached = None
            if cached and cached.path == f"raw/{cached.sha256}" and not refresh:
                raw = self.root / cached.path
                if raw.is_file() and sha256(raw.read_bytes()).hexdigest() == cached.sha256:
                    self.memory[key] = cached
                    return cached
            import aiohttp
            async with self.semaphore:
                for attempt in range(self.retries + 1):
                    try:
                        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                            async with session.get(url, allow_redirects=True) as response:
                                response.raise_for_status()
                                if response.url.scheme != "https":
                                    raise ValueError("Source redirected away from HTTPS")
                                chunks, size = [], 0
                                async for chunk in response.content.iter_chunked(65536):
                                    size += len(chunk)
                                    if size > self.max_bytes:
                                        raise ValueError("Source exceeds size limit")
                                    chunks.append(chunk)
                                payload = b"".join(chunks)
                                digest = sha256(payload).hexdigest()
                                relpath = f"raw/{digest}"
                                path = self.root / relpath
                                path.parent.mkdir(parents=True, exist_ok=True)
                                if not path.exists():
                                    temp = path.with_name(path.name + ".tmp")
                                    temp.write_bytes(payload)
                                    os.replace(temp, path)
                                snapshot = Snapshot(source, url, datetime.now(timezone.utc).isoformat(),
                                                    available_at, period, digest, response.headers.get("ETag"),
                                                    response.headers.get("Last-Modified"), response.status,
                                                    schema_version, relpath)
                                manifest.parent.mkdir(parents=True, exist_ok=True)
                                temp_manifest = manifest.with_suffix(".tmp")
                                temp_manifest.write_text(json.dumps(asdict(snapshot), ensure_ascii=False, indent=2), encoding="utf-8")
                                os.replace(temp_manifest, manifest)
                                self.memory[key] = snapshot
                                return snapshot
                    except (aiohttp.ClientError, asyncio.TimeoutError):
                        if attempt == self.retries:
                            raise
                        await asyncio.sleep(min(2 ** attempt + random.random(), 10))
        raise RuntimeError("Download failed")

    async def fetch_many(self, items: list[dict]) -> list[Snapshot]:
        return await asyncio.gather(*(self.fetch(**item) for item in items))
