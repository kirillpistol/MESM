from dataclasses import replace
from datetime import date

import pytest
from mesm.budget.cash_execution import CashLine, ManualCorrection, monthly_from_ytd, normalize_cash


def line(month, amount, **kwargs):
    return CashLine('Сургут', date(2026, month, 1), 'EXP', 'EXPENDITURE', amount,
                    'REPORT_0503117', date(2026, month, 10), 'Отчёт', **kwargs)


def test_ytd_keeps_separate_classifications_and_metadata():
    rows = [line(m, amount, period_basis='YTD', kfsr='0101', kvr=kvr,
                 document_id=f'{m}-{kvr}') for m, amount in [(1, 10), (2, 25)]
            for kvr in ['111', '244']]
    result = monthly_from_ytd(rows)
    assert [r.amount for r in result] == [10, 10, 15, 15]
    assert {r.kvr for r in result} == {'111', '244'}
    assert all(r.document_id and r.kfsr == '0101' for r in result)


def test_effective_date_prevents_early_application():
    row = line(1, 10, period_basis='MONTH')
    correction = ManualCorrection('C1', 'ONE_OFF', 'Сургут', 'EXP', 'EXPENDITURE',
        date(2026, 1, 1), 3, 'Причина', 'Документ', 'Утвердил', date(2026, 1, 15),
        effective_date=date(2026, 3, 1), is_manual=False)
    before = normalize_cash([row], [correction], as_of=date(2026, 2, 1), municipality='Сургут', source='REPORT_0503117')
    after = normalize_cash([row], [correction], as_of=date(2026, 3, 1), municipality='Сургут', source='REPORT_0503117')
    assert before[0].normalized_expenditure == 10
    assert after[0].normalized_expenditure == 7
    assert after[0].raw_expenditure == 10


def test_invalid_classification_or_status_rejected():
    with pytest.raises(ValueError):
        line(1, 1, kfsr='111')
    with pytest.raises(ValueError):
        line(1, 1, preliminary_status='final')
