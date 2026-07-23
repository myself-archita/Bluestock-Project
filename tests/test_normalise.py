import unittest

from src.etl.loader import normalize_year, normalize_ticker


class TestNormalise(unittest.TestCase):
    def test_normalize_year_cases(self):
        cases = {
            2024: 2024,
            "2024": 2024,
            "FY24": 2024,
            "24": 2024,
            "99": 1999,
            None: None,
        }
        for raw, expected in cases.items():
            self.assertEqual(normalize_year(raw), expected)

    def test_normalize_ticker_cases(self):
        cases = {
            "reliance.ns": "RELIANCE",
            "tcs -eq": "TCS",
            "  hdfcbank  ": "HDFCBANK",
            None: None,
        }
        for raw, expected in cases.items():
            self.assertEqual(normalize_ticker(raw), expected)
