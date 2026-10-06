"""Human-curated search tasks; AI responses never approve source data."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def fingerprint(criteria):
    """Bind human confirmation to the exact search requirements."""
    return hashlib.sha256(json.dumps(criteria, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def load_directory(root):
    path = Path(root) / "data/search/directory.json"
    if not path.exists():
        path = Path(root) / "config/search_directory.json"
    return json.loads(path.read_text(encoding="utf-8"))


def save_task(root, task_id, criteria, actor, confirm=False):
    """Save requirements and append a review event; changed criteria reset approval."""
    required = ("title", "municipality", "indicator", "period", "unit", "primary_source", "query")
    if not actor.strip() or any(not str(criteria.get(k, "")).strip() for k in required):
        raise ValueError("Заполните автора и все требования поиска")
    directory = load_directory(root)
    existing = next((t for t in directory["tasks"] if t["id"] == task_id), None)
    if existing is None:
        existing = {"id": task_id, "history": []}
        directory["tasks"].append(existing)
    digest = fingerprint(criteria)
    changed = existing.get("criteria_sha256") != digest
    if changed:
        existing["confirmation"] = None
    existing.update(criteria=criteria, criteria_sha256=digest)
    stamp = datetime.now(timezone.utc).isoformat()
    if confirm:
        existing["confirmation"] = {"actor": actor.strip(), "at": stamp, "criteria_sha256": digest}
    existing["history"].append({"actor": actor.strip(), "at": stamp, "criteria_sha256": digest,
                                "action": "confirm_requirements" if confirm else "save_requirements"})
    # Future: authenticated reviewers, source/artifact hashes and parser-specific review gates.
    # Keep local operator records separate from public templates and source validation status.
    path = Path(root) / "data/search/directory.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(directory, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return existing


def build_query(task):
    """Export a prompt only after confirmation of the current requirements."""
    confirmation = task.get("confirmation")
    if not confirmation or confirmation["criteria_sha256"] != fingerprint(task["criteria"]):
        raise ValueError("Сначала подтвердите текущие требования поиска")
    c = task["criteria"]
    # Future AI adapters may return candidates only; they must not validate or import data.
    return (f"Муниципалитет: {c['municipality']}. Показатель: {c['indicator']}. "
            f"Период: {c['period']}. Единица: {c['unit']}. Первичный источник: {c['primary_source']}.\n"
            f"Задача: {c['query']}\n"
            "Укажи прямую ссылку на первичный документ, дату публикации, страницу/строку/ячейку, "
            "формат и ограничения. Не выдумывай отсутствующие значения. Ответ требует проверки человеком.")
