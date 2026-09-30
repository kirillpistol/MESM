from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

TRANSITIONS = {'candidate': {'connected', 'rejected'}, 'connected': {'validated', 'rejected'},
               'validated': {'connected', 'rejected'}, 'rejected': {'candidate'}}


def load_registry(path: str | Path) -> dict:
    registry = json.loads(Path(path).read_text(encoding='utf-8'))
    seen = set()
    for source in registry['external_sources']:
        required = {'id', 'title', 'url', 'format', 'frequency', 'status', 'blocker',
                    'owner', 'added_at', 'validation_metric', 'expected_lag_months'}
        if not required <= source.keys() or source['id'] in seen or source['status'] not in TRANSITIONS:
            raise ValueError('Некорректная запись реестра источников')
        seen.add(source['id'])
    return registry


def transition(path: str | Path, source_id: str, status: str, *, actor: str, evidence: str) -> None:
    if not actor.strip() or not evidence.strip():
        raise ValueError('Нужны исполнитель и доказательство перехода')
    path = Path(path)
    registry = load_registry(path)
    source = next((s for s in registry['external_sources'] if s['id'] == source_id), None)
    if source is None or status not in TRANSITIONS[source['status']]:
        raise ValueError('Недопустимый переход статуса')
    if status == 'connected' and not source.get('artifact_sha256'):
        raise ValueError('Подключение требует контрольной суммы полученного файла')
    if status == 'validated' and not source.get('validation_report'):
        raise ValueError('Валидация требует отчёта сверки')
    registry.setdefault('history', []).append(dict(source_id=source_id, previous=source['status'],
        status=status, actor=actor, evidence=evidence, at=datetime.now(timezone.utc).isoformat()))
    source['status'] = status
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)
