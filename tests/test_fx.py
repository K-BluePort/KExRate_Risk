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

if __name__ == '__main__': unittest.main()
