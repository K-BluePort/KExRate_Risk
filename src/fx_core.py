from __future__ import annotations
import csv
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import mean

@dataclass(frozen=True)
class Rate:
    day: date
    value: float

def load_rates(path: str | Path) -> list[Rate]:
    rows = []
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        missing = {'date', 'usd_krw'} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f'CSV 헤더 누락: {", ".join(sorted(missing))} (필요: date,usd_krw)')
        for line, item in enumerate(reader, start=2):
            try:
                day = date.fromisoformat((item['date'] or '').strip())
                rate = float((item['usd_krw'] or '').strip())
            except ValueError as e:
                raise ValueError(f'{line}행 값이 올바르지 않습니다: {e}') from None
            if not math.isfinite(rate) or rate <= 0:
                raise ValueError(f'{line}행 환율은 유한한 양수여야 합니다: {rate}')
            rows.append(Rate(day, rate))
    if not rows:
        raise ValueError('환율 데이터가 없습니다')
    if len({x.day for x in rows}) != len(rows):
        raise ValueError('중복 날짜가 존재합니다')
    return sorted(rows, key=lambda x: x.day)

def subtract_months(day: date, months: int) -> date:
    import calendar
    n = day.year * 12 + day.month - 1 - months
    year, month = divmod(n, 12)
    month += 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))

def calculate(rates: list[Rate], as_of: date | None = None) -> dict:
    if not rates:
        raise ValueError('환율 데이터가 없습니다')
    end = as_of or max(r.day for r in rates)
    eligible = sorted((r for r in rates if r.day <= end), key=lambda r: r.day)
    if len(eligible) < 10:
        raise ValueError('10개 이상의 유효 관측값이 필요합니다')
    base = eligible[-1].day
    start = subtract_months(base, 3)
    rolling = [r.value for r in eligible if start <= r.day <= base]
    if len(rolling) < 40:
        raise ValueError('Rolling 3개월 데이터 부족: 최소 40개 관측값 필요')
    current = eligible[-1].value
    avg10 = mean(r.value for r in eligible[-10:])
    avg3 = mean(rolling)
    # 부동소수점 오차로 경계값(-3/-7/-10%)이 어긋나지 않도록 반올림 후 판정
    deviation = round((current / avg3 - 1) * 100, 8)
    if deviation <= -10:
        risk, safety, basis = 'CRITICAL', .05, min(current, avg10)
    elif deviation <= -7:
        risk, safety, basis = 'RISK', .04, min(current, avg10)
    elif deviation < -3:
        risk, safety, basis = 'CAUTION', .03, avg10
    else:
        risk, safety, basis = 'NORMAL', .03, avg3
    raw = basis * (1 - safety)
    # 수출대금 환산 기준: 안전을 위해 5원 단위 내림
    recommended = int(raw // 5) * 5
    return {'as_of': base.isoformat(), 'current': round(current, 4),
            'avg10': round(avg10, 4), 'avg3': round(avg3, 4),
            'deviation_pct': round(deviation, 4), 'risk': risk,
            'safety_pct': safety * 100, 'basis': round(basis, 4),
            'calculated': round(raw, 4), 'recommended': recommended,
            'observations_3m': len(rolling), 'source': 'SAMPLE_NOT_OFFICIAL'}
