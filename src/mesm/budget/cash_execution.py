from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Literal

from mesm.features.fiscal import execution_gap, execution_rate


Side = Literal["REVENUE", "EXPENDITURE", "FINANCING"]
Source = Literal["UFK_CASH", "REPORT_0503117", "FNS_TAX"]
Kind = Literal["REFUND_REALLOCATION", "ONE_OFF", "ADVANCE_REALLOCATION", "CARRYOVER"]


@dataclass(frozen=True)
class CashLine:
    municipality: str
    month: date
    kbk: str
    side: Side
    amount: float
    source: Source
    available_at: date
    source_document: str
    period_basis: Literal["MONTH", "YTD"] = "MONTH"
    preliminary: bool = True


@dataclass(frozen=True)
class ManualCorrection:
    correction_id: str
    kind: Kind
    municipality: str
    kbk: str
    side: Side
    cash_month: date
    amount: float
    reason: str
    evidence: str
    approved_by: str
    approved_at: date
    target_month: date | None = None


@dataclass(frozen=True)
class CashMonth:
    month: date
    raw_revenue: float
    raw_expenditure: float
    raw_financing: float
    normalized_revenue: float
    normalized_expenditure: float
    recurring_balance: float
    cash_balance: float
    reserve_need: float
    real_recurring_balance: float | None
    seasonal_balance: float | None
    status: Literal["OBSERVED", "ADJUSTED"]


@dataclass(frozen=True)
class OperationalBridge:
    month: date
    raw_revenue_execution_rate: float | None
    raw_expenditure_execution_rate: float | None
    normalized_revenue_gap: float | None
    normalized_expenditure_gap: float | None
    cash_reserve_need: float
    recurring_balance: float
    basis: str = "ANALYTICAL_MONTHLY"


def cash_vs_monthly_plan(month: CashMonth, *, planned_revenue: float,
                         planned_expenditure: float) -> OperationalBridge:
    if planned_revenue < 0 or planned_expenditure < 0:
        raise ValueError("Месячный план не может быть отрицательным")
    return OperationalBridge(month.month,
                             execution_rate(planned_revenue, month.raw_revenue),
                             execution_rate(planned_expenditure, month.raw_expenditure),
                             execution_gap(planned_revenue, month.normalized_revenue),
                             execution_gap(planned_expenditure, month.normalized_expenditure),
                             month.reserve_need, month.recurring_balance)


def _month(value: date) -> date:
    if value.day != 1:
        raise ValueError("Месяц должен быть датой первого числа")
    return value


def monthly_from_ytd(lines: list[CashLine]) -> list[CashLine]:
    previous: dict[tuple[str, str, Side, Source, int], tuple[int, float]] = {}
    result: list[CashLine] = []
    for line in sorted(lines, key=lambda row: (row.month, row.kbk, row.side)):
        _month(line.month)
        if line.period_basis == "MONTH":
            result.append(line)
            continue
        key = (line.municipality, line.kbk, line.side, line.source, line.month.year)
        if key in previous:
            prev_month, prev_total = previous[key]
            if line.month.month != prev_month + 1:
                raise ValueError(f"Пропуск месячного отчёта по КБК {line.kbk}")
        elif line.month.month != 1:
            raise ValueError(f"Нет январской базы для КБК {line.kbk}")
        else:
            prev_total = 0.0
        result.append(CashLine(line.municipality, line.month, line.kbk, line.side,
                               line.amount - prev_total, line.source, line.available_at,
                               line.source_document, "MONTH", line.preliminary))
        previous[key] = (line.month.month, line.amount)
    return result


def normalize_cash(lines: list[CashLine], corrections: list[ManualCorrection], *,
                   as_of: date, municipality: str, source: Source,
                   deflators: dict[date, float] | None = None,
                   season_factors: dict[tuple[date, str], float] | None = None,
                   opening_balance: float = 0.0) -> list[CashMonth]:
    if opening_balance < 0 or not isfinite(opening_balance):
        raise ValueError("Начальный остаток должен быть конечным и неотрицательным")
    chosen = [row for row in lines if row.municipality == municipality and row.source == source
              and row.available_at <= as_of]
    if source == "REPORT_0503117":
        latest: dict[tuple[date, str, Side], CashLine] = {}
        for row in chosen:
            key = (row.month, row.kbk, row.side)
            if key in latest and row.available_at == latest[key].available_at:
                raise ValueError("Повтор строки КБК в одном срезе отчёта")
            if key not in latest or row.available_at > latest[key].available_at:
                latest[key] = row
        chosen = list(latest.values())
    if any(row.period_basis != "MONTH" for row in chosen):
        raise ValueError("Сначала преобразуйте накопленные значения формы 0503117 в месячные")
    if not chosen:
        return []
    raw: dict[date, dict[Side, float]] = {}
    by_key: dict[tuple[date, str, Side], float] = {}
    for row in chosen:
        _month(row.month)
        if not row.source_document or not row.kbk or not isfinite(row.amount):
            raise ValueError("Нужны документ, КБК и конечная сумма")
        if row.side not in ("REVENUE", "EXPENDITURE", "FINANCING"):
            raise ValueError("Неизвестная сторона бюджета")
        raw.setdefault(row.month, {"REVENUE": 0.0, "EXPENDITURE": 0.0, "FINANCING": 0.0})[row.side] += row.amount
        key = (row.month, row.kbk, row.side)
        by_key[key] = by_key.get(key, 0.0) + row.amount
    adjusted = {month: dict(values) for month, values in raw.items()}
    adjusted_key = dict(by_key)
    carryover_by_month: dict[date, float] = {}
    used: set[str] = set()
    allocated: dict[tuple[date, str, Side, Kind], float] = {}
    positive_exclusions: dict[tuple[date, str, Side], float] = {}
    for correction in corrections:
        if correction.municipality != municipality or correction.approved_at > as_of:
            continue
        if correction.correction_id in used:
            raise ValueError("Повторный идентификатор корректировки")
        used.add(correction.correction_id)
        if (not correction.correction_id or not correction.reason or not correction.evidence
                or not correction.approved_by or not isfinite(correction.amount) or correction.amount <= 0):
            raise ValueError("Корректировка требует основания, утверждения и положительной суммы")
        if correction.cash_month not in raw or correction.approved_at < correction.cash_month:
            raise ValueError("Корректировка не соответствует доступному кассовому месяцу")
        observed = by_key.get((correction.cash_month, correction.kbk, correction.side), 0.0)
        cash_key = (correction.cash_month, correction.kbk, correction.side)
        allocation_key = (correction.cash_month, correction.kbk, correction.side, correction.kind)
        allocated[allocation_key] = allocated.get(allocation_key, 0.0) + correction.amount
        if correction.kind in ("ONE_OFF", "ADVANCE_REALLOCATION", "CARRYOVER"):
            positive_exclusions[cash_key] = positive_exclusions.get(cash_key, 0.0) + correction.amount
            if positive_exclusions[cash_key] > observed:
                raise ValueError("Совокупные исключения превышают кассовую строку")
        if correction.kind == "REFUND_REALLOCATION":
            if observed >= 0 or correction.side != "REVENUE" or allocated[allocation_key] > -observed:
                raise ValueError("Возврат должен соответствовать отрицательной строке доходов")
            if correction.target_month is None or correction.target_month >= correction.cash_month:
                raise ValueError("Период начисления должен предшествовать возврату")
            delta = correction.amount
        elif correction.kind == "ADVANCE_REALLOCATION":
            if correction.side != "REVENUE" or observed < allocated[allocation_key]:
                raise ValueError("Аванс не подтверждён поступлением")
            if correction.target_month is None or correction.target_month <= correction.cash_month:
                raise ValueError("Период использования аванса должен быть позже платежа")
            delta = -correction.amount
        elif correction.kind in ("ONE_OFF", "CARRYOVER"):
            if observed < allocated[allocation_key]:
                raise ValueError("Исключаемая сумма превышает кассовую строку")
            if correction.kind == "CARRYOVER" and correction.side != "FINANCING":
                raise ValueError("Переходящий остаток относится к финансированию, а не к доходам")
            if correction.target_month is not None:
                raise ValueError("Для исключения не нужен целевой месяц")
            delta = -correction.amount
            if correction.kind == "CARRYOVER":
                carryover_by_month[correction.cash_month] = carryover_by_month.get(correction.cash_month, 0.0) + correction.amount
        else:
            raise ValueError("Неизвестный вид корректировки")
        adjusted[correction.cash_month][correction.side] += delta
        adjusted_key[(correction.cash_month, correction.kbk, correction.side)] += delta
        if correction.target_month is not None:
            _month(correction.target_month)
            if correction.target_month not in raw:
                raise ValueError("Нет наблюдения за целевой месяц")
            adjusted[correction.target_month][correction.side] -= delta
            key = (correction.target_month, correction.kbk, correction.side)
            adjusted_key[key] = adjusted_key.get(key, 0.0) - delta

    result: list[CashMonth] = []
    balance = opening_balance
    for month in sorted(raw):
        r, a = raw[month], adjusted[month]
        balance += r["REVENUE"] + r["FINANCING"] - carryover_by_month.get(month, 0.0) - r["EXPENDITURE"]
        recurring = a["REVENUE"] - a["EXPENDITURE"]
        deflator = None if deflators is None else deflators.get(month)
        if deflator is not None and (not isfinite(deflator) or deflator <= 0):
            raise ValueError("Дефлятор должен быть положительным")
        seasonal_balance = None
        if season_factors is not None:
            seasonal_balance = 0.0
            for (line_month, kbk, side), value in adjusted_key.items():
                if line_month != month or side == "FINANCING":
                    continue
                factor = season_factors.get((month, kbk))
                if factor is None or not isfinite(factor) or factor <= 0:
                    raise ValueError(f"Нет сезонного коэффициента для {kbk} за {month}")
                seasonal_balance += value / factor * (1 if side == "REVENUE" else -1)
        result.append(CashMonth(month, r["REVENUE"], r["EXPENDITURE"], r["FINANCING"],
                                a["REVENUE"], a["EXPENDITURE"], recurring,
                                balance, max(-balance, 0.0),
                                None if deflator is None else recurring / deflator,
                                seasonal_balance,
                                "ADJUSTED" if a != r else "OBSERVED"))
    return result
