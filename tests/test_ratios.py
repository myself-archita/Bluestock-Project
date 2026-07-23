import unittest

import pandas as pd
from src.analytics.ratios import compute_profitability_ratios, compute_leverage_ratios


class TestRatios(unittest.TestCase):
    def test_profitability_ratios(self):
        df = pd.DataFrame([{"sales": 100, "operating_profit": 20, "pat": 10, "equity": 50, "debt": 25}])
        out = compute_profitability_ratios(df)
        self.assertEqual(round(out.loc[0, "npm"], 2), 0.10)
        self.assertEqual(round(out.loc[0, "opm"], 2), 0.20)
        self.assertEqual(round(out.loc[0, "roe"], 2), 0.20)

    def test_leverage_ratios(self):
        df = pd.DataFrame([{"sales": 100, "operating_profit": 20, "equity": 50, "debt": 25, "assets": 200, "is_bank": 0}])
        out = compute_leverage_ratios(df)
        self.assertEqual(round(out.loc[0, "debt_equity"], 2), 0.50)
        self.assertEqual(round(out.loc[0, "asset_turnover"], 2), 0.50)
