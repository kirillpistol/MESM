"""python scripts/reconcile_sources.py left.csv right.csv --as-of YYYY-MM-DD --output report.json"""
import argparse
import json
from datetime import date
from pathlib import Path
import pandas as pd
from mesm.sources.reconciliation import reconcile

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Сверка внешнего ряда с бюджетным')
    parser.add_argument('left')
    parser.add_argument('right')
    parser.add_argument('--as-of', required=True, type=date.fromisoformat)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    report = reconcile(pd.read_csv(args.left, dtype={'oktmo': str, 'period': str}),
                       pd.read_csv(args.right, dtype={'oktmo': str, 'period': str}), as_of=args.as_of)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
