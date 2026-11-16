"""시나리오별 가상 환율 CSV와 기대 결과 JSON을 결정적으로 생성한다.

실행: python scripts/make_scenarios.py
출력: data/scenario_<name>.csv, docs/sample_result_<name>.json
모든 데이터는 기능 시연용 가상 데이터이며 공식 환율이 아니다.
"""
import json
import math
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.fx_core import Rate, calculate  # noqa: E402

START = date(2026, 8, 3)
DAYS = 75  # 영업일(월~금) 75개
# 시나리오: 마지막 값을 3개월 평균 대비 목표 괴리율(%)로 조정
SCENARIOS = {'normal': -1.0, 'caution': -5.0, 'risk': -8.5, 'critical': -12.0}


def weekdays(start, n):
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def build(target_dev):
    days = weekdays(START, DAYS)
    values = [round(1400 + 12 * math.sin(i / 7), 2) for i in range(DAYS - 1)]
    # 마지막 값을 반복 보정: 평균에 자기 자신이 포함되므로 몇 번 수렴시킨다
    last = values[-1]
    for _ in range(50):
        rates = [Rate(d, v) for d, v in zip(days, values + [last])]
        dev = calculate(rates)['deviation_pct']
        last = round(last * (1 + (target_dev - dev) / 100), 2)
    return days, values + [last]


def main():
    for name, target in SCENARIOS.items():
        days, values = build(target)
        csv_path = ROOT / 'data' / f'scenario_{name}.csv'
        lines = ['date,usd_krw'] + [f'{d.isoformat()},{v}' for d, v in zip(days, values)]
        csv_path.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
        result = calculate([Rate(d, v) for d, v in zip(days, values)])
        (ROOT / 'docs' / f'sample_result_{name}.json').write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        print(f"{name:9s} {result['risk']:9s} dev={result['deviation_pct']:8.4f}% rec={result['recommended']}")


if __name__ == '__main__':
    main()
