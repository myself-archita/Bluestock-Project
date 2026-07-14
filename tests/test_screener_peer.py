import unittest

import pandas as pd

from src.analytics.peer import compute_peer_percentiles
from src.screener.engine import apply_filters, compute_composite_quality_score


class TestScreenerPeer(unittest.TestCase):
    def test_quality_compounder_filter(self):
        df = pd.DataFrame(
            [
                {"ticker": "A", "sector": "IT", "pat": 50, "sales": 100, "operating_profit": 30, "equity": 200, "debt": 100, "cfo": 60, "capex": 10, "year": 2024, "revenue_cagr_5y": 0.2},
                {"ticker": "B", "sector": "IT", "pat": 5, "sales": 100, "operating_profit": 10, "equity": 20, "debt": 80, "cfo": 1, "capex": 5, "year": 2024, "revenue_cagr_5y": 0.05},
            ]
        )
        out = apply_filters(df, {"filters": {"roe": {"min": 0.15}, "debt_equity": {"max": 1.0}, "fcf": {"min": 0.0}, "revenue_cagr_5y": {"min": 0.1}}}, preset_name="Quality Compounder")
        self.assertEqual(list(out["ticker"]), ["A"])

    def test_composite_score_returns_bounded_values(self):
        df = pd.DataFrame([{"roe": 0.2, "roce": 0.15, "npm": 0.1, "fcf": 10, "cfo_pat_ratio": 1.2, "fcf_conversion": 0.5, "revenue_cagr_5y": 0.2, "pat_cagr_5y": 0.18, "eps_cagr_5y": 0.12, "debt_equity": 0.5, "interest_coverage": 3, "sector": "IT"}])
        score = compute_composite_quality_score(df)
        self.assertTrue((score >= 0).all() and (score <= 100).all())

    def test_peer_percentiles_inverse_debt_equity(self):
        df = pd.DataFrame(
            [
                {"ticker": "A", "peer_group": "IT", "debt_equity": 0.5, "roe": 0.2},
                {"ticker": "B", "peer_group": "IT", "debt_equity": 1.0, "roe": 0.1},
            ]
        )
        out = compute_peer_percentiles(df, metric_cols=["debt_equity", "roe"])
        debt = out[out["metric"] == "debt_equity"].sort_values("ticker")
        self.assertGreater(debt.iloc[0]["percentile_rank"], debt.iloc[1]["percentile_rank"])


if __name__ == "__main__":
    unittest.main()

