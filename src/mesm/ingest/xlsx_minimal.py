"""Минимальный read-only reader для XLSX на стандартной библиотеке Python.

Модуль не запускает макросы, не пересчитывает формулы и не меняет workbook.
Если в файле есть сохраненное значение формулы, читается именно оно. Для старого
\`.xls\` используется отдельный проверенный backend — подменять его XLSX-парсером нельзя.
"""
from __future__ import annotations
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
       "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def _col_index(ref: str) -> int:
    letters = re.match(r"([A-Z]+)", ref).group(1)
    value = 0
    for ch in letters:
        value = value * 26 + (ord(ch) - 64)
    return value - 1


def _shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    out = []
    for si in root.findall("m:si", _NS):
        parts = [t.text or "" for t in si.iterfind(".//m:t", _NS)]
        out.append("".join(parts))
    return out


def sheet_names(path: str | Path) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(zf.read("xl/workbook.xml"))
        return [s.attrib["name"] for s in root.find("m:sheets", _NS)]


def read_first_sheet(path: str | Path, max_rows: int | None = None) -> list[list[object]]:
    with zipfile.ZipFile(path) as zf:
        shared = _shared_strings(zf)
        root = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
        rows = []
        for row in root.iterfind(".//m:sheetData/m:row", _NS):
            cells = {}
            for c in row.findall("m:c", _NS):
                ref = c.attrib.get("r", "A1")
                idx = _col_index(ref)
                ctype = c.attrib.get("t")
                v = c.find("m:v", _NS)
                value = None if v is None else v.text
                if ctype == "inlineStr":
                    inline = c.find("m:is", _NS)
                    if inline is not None:
                        value = "".join(t.text or "" for t in inline.iterfind(".//m:t", _NS))
                if value is not None:
                    if ctype == "s":
                        value = shared[int(value)]
                    elif ctype == "b":
                        value = value == "1"
                    elif ctype != "inlineStr":
                        try:
                            value = float(value)
                            if value.is_integer():
                                value = int(value)
                        except ValueError:
                            pass
                cells[idx] = value
            width = max(cells, default=-1) + 1
            rows.append([cells.get(i) for i in range(width)])
            if max_rows is not None and len(rows) >= max_rows:
                break
        return rows
