from mesm.ingest.surgut_budget import parse_adopted_budget, extract_expenditure_sections


def test_parse_adopted_budget_from_labels_and_formulas_only():
    revenue = [
        ["Доходы бюджета", None, None, None],
        ["Наименование", "2025 год", "2026 год", "2027 год"],
        ["ВСЕГО", 1000, 1100, 1200],
        ["НАЛОГОВЫЕ И НЕНАЛОГОВЫЕ ДОХОДЫ", 400, 500, 600],
        ["БЕЗВОЗМЕЗДНЫЕ ПОСТУПЛЕНИЯ", 600, 600, 600],
    ]
    financing = [
        ["Наименование", "2025 год", "2026 год", "2027 год"],
        ["ВСЕГО", 150, 120, 80],
        ["Изменение остатков средств", 70, 0, 0],
        ["Поступления от продажи акций и иных форм участия в капитале", 0, 25, 0],
    ]
    expenditure = [
        ["Код", "Наименование", "2025 год", "2026 год", "2027 год"],
        ["", "ВСЕГО", 1150, 1220, 1280],
        ["13", "Обслуживание муниципального долга", 10, 20, 30],
    ]

    result = parse_adopted_budget(revenue, financing, expenditure)
    by_year = {row.year: row for row in result}
    assert by_year[2025].revenue_base == 400
    assert by_year[2025].transfers == 600
    assert by_year[2025].deficit == 150
    assert by_year[2025].eligible_exceptions == 70
    assert by_year[2026].eligible_exceptions == 25
    assert by_year[2027].eligible_exceptions == 0
    assert by_year[2027].debt_service == 30


def test_extracts_top_level_expenditure_sections():
    rows = [
        ["Код", "Наименование", "2025 год", "2026 год", "2027 год"],
        ["01", "Общегосударственные вопросы", 100, 110, 120],
        ["0102", "Подраздел", 50, 55, 60],
        ["04", "Национальная экономика", 200, 210, 220],
    ]
    result = extract_expenditure_sections(rows)
    assert {(r["year"], r["section_code"]) for r in result} == {
        (2025, "01"), (2026, "01"), (2027, "01"),
        (2025, "04"), (2026, "04"), (2027, "04"),
    }


def test_debt_limits_are_parsed_from_decision_text():
    from mesm.ingest.surgut_budget import parse_debt_limits_text

    text = """
    Утвердить верхний предел муниципального внутреннего долга:
    на 01.01.2026 в объёме 1 145 352 694,99 рубля;
    на 01.01.2027 в объёме 2 845 405 559,11 рубля;
    на 01.01.2028 в объёме 3 916 687 251,86 рубля.
    """
    assert parse_debt_limits_text(text) == {
        2025: 1145352694.99,
        2026: 2845405559.11,
        2027: 3916687251.86,
    }
