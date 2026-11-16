import os
import tempfile
import unittest
from datetime import date, timedelta
from src.fx_core import Rate, calculate, load_rates, subtract_months

class FxTest(unittest.TestCase):
    def make(self, last):
        return [Rate(date(2026, 8, 1) + timedelta(days=i), last if i == 90 else 1400.) for i in range(91)]
    def test_normal(self):
        r = calculate(self.make(1400))
        self.assertEqual(r['risk'], 'NORMAL')
        self.assertEqual(r['recommended'], 1355)
    def test_critical(self):
        r = calculate(self.make(1100))
        self.assertEqual(r['risk'], 'CRITICAL')
    def test_month_end(self):
        self.assertEqual(subtract_months(date(2026, 5, 31), 3), date(2026, 2, 28))
    def test_insufficient(self):
        with self.assertRaises(ValueError):
            calculate([Rate(date(2026, 1, 1), 1400)])

class LoadTest(unittest.TestCase):
    def load(self, text):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'r.csv')
            with open(p, 'w', encoding='utf-8', newline='') as f:
                f.write(text)
            return load_rates(p)
    def test_missing_header(self):
        with self.assertRaisesRegex(ValueError, '헤더'):
            self.load('date,rate\n2026-01-01,1400\n')
    def test_empty(self):
        with self.assertRaises(ValueError):
            self.load('date,usd_krw\n')
    def test_bad_values(self):
        for body in ('2026-01-01,abc', 'xx,1400', '2026-01-01,0', '2026-01-01,-5', '2026-01-01,nan'):
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.load('date,usd_krw\n' + body + '\n')
    def test_duplicate(self):
        with self.assertRaisesRegex(ValueError, '중복'):
            self.load('date,usd_krw\n2026-01-01,1\n2026-01-01,2\n')

class AsOfTest(unittest.TestCase):
    def test_as_of_ignores_later_data(self):
        rates = FxTest().make(1400) + [Rate(date(2026, 11, 1), 1000.)]
        r = calculate(rates, as_of=date(2026, 10, 30))
        self.assertEqual(r['as_of'], '2026-10-30')
        self.assertEqual(r['risk'], 'NORMAL')

N = 91  # 2026-08-01 ~ 2026-10-30, 전부 Rolling 3개월 안에 포함
BASE = 1400.0

def series(last, n=N, base=BASE):
    return [Rate(date(2026, 8, 1) + timedelta(days=i), last if i == n - 1 else base) for i in range(n)]

def last_for_deviation(dev_pct):
    """마지막 값을 x, 나머지를 BASE로 둘 때 괴리율이 dev_pct가 되는 x를 해석적으로 역산."""
    r = 1 + dev_pct / 100
    return r * BASE * (N - 1) / (N - r)

class HandCalcTest(unittest.TestCase):
    """TC01: 수기 계산과 일치."""
    def test_caution_case(self):
        # 90일 1400, 마지막 1330
        # avg3 = 1400 - 70/91 = 1399.230769..., avg10 = (9*1400+1330)/10 = 1393
        # deviation = (1330/avg3 - 1)*100 = -4.9477..% -> CAUTION(3%), basis=avg10
        # raw = 1393*0.97 = 1351.21 -> 5원 내림 1350
        r = calculate(series(1330.0))
        self.assertAlmostEqual(r['avg3'], 1400 - 70 / 91, places=4)
        self.assertEqual(r['avg10'], 1393.0)
        self.assertAlmostEqual(r['deviation_pct'], (1330 / (1400 - 70 / 91) - 1) * 100, places=4)
        self.assertEqual(r['risk'], 'CAUTION')
        self.assertEqual(r['safety_pct'], 3)
        self.assertEqual(r['basis'], 1393.0)
        self.assertAlmostEqual(r['calculated'], 1351.21, places=4)
        self.assertEqual(r['recommended'], 1350)
        self.assertEqual(r['observations_3m'], N)
        self.assertEqual(r['source'], 'SAMPLE_NOT_OFFICIAL')

    def test_risk_uses_min_of_current_and_avg10(self):
        r = calculate(series(1280.0))  # 약 -8.5%
        self.assertEqual(r['risk'], 'RISK')
        self.assertEqual(r['safety_pct'], 4)
        self.assertEqual(r['basis'], 1280.0)          # min(1280, avg10=1388)
        self.assertEqual(r['recommended'], 1225)      # 1280*0.96=1228.8 -> 1225

    def test_critical_safety(self):
        r = calculate(series(1100.0))
        self.assertEqual(r['safety_pct'], 5)
        self.assertEqual(r['recommended'], 1045)      # 1100*0.95=1045

class BoundaryTest(unittest.TestCase):
    """TC02: -3/-7/-10% 경계와 직전/직후."""
    def risk(self, dev):
        return calculate(series(last_for_deviation(dev)))['risk']

    def test_boundaries(self):
        cases = [
            (-2.99, 'NORMAL'), (-3.00, 'NORMAL'), (-3.01, 'CAUTION'),
            (-6.99, 'CAUTION'), (-7.00, 'RISK'), (-7.01, 'RISK'),
            (-9.99, 'RISK'), (-10.00, 'CRITICAL'), (-10.01, 'CRITICAL'),
            (0.0, 'NORMAL'), (5.0, 'NORMAL'),
        ]
        for dev, expected in cases:
            with self.subTest(deviation=dev):
                self.assertEqual(self.risk(dev), expected)

class ErrorTest(unittest.TestCase):
    """TC03: 데이터 부족 오류."""
    def test_empty(self):
        with self.assertRaises(ValueError):
            calculate([])

    def test_fewer_than_10(self):
        with self.assertRaisesRegex(ValueError, '10개'):
            calculate(series(1400.0, n=9))

    def test_rolling_3m_under_40(self):
        with self.assertRaisesRegex(ValueError, '40개'):
            calculate(series(1400.0, n=20))

    def test_old_data_outside_window_not_counted(self):
        # 10개 이상이지만 3개월 창 안에는 39개뿐 -> 부족
        old = [Rate(date(2025, 1, 1) + timedelta(days=i), 1400.0) for i in range(30)]
        recent = [Rate(date(2026, 10, 1) + timedelta(days=i), 1400.0) for i in range(39)]
        with self.assertRaisesRegex(ValueError, '40개'):
            calculate(old + recent)

    def test_unsorted_input_is_sorted(self):
        rates = series(1330.0)
        self.assertEqual(calculate(rates[::-1]), calculate(rates))

class ReproTest(unittest.TestCase):
    """TC04: 동일 입력 -> 동일 결과."""
    def test_calculate_is_deterministic(self):
        self.assertEqual(calculate(series(1330.0)), calculate(series(1330.0)))

    def test_cli_twice_same_json(self):
        import subprocess, sys, pathlib
        root = pathlib.Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as d:
            outs = []
            for i in range(2):
                out = os.path.join(d, f'r{i}.json')
                subprocess.run([sys.executable, 'main.py', '--output', out],
                               cwd=root, check=True, capture_output=True)
                outs.append(pathlib.Path(out).read_text(encoding='utf-8'))
            self.assertEqual(outs[0], outs[1])

    def test_sample_csv_matches_committed_result(self):
        import json, pathlib
        root = pathlib.Path(__file__).resolve().parent.parent
        expected = json.loads((root / 'docs' / 'sample_result.json').read_text(encoding='utf-8'))
        self.assertEqual(calculate(load_rates(root / 'data' / 'sample_rates.csv')), expected)

if __name__ == '__main__': unittest.main()
