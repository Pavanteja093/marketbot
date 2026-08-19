import unittest
import sqlite3
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from research.factor_agreement_candidate import (
    add_agreement,
    add_baseline_score,
    evaluate_day,
    summarize,
)


class FactorAgreementCandidateTests(unittest.TestCase):

    def make_df(self, n=25):
        dates = pd.to_datetime(["2026-01-01"] * n)
        return pd.DataFrame({
            "trade_date": dates,
            "entity": [f"S{i}" for i in range(n)],
            "relative_strength": np.linspace(-1, 1, n),
            "trend_score": np.linspace(-1, 1, n),
            "momentum_score": np.linspace(-1, 1, n),
            "volatility_score": np.linspace(-1, 1, n),
            "liquidity_score": np.linspace(-1, 1, n),
            "return_5d": np.linspace(-1, 1, n),
        })

    def test_agreement_columns(self):
        out = add_agreement(self.make_df())
        self.assertIn("agreement_score", out.columns)
        self.assertIn("daily_agreement", out.columns)
        self.assertTrue(np.isfinite(out["agreement_score"]).all())

    def test_baseline_score_finite(self):
        out = add_baseline_score(self.make_df())
        self.assertIn("baseline_score", out.columns)
        self.assertTrue(np.isfinite(out["baseline_score"]).all())

    def test_evaluate_day(self):
        out = add_agreement(self.make_df())
        out = add_baseline_score(out)
        result = evaluate_day(out, min_stocks=10)
        self.assertIsNotNone(result)
        self.assertTrue(np.isfinite(result["spread"]))

    def test_evaluate_rejects_small_sample(self):
        out = add_agreement(self.make_df(5))
        out = add_baseline_score(out)
        self.assertIsNone(evaluate_day(out, min_stocks=10))

    def test_summary(self):
        results = pd.DataFrame({
            "spread": [1.0, -0.5, 0.2, -0.1],
            "agreement": [0.2, 0.9, 0.3, 0.8],
            "high_agreement": [False, True, False, True],
        })
        s = summarize(results)
        self.assertEqual(set(s["condition"]), {
            "ALL_DAYS", "LOW_AGREEMENT", "HIGH_AGREEMENT"
        })

    def test_helpers_do_not_mutate(self):
        df = self.make_df()
        before = df.copy(deep=True)
        add_agreement(df)
        add_baseline_score(df)
        pd.testing.assert_frame_equal(df, before)


if __name__ == "__main__":
    unittest.main()
