import pytest
from mesm.sources.search_directory import save_task, build_query, load_directory


def test_changed_requirements_invalidate_confirmation_and_keep_history(tmp_path):
    (tmp_path / 'config').mkdir()
    (tmp_path / 'config/search_directory.json').write_text('{"tasks": []}')
    c = dict(title='0503117', municipality='Сургут', indicator='Доходы', period='2025', unit='руб.', primary_source='Документ', query='Найти таблицу')
    task = save_task(tmp_path, 'cash', c, 'Кирилл', True)
    assert 'Сургут' in build_query(task)
    c['unit'] = 'тыс. руб.'
    task = save_task(tmp_path, 'cash', c, 'Кирилл')
    with pytest.raises(ValueError):
        build_query(task)
    task = save_task(tmp_path, 'cash', c, 'Кирилл', True)
    assert 'тыс. руб.' in build_query(task)
    history = load_directory(tmp_path)['tasks'][0]['history']
    assert len(history) == 3
    assert history[0]['criteria_sha256'] != history[1]['criteria_sha256']
    assert history[2]['actor'] == 'Кирилл'


def test_incomplete_requirements_cannot_be_confirmed(tmp_path):
    with pytest.raises(ValueError):
        save_task(tmp_path, 'cash', {}, 'Кирилл', True)
