"""Parsers/builders for official Surgut budget spreadsheets.

The parser is deliberately based on labels and year headers instead of fixed
cell addresses because official workbooks may move rows between publications.
Values are preserved in the workbook unit (the 2025-2027 decision uses thousand
rubles). The builder never inserts budget numbers in source code.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import math
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import Iterable, Sequence

from mesm.ingest.xlsx_minimal import read_first_sheet

YEARS = (2025, 2026, 2027)


def _text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _norm(value: object) -> str:
    return _text(value).casefold().replace("ё", "е")


def _number(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        value = float(value)
        return value if math.isfinite(value) else None
    cleaned = str(value).replace("\xa0", "").replace(" ", "").replace(",", ".")
    cleaned = cleaned.replace("−", "-").strip()
    try:
        value = float(cleaned)
        return value if math.isfinite(value) else None
    except ValueError:
        return None


def _row_label(row: Sequence[object]) -> str:
    return " | ".join(_text(x) for x in row if _text(x))


def workbook_unit_scale_to_rubles(rows: Sequence[Sequence[object]]) -> float:
    header = " ".join(_norm(_row_label(row)) for row in rows[:20])
    if "тыс" in header and "руб" in header:
        return 1000.0
    return 1.0


def read_docx_text(path: str | Path) -> str:
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(zf.read("word/document.xml"))
    texts = []
    for node in root.iter():
        if node.tag.endswith("}t") and node.text:
            texts.append(node.text)
        elif node.tag.endswith("}p"):
            texts.append("\n")
    return re.sub(r"[ \t]+", " ", "".join(texts))


def parse_debt_limits_text(text: str) -> dict[int, float]:
    normalized = text.replace("\xa0", " ").replace("ё", "е")
    result: dict[int, float] = {}
    pattern = re.compile(
        r"на\s+01\.01\.(20\d{2})\s+в\s+объеме\s+([0-9 \u00a0]+,[0-9]{2})",
        re.IGNORECASE,
    )
    for match in pattern.finditer(normalized):
        boundary_year = int(match.group(1))
        amount = _number(match.group(2))
        if amount is not None:
            result[boundary_year - 1] = amount
    return result


def read_excel_rows(path: str | Path) -> list[list[object]]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xlsm"}:
        return read_first_sheet(path)
    if suffix == ".xls":
        try:
            import pandas as pd
            frame = pd.read_excel(path, sheet_name=0, header=None, engine="xlrd")
        except ImportError as exc:
            raise RuntimeError('Legacy .xls requires: pip install -e ".[excel]"') from exc
        return frame.where(frame.notna(), None).values.tolist()
    raise ValueError(f"Unsupported spreadsheet: {path}")


def _find_year_columns(rows: Sequence[Sequence[object]], years: Iterable[int] = YEARS) -> dict[int, int]:
    wanted = tuple(int(y) for y in years)
    best: dict[int, int] = {}
    for row in rows[:25]:
        current: dict[int, int] = {}
        for idx, cell in enumerate(row):
            text = _text(cell)
            for year in wanted:
                if re.search(rf"(?<!\d){year}(?!\d)", text):
                    current[year] = idx
        if len(current) > len(best):
            best = current
    if not best:
        raise ValueError("Could not locate year columns in official workbook")
    return best


def _find_row(
    rows: Sequence[Sequence[object]],
    *,
    contains: Sequence[str],
    excludes: Sequence[str] = (),
    prefer_short: bool = False,
) -> Sequence[object]:
    tokens = [_norm(x) for x in contains]
    negative = [_norm(x) for x in excludes]
    matches: list[Sequence[object]] = []
    for row in rows:
        text = _norm(_row_label(row))
        if all(token in text for token in tokens) and not any(token in text for token in negative):
            matches.append(row)
    if not matches:
        raise ValueError(f"Official workbook row not found: {contains}")
    if prefer_short:
        matches.sort(key=lambda row: len(_row_label(row)))
    return matches[0]


def _values_by_year(row: Sequence[object], year_cols: dict[int, int]) -> dict[int, float]:
    out: dict[int, float] = {}
    for year, idx in year_cols.items():
        value = _number(row[idx] if idx < len(row) else None)
        if value is None:
            raise ValueError(f"Missing numeric value for {year} in row: {_row_label(row)}")
        out[year] = value
    return out


def _first_total_row(rows: Sequence[Sequence[object]], year_cols: dict[int, int]) -> Sequence[object]:
    candidates = []
    for row in rows:
        label = _norm(_row_label(row))
        if "всего" not in label:
            continue
        numeric = sum(
            _number(row[idx] if idx < len(row) else None) is not None
            for idx in year_cols.values()
        )
        if numeric == len(year_cols):
            candidates.append(row)
    if not candidates:
        raise ValueError("TOTAL row not found")
    candidates.sort(key=lambda row: len(_row_label(row)))
    return candidates[0]


@dataclass(frozen=True)
class AdoptedBudget:
    year: int
    total_revenue: float
    revenue_base: float
    transfers: float
    expenditure: float
    financing_sources: float
    eligible_exceptions: float
    debt_service: float

    @property
    def deficit(self) -> float:
        return max(self.expenditure - self.total_revenue, 0.0)


def parse_adopted_budget(
    revenue_rows: Sequence[Sequence[object]],
    financing_rows: Sequence[Sequence[object]],
    expenditure_rows: Sequence[Sequence[object]],
    years: Iterable[int] = YEARS,
) -> list[AdoptedBudget]:
    years = tuple(int(y) for y in years)
    rev_cols = _find_year_columns(revenue_rows, years)
    fin_cols = _find_year_columns(financing_rows, years)
    exp_cols = _find_year_columns(expenditure_rows, years)

    total_revenue = _values_by_year(_first_total_row(revenue_rows, rev_cols), rev_cols)
    revenue_base = _values_by_year(
        _find_row(revenue_rows, contains=("налоговые и неналоговые доходы",), prefer_short=True),
        rev_cols,
    )
    expenditure = _values_by_year(_first_total_row(expenditure_rows, exp_cols), exp_cols)
    financing = _values_by_year(_first_total_row(financing_rows, fin_cols), fin_cols)

    try:
        debt_service = _values_by_year(
            _find_row(expenditure_rows, contains=("обслуживание", "долг"), prefer_short=True),
            exp_cols,
        )
    except ValueError:
        debt_service = {year: 0.0 for year in years}

    exception_rows: list[Sequence[object]] = []
    for row in financing_rows:
        label = _norm(_row_label(row))
        if "изменен" in label and "остат" in label:
            exception_rows.append(row)
        elif "продаж" in label and ("акци" in label or "участи" in label or "капитал" in label):
            exception_rows.append(row)

    exceptions = {year: 0.0 for year in years}
    for row in exception_rows:
        for year, value in _values_by_year(row, fin_cols).items():
            exceptions[year] += max(value, 0.0)

    result = []
    for year in years:
        total = total_revenue[year]
        base = revenue_base[year]
        result.append(
            AdoptedBudget(
                year=year,
                total_revenue=total,
                revenue_base=base,
                transfers=total - base,
                expenditure=expenditure[year],
                financing_sources=abs(financing[year]),
                eligible_exceptions=exceptions[year],
                debt_service=debt_service[year],
            )
        )
    return result


def extract_expenditure_sections(
    rows: Sequence[Sequence[object]],
    years: Iterable[int] = YEARS,
) -> list[dict]:
    year_cols = _find_year_columns(rows, years)
    output: list[dict] = []
    seen: set[tuple[int, str]] = set()
    for row in rows:
        strings = [_text(cell) for cell in row]
        section_idx = None
        section_code = None
        for idx, cell in enumerate(strings):
            if re.fullmatch(r"\d{2}", cell):
                section_idx, section_code = idx, cell
                break
        if section_idx is None:
            continue
        name = ""
        for cell in strings[section_idx + 1:]:
            if cell and _number(cell) is None and not re.fullmatch(r"\d+", cell):
                name = cell
                break
        if not name:
            continue
        for year, col in year_cols.items():
            value = _number(row[col] if col < len(row) else None)
            if value is None:
                continue
            key = (year, section_code)
            if key in seen:
                continue
            seen.add(key)
            output.append({"year": year, "section_code": section_code, "section_name": name, "amount": value})
    return output


def _find_raw_file(source_dir: Path, *, app_no: int, extensions=(".xls", ".xlsx")) -> Path:
    matches = []
    pattern = re.compile(rf"приложение[ _.-]*{app_no}(?!\d)", re.IGNORECASE)
    for path in source_dir.iterdir():
        if path.suffix.lower() not in extensions:
            continue
        if pattern.search(path.name.replace("_", " ")):
            matches.append(path)
    if not matches:
        raise FileNotFoundError(f"No raw source for Appendix {app_no} in {source_dir}")
    return sorted(matches)[0]


def _find_decision_docx(source_dir: Path) -> Path | None:
    docs = sorted(path for path in source_dir.iterdir() if path.suffix.lower() == ".docx")
    return docs[0] if docs else None


def build_adopted_outputs(
    source_dir: str | Path,
    output_plan: str | Path,
    output_structure: str | Path,
    *,
    source_page_url: str,
    publication_date: str,
    source_document: str,
) -> tuple[list[dict], list[dict]]:
    source_dir = Path(source_dir)
    app1 = _find_raw_file(source_dir, app_no=1)
    app2 = _find_raw_file(source_dir, app_no=2)
    app3 = _find_raw_file(source_dir, app_no=3)

    revenue_rows = read_excel_rows(app1)
    financing_rows = read_excel_rows(app2)
    expenditure_rows = read_excel_rows(app3)
    budgets = parse_adopted_budget(revenue_rows, financing_rows, expenditure_rows)
    sections = extract_expenditure_sections(expenditure_rows)
    unit_scale = workbook_unit_scale_to_rubles(revenue_rows)
    decision_docx = _find_decision_docx(source_dir)
    debt_limits_rub = parse_debt_limits_text(read_docx_text(decision_docx)) if decision_docx else {}

    plan_rows = []
    structure_rows = []
    for budget in budgets:
        plan_rows.append({
            "year": budget.year,
            "municipality_name": "Сургут",
            "stage": "ADOPTED" if budget.year == 2025 else "PLAN_PERIOD",
            "total_revenue": budget.total_revenue,
            "revenue_base": budget.revenue_base,
            "transfers": budget.transfers,
            "expenditure": budget.expenditure,
            "deficit": budget.deficit,
            "financing_sources": budget.financing_sources,
            "eligible_exceptions": budget.eligible_exceptions,
            "debt_upper_limit": debt_limits_rub.get(budget.year, 0.0) / unit_scale if budget.year in debt_limits_rub else 0.0,
            "debt_service": budget.debt_service,
            "exceptions_status": "PARSED_FROM_OFFICIAL_APP2",
            "source_document": source_document,
            "source_url": source_page_url,
            "publication_date": publication_date,
            "notes": (
                "generated from official source files; workbook unit preserved; "
                + ("debt limit parsed from decision DOCX" if budget.year in debt_limits_rub else "debt limit not found in raw DOCX")
            ),
        })
        structure_rows.extend([
            {
                "year": budget.year, "municipality_name": "Сургут", "budget_side": "REVENUE",
                "group": "Собственные доходы", "item_name": "Доходы без безвозмездных поступлений",
                "amount": budget.revenue_base, "item_code": "", "is_transfer": 0,
                "is_recurring": "", "is_subvention": "", "is_debt_service": 0,
                "is_borrowing": 0, "flexibility": "UNKNOWN", "source_file": app1.name,
                "notes": "generated from official workbook",
            },
            {
                "year": budget.year, "municipality_name": "Сургут", "budget_side": "REVENUE",
                "group": "Безвозмездные поступления", "item_name": "Безвозмездные поступления",
                "amount": budget.transfers, "item_code": "", "is_transfer": 1,
                "is_recurring": "", "is_subvention": "", "is_debt_service": 0,
                "is_borrowing": 0, "flexibility": "UNKNOWN", "source_file": app1.name,
                "notes": "total revenue minus tax and non-tax revenue",
            },
            {
                "year": budget.year, "municipality_name": "Сургут", "budget_side": "FINANCING",
                "group": "Источники финансирования", "item_name": "Источники финансирования дефицита",
                "amount": budget.financing_sources, "item_code": "", "is_transfer": 0,
                "is_recurring": "", "is_subvention": "", "is_debt_service": 0,
                "is_borrowing": 0, "flexibility": "UNKNOWN", "source_file": app2.name,
                "notes": "generated from official workbook",
            },
            {
                "year": budget.year, "municipality_name": "Сургут", "budget_side": "EXCEPTION",
                "group": "Допустимые исключения", "item_name": "Проверенные специальные источники",
                "amount": budget.eligible_exceptions, "item_code": "", "is_transfer": 0,
                "is_recurring": "", "is_subvention": "", "is_debt_service": 0,
                "is_borrowing": 0, "flexibility": "UNKNOWN", "source_file": app2.name,
                "notes": "positive change in balances / equity-sale receipts parsed by label",
            },
        ])
    for item in sections:
        structure_rows.append({
            "year": item["year"], "municipality_name": "Сургут", "budget_side": "EXPENDITURE",
            "group": item["section_name"], "item_name": item["section_name"],
            "amount": item["amount"], "item_code": item["section_code"], "is_transfer": 0,
            "is_recurring": "", "is_subvention": "", "is_debt_service": int("долг" in _norm(item["section_name"])),
            "is_borrowing": 0, "flexibility": "UNKNOWN", "source_file": app3.name,
            "notes": "top-level budget classification section",
        })

    _write_csv(output_plan, plan_rows)
    _write_csv(output_structure, structure_rows)
    return plan_rows, structure_rows


def _write_csv(path: str | Path, rows: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"Refusing to write empty dataset: {path}")
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
