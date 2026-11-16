import argparse
import json
from pathlib import Path
from src.fx_core import calculate, load_rates

parser = argparse.ArgumentParser(description='해외견적 환율 위험도 계산 데모')
parser.add_argument('--csv', default='data/sample_rates.csv')
parser.add_argument('--output', default='result.json')
args = parser.parse_args()
try:
    result = calculate(load_rates(args.csv))
except (OSError, ValueError) as e:
    raise SystemExit(f'오류: {e}')
Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
