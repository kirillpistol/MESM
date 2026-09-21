"""Контролируемый ввод, проверка и версионирование данных MESM."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from io import BytesIO, StringIO
from pathlib import Path
import csv
import re

import pandas as pd


@dataclass(frozen=True)
class DatasetSpec:
    key: str
    title: str
    purpose: str
    produces: str
    required_columns: tuple[str, ...]
    optional_columns: tuple[str, ...]
    key_columns: tuple[str, ...]
    fallback_path: str


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    row_count: int
    column_count: int
    missing_required_cells: int
    duplicate_keys: int
    municipality_count: int
    period_label: str
    consistency_status: str

    @property
    def quality_status(self) -> str:
        if self.errors:
            return "REJECTED"
        if self.warnings:
            return "REVIEW"
        return "ACCEPTED"


DATASET_SPECS: dict[str, DatasetSpec] = {
    "reference_core": DatasetSpec(
        key="reference_core",
        title="1. Бюджетный Reference Core",
        purpose=(
            "Нужен для расчета отклонения доходов от первоначального плана, "
            "доли программных расходов, числа изменений бюджета и долговой нагрузки."
        ),
        produces="Fiscal Reference Panel и основные Reference-признаки.",
        required_columns=(
            "year", "municipality_name", "tax_initial", "nontax_initial",
            "tax_actual", "nontax_actual", "program_expense", "total_expense",
            "budget_amendments", "municipal_debt", "own_revenue_base",
        ),
        optional_columns=(),
        key_columns=("year", "municipality_name"),
        fallback_path="data/processed/official_quality_core_inputs_2023_2025.csv",
    ),
    "quality_rankings": DatasetSpec(
        key="quality_rankings",
        title="2. Официальные рейтинги качества",
        purpose=(
            "Дополняет Reference Panel официальным рангом и флагом высокой "
            "дотационности по статье 136, если эти поля есть в источнике."
        ),
        produces="quality_rank и article136_high_subsidy_flag.",
        required_columns=("year", "municipality_name", "rank"),
        optional_columns=(
            "article136_high_subsidy_flag", "quality_score_workbook_value",
            "budget_law_violation_count", "source_file", "source_sheet",
        ),
        key_columns=("year", "municipality_name"),
        fallback_path="data/processed/official_quality_rankings_2023_2025.csv",
    ),
    "budget_provision": DatasetSpec(
        key="budget_provision",
        title="3. Бюджетная обеспеченность (БО)",
        purpose=(
            "Нужна для фискального контекста: сравнения фактической и расчетной "
            "бюджетной обеспеченности, обязательств и недостатка доходов."
        ),
        produces="Вкладка БО, история БО и блок БО в итоговом отчете.",
        required_columns=("year", "period", "period_end", "municipality_name", "bo_actual", "bo_calculated"),
        optional_columns=(
            "population", "estimated_revenue", "estimated_obligations",
            "revenue_shortfall", "equalization_support", "source_file", "source_status",
        ),
        key_columns=("year", "period", "municipality_name"),
        fallback_path="data/processed/budget_provision_history_2021_2023.csv",
    ),
    "budget_official_plan": DatasetSpec(
        key="budget_official_plan",
        title="4. Официальные параметры бюджета",
        purpose="Утвержденные доходы, расходы, дефицит, трансферты и долговые параметры.",
        produces="Автоматический расчет Budget Normalization без ручного ввода.",
        required_columns=(
            "year", "municipality_name", "stage", "total_revenue",
            "revenue_base", "transfers", "expenditure", "deficit",
            "financing_sources", "eligible_exceptions", "source_url", "publication_date",
        ),
        optional_columns=(
            "debt_upper_limit", "debt_service", "exceptions_status",
            "source_document", "notes",
        ),
        key_columns=("year", "municipality_name", "stage"),
        fallback_path="data/processed/official_budget_plan_surgut_2025_2027.csv",
    ),
    "budget_project": DatasetSpec(
        key="budget_project",
        title="5. Структура проекта бюджета",
        purpose="Структура доходов, расходов, финансирования и допустимых исключений.",
        produces="Автозаполнение Budget Normalization и структура статей.",
        required_columns=(
            "year", "municipality_name", "budget_side", "group", "item_name", "amount",
        ),
        optional_columns=(
            "item_code", "is_transfer", "is_recurring", "is_subvention",
            "is_debt_service", "is_borrowing", "flexibility", "source_file", "notes",
        ),
        key_columns=("year", "municipality_name", "budget_side", "group", "item_name"),
        fallback_path="data/processed/official_budget_project_surgut_2025.csv",
    ),
    "external_monthly": DatasetSpec(
        key="external_monthly",
        title="6. External / Predictive Proxy",
        purpose=(
            "Нужен для подключения месячных или недельных внешних факторов: "
            "CPI, fuel, FX, oil, income, employment и других разрешенных агрегатов."
        ),
        produces=(
            "External Data Layer, coverage-контроль и Forecast vs Actual benchmark. "
            "Сам по себе этот файл еще не создает реальный EARLY_WARNING."
        ),
        required_columns=(
            "period", "geography_name", "geography_level", "variable",
            "value", "unit", "source", "publication_date", "as_of_date",
        ),
        optional_columns=("source_url", "oktmo", "notes"),
        key_columns=("period", "geography_name", "variable"),
        fallback_path="data/processed/external_monthly.csv",
    ),
}


def _normalise_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out.columns = [str(col).strip().lstrip("\ufeff") for col in out.columns]
    return out


def list_excel_sheets(filename: str, content: bytes) -> list[str]:
    suffix = Path(filename).suffix.lower()
    if suffix not in {".xlsx", ".xlsm"}:
        return []
    with pd.ExcelFile(BytesIO(content), engine="openpyxl") as book:
        return list(book.sheet_names)


def read_uploaded_table(filename: str, content: bytes, sheet_name: str | None = None) -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        last_error: Exception | None = None
        for encoding in ("utf-8-sig", "utf-8", "cp1251"):
            try:
                text = content.decode(encoding)
                return _normalise_columns(pd.read_csv(StringIO(text), sep=None, engine="python"))
            except Exception as exc:
                last_error = exc
        raise ValueError(f"Не удалось прочитать CSV: {last_error}")

    if suffix in {".xlsx", ".xlsm"}:
        return _normalise_columns(pd.read_excel(
            BytesIO(content),
            sheet_name=sheet_name if sheet_name is not None else 0,
            engine="openpyxl",
        ))

    if suffix == ".xls":
        raise ValueError(
            "Старый .xls пока не принимается через визуальный загрузчик. "
            "Для него нужен отдельный legacy parser."
        )
    raise ValueError("Поддерживаются .csv, .xlsx и .xlsm.")


def _period_label(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "—"
    if "year" in frame.columns:
        years = pd.to_numeric(frame["year"], errors="coerce").dropna().astype(int)
        if not years.empty:
            start, end = int(years.min()), int(years.max())
            return str(start) if start == end else f"{start}–{end}"
    if "period" in frame.columns:
        periods = pd.to_datetime(frame["period"], errors="coerce").dropna()
        if not periods.empty:
            start = periods.min().strftime("%Y-%m")
            end = periods.max().strftime("%Y-%m")
            return start if start == end else f"{start}–{end}"
    return "—"


def _consistency_warnings(dataset_key: str, frame: pd.DataFrame) -> list[str]:
    warnings: list[str] = []

    if dataset_key == "reference_core":
        numeric = frame.copy()
        for col in (
            "program_expense", "total_expense", "municipal_debt",
            "own_revenue_base", "tax_initial", "nontax_initial",
            "tax_actual", "nontax_actual",
        ):
            if col in numeric.columns:
                numeric[col] = pd.to_numeric(numeric[col], errors="coerce")

        if {"program_expense", "total_expense"}.issubset(numeric.columns):
            bad = int((numeric["program_expense"] > numeric["total_expense"]).fillna(False).sum())
            if bad:
                warnings.append(f"В {bad} строках program_expense больше total_expense.")
        for column in ("municipal_debt", "own_revenue_base", "total_expense"):
            if column in numeric.columns:
                bad = int((numeric[column] < 0).fillna(False).sum())
                if bad:
                    warnings.append(f"В колонке {column} отрицательных значений: {bad}.")

    if dataset_key == "quality_rankings" and "rank" in frame.columns:
        ranks = pd.to_numeric(frame["rank"], errors="coerce")
        bad = int((ranks <= 0).fillna(False).sum())
        if bad:
            warnings.append(f"Неположительных rank: {bad}.")

    if dataset_key == "budget_provision":
        needed = {"estimated_revenue", "estimated_obligations", "revenue_shortfall"}
        if needed.issubset(frame.columns):
            revenue = pd.to_numeric(frame["estimated_revenue"], errors="coerce")
            obligations = pd.to_numeric(frame["estimated_obligations"], errors="coerce")
            shortfall = pd.to_numeric(frame["revenue_shortfall"], errors="coerce")
            expected = obligations - revenue
            tolerance = expected.abs().clip(lower=1.0) * 0.001
            comparable = expected.notna() & shortfall.notna()
            bad = int((comparable & ((expected - shortfall).abs() > tolerance)).sum())
            if bad:
                warnings.append(
                    f"В {bad} строках revenue_shortfall не совпадает с obligations − revenue "
                    "в пределах допуска 0.1%."
                )
    return warnings


def validate_dataset(dataset_key: str, frame: pd.DataFrame) -> ValidationResult:
    spec = DATASET_SPECS[dataset_key]
    frame = _normalise_columns(frame)
    errors: list[str] = []
    warnings: list[str] = []

    if frame.empty:
        errors.append("Файл не содержит строк данных.")

    duplicated_columns = frame.columns[frame.columns.duplicated()].tolist()
    if duplicated_columns:
        errors.append("Повторяющиеся колонки: " + ", ".join(map(str, duplicated_columns)))

    missing_columns = [col for col in spec.required_columns if col not in frame.columns]
    if missing_columns:
        errors.append("Не хватает обязательных колонок: " + ", ".join(missing_columns))

    present_required = [col for col in spec.required_columns if col in frame.columns]
    missing_required_cells = int(frame[present_required].isna().sum().sum()) if present_required else 0
    if missing_required_cells:
        errors.append(f"Пустых ячеек в обязательных колонках: {missing_required_cells}.")

    duplicate_keys = 0
    if all(col in frame.columns for col in spec.key_columns):
        duplicate_keys = int(frame.duplicated(list(spec.key_columns), keep=False).sum())
        if duplicate_keys:
            warnings.append(f"Строк с повторяющимся логическим ключом: {duplicate_keys}.")

    if "municipality_name" in frame.columns:
        names = frame["municipality_name"].astype("string").str.strip()
        blank = names.eq("").fillna(True)
        blank_count = int(blank.sum())
        if blank_count:
            errors.append(f"Пустых municipality_name: {blank_count}.")
        numeric_only = int(names.str.fullmatch(r"\d+").fillna(False).sum())
        if numeric_only:
            errors.append(
                f"В municipality_name найдено числовых кодов вместо названий: {numeric_only}. "
                "Для кода используйте отдельное поле OKTMO, а здесь укажите название муниципалитета."
            )

    if "year" in frame.columns:
        years = pd.to_numeric(frame["year"], errors="coerce")
        bad_years = int(years.isna().sum())
        if bad_years:
            errors.append(f"Некорректных значений year: {bad_years}.")

    if "period_end" in frame.columns:
        dates = pd.to_datetime(frame["period_end"], errors="coerce")
        bad_dates = int(dates.isna().sum())
        if bad_dates:
            errors.append(f"Некорректных period_end: {bad_dates}.")

    if dataset_key == "budget_official_plan":
        for column in (
            "total_revenue", "revenue_base", "transfers", "expenditure",
            "deficit", "financing_sources", "eligible_exceptions",
        ):
            if column in frame.columns:
                values = pd.to_numeric(frame[column], errors="coerce")
                bad = int(values.isna().sum())
                if bad:
                    errors.append(f"Некорректных {column}: {bad}.")
                negative = int((values < 0).fillna(False).sum())
                if negative:
                    errors.append(f"Отрицательных {column}: {negative}.")

        if {"total_revenue", "revenue_base", "transfers"}.issubset(frame.columns):
            total = pd.to_numeric(frame["total_revenue"], errors="coerce")
            base = pd.to_numeric(frame["revenue_base"], errors="coerce")
            transfers = pd.to_numeric(frame["transfers"], errors="coerce")
            tolerance = total.abs().clip(lower=1.0) * 0.001
            mismatch = ((base + transfers - total).abs() > tolerance).fillna(False)
            if int(mismatch.sum()):
                warnings.append("revenue_base + transfers не совпадает с total_revenue в пределах 0.1%.")

        if {"total_revenue", "expenditure", "deficit"}.issubset(frame.columns):
            total = pd.to_numeric(frame["total_revenue"], errors="coerce")
            expenditure = pd.to_numeric(frame["expenditure"], errors="coerce")
            deficit = pd.to_numeric(frame["deficit"], errors="coerce")
            expected = (expenditure - total).clip(lower=0)
            tolerance = expected.abs().clip(lower=1.0) * 0.001
            mismatch = ((expected - deficit).abs() > tolerance).fillna(False)
            if int(mismatch.sum()):
                warnings.append("deficit не совпадает с expenditure - total_revenue в пределах 0.1%.")

    if dataset_key == "budget_project":
        sides = frame.get("budget_side", pd.Series(dtype="string")).astype("string").str.upper().str.strip()
        allowed_sides = {"REVENUE", "EXPENDITURE", "FINANCING", "EXCEPTION"}
        bad_sides = sorted(set(sides.dropna()) - allowed_sides)
        if bad_sides:
            errors.append("Некорректные budget_side: " + ", ".join(map(str, bad_sides)))

        if "amount" in frame.columns:
            amounts = pd.to_numeric(frame["amount"], errors="coerce")
            bad_amounts = int(amounts.isna().sum())
            if bad_amounts:
                errors.append(f"Некорректных amount: {bad_amounts}.")
            negative_amounts = int((amounts < 0).fillna(False).sum())
            if negative_amounts:
                errors.append(f"Отрицательных amount: {negative_amounts}.")

        if "flexibility" in frame.columns:
            flexibility = frame["flexibility"].astype("string").str.upper().str.strip()
            allowed_flex = {"FIXED", "PARTIAL", "FLEXIBLE", "UNKNOWN"}
            bad_flex = sorted(set(flexibility.dropna()) - allowed_flex)
            if bad_flex:
                errors.append("Некорректные flexibility: " + ", ".join(map(str, bad_flex)))

    if dataset_key == "external_monthly":
        period_dates = pd.to_datetime(frame.get("period"), errors="coerce")
        bad_periods = int(period_dates.isna().sum())
        if bad_periods:
            errors.append(f"Некорректных period: {bad_periods}.")
        for date_column in ("publication_date", "as_of_date"):
            dates = pd.to_datetime(frame.get(date_column), errors="coerce")
            bad = int(dates.isna().sum())
            if bad:
                errors.append(f"Некорректных {date_column}: {bad}.")
        values = pd.to_numeric(frame.get("value"), errors="coerce")
        bad_values = int(values.isna().sum())
        if bad_values:
            errors.append(f"Некорректных value: {bad_values}.")
        future_leak = (
            pd.to_datetime(frame.get("as_of_date"), errors="coerce")
            < pd.to_datetime(frame.get("publication_date"), errors="coerce")
        )
        if int(future_leak.fillna(False).sum()):
            warnings.append(
                "Есть строки, где as_of_date раньше publication_date. "
                "Проверьте as-of semantics, чтобы исключить утечку будущих данных."
            )

    consistency = _consistency_warnings(dataset_key, frame)
    warnings.extend(consistency)

    extra = [c for c in frame.columns if c not in spec.required_columns and c not in spec.optional_columns]
    if extra:
        warnings.append(
            "Дополнительные колонки будут сохранены, но текущий расчет их не использует: "
            + ", ".join(map(str, extra[:12]))
        )

    entity_column = "municipality_name" if "municipality_name" in frame.columns else (
        "geography_name" if "geography_name" in frame.columns else None
    )
    municipality_count = (
        int(frame[entity_column].dropna().astype(str).str.strip().replace("", pd.NA).nunique())
        if entity_column is not None else 0
    )

    return ValidationResult(
        valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
        row_count=len(frame),
        column_count=len(frame.columns),
        missing_required_cells=missing_required_cells,
        duplicate_keys=duplicate_keys,
        municipality_count=municipality_count,
        period_label=_period_label(frame),
        consistency_status="REVIEW" if consistency else "OK",
    )


def template_csv(dataset_key: str) -> bytes:
    spec = DATASET_SPECS[dataset_key]
    return (",".join(list(spec.required_columns) + list(spec.optional_columns)) + "\n").encode("utf-8-sig")


def _safe_name(value: str) -> str:
    stem = Path(value).stem
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("_")
    return clean[:80] or "upload"


def file_sha256(content: bytes) -> str:
    return sha256(content).hexdigest()


def resolve_dataset_path(dataset_key: str, root: Path) -> Path:
    active = root / "data" / "intake" / "active" / f"{dataset_key}.csv"
    return active if active.exists() else root / DATASET_SPECS[dataset_key].fallback_path


def load_current_dataset(dataset_key: str, root: Path) -> pd.DataFrame:
    path = resolve_dataset_path(dataset_key, root)
    if not path.exists():
        return pd.DataFrame()
    return _normalise_columns(pd.read_csv(path, encoding="utf-8-sig"))


def _row_signature(row: pd.Series, columns: list[str]) -> tuple[str, ...]:
    values: list[str] = []
    for column in columns:
        value = row.get(column)
        if pd.isna(value):
            values.append("<NA>")
        elif isinstance(value, float):
            values.append(f"{value:.12g}")
        else:
            values.append(str(value).strip())
    return tuple(values)


def compare_frames(before: pd.DataFrame, after: pd.DataFrame, key_columns: tuple[str, ...]) -> dict[str, object]:
    if before.empty:
        return {
            "before_rows": 0, "after_rows": len(after), "row_delta": len(after),
            "added_keys": len(after), "removed_keys": 0, "changed_keys": 0,
            "changed_municipalities": sorted(
                after[
                    "municipality_name" if "municipality_name" in after.columns else "geography_name"
                ].dropna().astype(str).unique().tolist()
            ) if ("municipality_name" in after.columns or "geography_name" in after.columns) else [],
        }

    before = _normalise_columns(before)
    after = _normalise_columns(after)
    common_columns = sorted((set(before.columns) & set(after.columns)) - set(key_columns))
    usable_keys = [k for k in key_columns if k in before.columns and k in after.columns]
    if not usable_keys:
        return {
            "before_rows": len(before), "after_rows": len(after),
            "row_delta": len(after) - len(before), "added_keys": 0,
            "removed_keys": 0, "changed_keys": 0, "changed_municipalities": [],
        }

    b = before.drop_duplicates(usable_keys, keep="last").set_index(usable_keys, drop=False)
    a = after.drop_duplicates(usable_keys, keep="last").set_index(usable_keys, drop=False)
    before_keys, after_keys = set(b.index.tolist()), set(a.index.tolist())
    added, removed = after_keys - before_keys, before_keys - after_keys
    common = before_keys & after_keys

    changed: list[object] = []
    for key in common:
        if _row_signature(b.loc[key], common_columns) != _row_signature(a.loc[key], common_columns):
            changed.append(key)

    municipalities: set[str] = set()
    entity_key = "municipality_name" if "municipality_name" in usable_keys else (
        "geography_name" if "geography_name" in usable_keys else None
    )
    if entity_key is not None:
        pos = usable_keys.index(entity_key)
        for key in list(added) + list(removed) + changed:
            municipalities.add(str(key if len(usable_keys) == 1 else key[pos]))

    return {
        "before_rows": len(before), "after_rows": len(after),
        "row_delta": len(after) - len(before), "added_keys": len(added),
        "removed_keys": len(removed), "changed_keys": len(changed),
        "changed_municipalities": sorted(municipalities),
    }


def compare_to_current(dataset_key: str, incoming: pd.DataFrame, root: Path) -> dict[str, object]:
    return compare_frames(
        load_current_dataset(dataset_key, root),
        incoming,
        DATASET_SPECS[dataset_key].key_columns,
    )


def persist_dataset(
    dataset_key: str,
    frame: pd.DataFrame,
    original_name: str,
    original_content: bytes,
    root: Path,
) -> dict[str, str | int]:
    validation = validate_dataset(dataset_key, frame)
    if not validation.valid:
        raise ValueError("Файл не прошел валидацию: " + "; ".join(validation.errors))

    intake_root = root / "data" / "intake"
    active_dir = intake_root / "active"
    history_dir = intake_root / "history" / dataset_key
    active_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    canonical = _normalise_columns(frame)
    history_path = history_dir / f"{timestamp}__{_safe_name(original_name)}.csv"
    active_path = active_dir / f"{dataset_key}.csv"
    canonical.to_csv(history_path, index=False, encoding="utf-8-sig")
    canonical.to_csv(active_path, index=False, encoding="utf-8-sig")

    log_path = intake_root / "intake_log.csv"
    log_exists = log_path.exists()
    row = {
        "accepted_at": datetime.now().isoformat(timespec="seconds"),
        "dataset_key": dataset_key,
        "source_filename": original_name,
        "source_sha256": file_sha256(original_content),
        "quality_status": validation.quality_status,
        "rows": len(canonical),
        "columns": len(canonical.columns),
        "municipalities": validation.municipality_count,
        "period": validation.period_label,
        "active_path": str(active_path.relative_to(root)),
        "history_path": str(history_path.relative_to(root)),
    }
    with log_path.open("a", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(row.keys()))
        if not log_exists:
            writer.writeheader()
        writer.writerow(row)
    return row


def dataset_status(dataset_key: str, root: Path) -> dict[str, object]:
    spec = DATASET_SPECS[dataset_key]
    active = root / "data" / "intake" / "active" / f"{dataset_key}.csv"
    path = resolve_dataset_path(dataset_key, root)
    if not path.exists():
        return {
            "dataset_key": dataset_key, "title": spec.title, "mode": "нет данных",
            "rows": 0, "municipalities": 0, "period": "—", "quality": "MISSING",
            "modified": "", "sha256": "", "path": str(path),
        }

    raw = path.read_bytes()
    frame = pd.read_csv(path, encoding="utf-8-sig")
    validation = validate_dataset(dataset_key, frame)
    return {
        "dataset_key": dataset_key,
        "title": spec.title,
        "mode": "загруженный" if active.exists() else "встроенный baseline",
        "rows": len(frame),
        "municipalities": validation.municipality_count,
        "period": validation.period_label,
        "quality": validation.quality_status,
        "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        "sha256": file_sha256(raw)[:12],
        "path": str(path.relative_to(root)),
    }


def recent_intake_log(root: Path, limit: int = 10) -> pd.DataFrame:
    path = root / "data" / "intake" / "intake_log.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig").tail(limit).iloc[::-1].reset_index(drop=True)
