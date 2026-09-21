"""Download immutable public source files from official municipal web pages.

The module intentionally uses the Python standard library. It stores the exact
HTML page, source files and a SHA-256 manifest so a processed dataset can always
be traced back to the public document that produced it.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import csv
import json
from pathlib import Path
import re
from typing import Iterable
from urllib.parse import urljoin, urlparse, unquote
from urllib.request import Request, urlopen

USER_AGENT = "MESM/1.10 (+public-budget-research; https://github.com/kirillpistol/MESM)"


@dataclass(frozen=True)
class OfficialLink:
    url: str
    title: str
    extension: str


@dataclass(frozen=True)
class ManifestRow:
    source_id: str
    authority: str
    document_type: str
    municipality_name: str
    page_url: str
    source_url: str
    title: str
    publication_date: str
    downloaded_at_utc: str
    file_name: str
    file_ext: str
    size_bytes: int
    sha256: str
    data_class: str = "PUBLIC"
    raw_immutable: bool = True
    ingestion_status: str = "DOWNLOADED"


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.current_href: str | None = None
        self.current_text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.current_href = href
            self.current_text = []

    def handle_data(self, data: str) -> None:
        if self.current_href is not None:
            self.current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self.current_href is not None:
            title = re.sub(r"\s+", " ", " ".join(self.current_text)).strip()
            self.links.append((self.current_href, title))
            self.current_href = None
            self.current_text = []


def discover_official_files(
    html: str,
    page_url: str,
    allowed_extensions: Iterable[str] = (".xls", ".xlsx", ".docx"),
) -> list[OfficialLink]:
    """Return unique downloadable spreadsheet/document links from a page."""
    allowed = {ext.lower() for ext in allowed_extensions}
    parser = _LinkParser()
    parser.feed(html)
    by_url: dict[str, OfficialLink] = {}
    for href, title in parser.links:
        url = urljoin(page_url, href)
        ext = Path(unquote(urlparse(url).path)).suffix.lower()
        if ext not in allowed:
            continue
        previous = by_url.get(url)
        candidate = OfficialLink(url=url, title=title, extension=ext)
        if previous is None or len(candidate.title) > len(previous.title):
            by_url[url] = candidate
    return list(by_url.values())


def _request_bytes(url: str, timeout: int = 60) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urlopen(request, timeout=timeout) as response:
        return response.read(), response.headers.get_content_type()


def _safe_filename(index: int, link: OfficialLink) -> str:
    original = Path(unquote(urlparse(link.url).path)).name
    original = re.sub(r"[<>:\\|?*\x00-\x1f]", "_", original).strip(" .")
    if not original:
        original = f"source_{index:02d}{link.extension}"
    return f"{index:02d}_{original}"


def load_source_config(path: str | Path, source_id: str) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    try:
        return payload["sources"][source_id]
    except KeyError as exc:
        raise KeyError(f"Unknown official source: {source_id}") from exc


def fetch_source_bundle(
    source_id: str,
    config: dict,
    raw_root: str | Path,
    manifest_path: str | Path,
    *,
    timeout: int = 60,
) -> list[ManifestRow]:
    """Fetch one configured source page and all allowed linked source files."""
    raw_root = Path(raw_root)
    source_dir = raw_root / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    page_bytes, _ = _request_bytes(config["page_url"], timeout=timeout)
    html = page_bytes.decode("utf-8", errors="replace")
    (source_dir / "source_page.html").write_bytes(page_bytes)

    links = discover_official_files(
        html,
        config["page_url"],
        config.get("allowed_extensions", (".xls", ".xlsx", ".docx")),
    )
    if not links:
        raise RuntimeError(f"No official files discovered at {config['page_url']}")

    required_tokens = [str(x).casefold() for x in config.get("required_title_tokens", [])]
    if required_tokens:
        titles = "\n".join(link.title.casefold() for link in links)
        missing = [token for token in required_tokens if token not in titles]
        if missing:
            raise RuntimeError(f"Official page changed; missing expected titles: {missing}")

    downloaded_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rows: list[ManifestRow] = []
    for index, link in enumerate(links, start=1):
        content, _ = _request_bytes(link.url, timeout=timeout)
        filename = _safe_filename(index, link)
        destination = source_dir / filename
        digest = sha256(content).hexdigest()
        if destination.exists():
            existing_digest = sha256(destination.read_bytes()).hexdigest()
            if existing_digest != digest:
                destination = destination.with_name(
                    f"{destination.stem}__{digest[:12]}{destination.suffix}"
                )
        if not destination.exists():
            destination.write_bytes(content)
        rows.append(
            ManifestRow(
                source_id=source_id,
                authority=config.get("authority", ""),
                document_type=config.get("document_type", ""),
                municipality_name=config.get("municipality_name", ""),
                page_url=config["page_url"],
                source_url=link.url,
                title=link.title,
                publication_date=config.get("publication_date", ""),
                downloaded_at_utc=downloaded_at,
                file_name=str(destination.relative_to(raw_root.parent.parent)).replace("\\", "/"),
                file_ext=link.extension,
                size_bytes=len(content),
                sha256=digest,
            )
        )

    write_manifest(rows, manifest_path, replace_source_id=source_id)
    return rows


def write_manifest(
    rows: Iterable[ManifestRow],
    path: str | Path,
    *,
    replace_source_id: str | None = None,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, str]] = []
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as fh:
            existing = list(csv.DictReader(fh))
    if replace_source_id is not None:
        existing = [r for r in existing if r.get("source_id") != replace_source_id]
    new_rows = [asdict(row) for row in rows]
    all_rows = existing + new_rows
    fieldnames = list(ManifestRow.__dataclass_fields__)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
