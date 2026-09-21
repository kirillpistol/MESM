from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mesm.ingest.dispatcher import classify_source

def test_dispatch():
    assert classify_source("Расчет по итогам 2025 год.xlsx") == "budget_quality"
    assert classify_source("3. Поселения по ст.136 БК РФ на 2026 год.xlsx") == "article136"
    assert classify_source("Сопоставительная таблица ЦСР.xlsx") == "classification_mapping"
