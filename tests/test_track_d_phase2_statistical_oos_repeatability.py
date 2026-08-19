from __future__ import annotations

import unittest
import numpy as np
import pandas as pd

from research import track_d_phase2_statistical_oos_repeatability as m


def make_data(days=180, stocks=25):
    dates = pd.bdate_range("2025-01-01", periods=days)
    rows = []
    rng = np.random.default_rng(42)
    for di, day in enumerate(dates):
        for s in range(stocks):
            factor = float(s + rng.normal(0, 0.1))
            rows.append(
                {
                    "trade_date": day,
                    "index_name": f"S{s:02d}",
                    "scenario": "SIDEWAYS",
                    "intelligence_score": factor,
                    "volatility_score": float(s + rng.normal(0, 0.1)),
                    "trend_score": float(s + rng.normal(0, 0.1)),
                    "return_1d": factor * 0.01 + rng.normal(0, 0.2),
                    "return_5d": factor * 0.02 + rng.normal(0, 0.2),
                    "return_10d": factor * 0.03 + rng.normal(0, 0.2),
                    "return_20d": factor * 0.04 + rng.normal(0, 0.2),
                }
            )
    return pd.DataFrame(rows)


class TrackDPhase2Tests(unittest.TestCase):
    def test_fold_builder_is_chronological(self):
        dates = pd.bdate_range("2025-01-01", periods=150)
        folds = m.make_oos_folds(dates)
        self.assertGreaterEqual(len(folds), 3)
        for _, train_end, test_start, test_end in folds:
            self.assertLess(train_end, test_start)
            self.assertLessEqual(test_start, test_end)

    def test_spearman_detects_monotonic_relationship(self):
        x = pd.Series([1, 2, 3, 4, 5])
        y = pd.Series([10, 20, 30, 40, 50])
        self.assertAlmostEqual(m._spearman(x, y), 1.0, places=9)

    def test_quintile_spread_requires_minimum_sample(self):
        frame = pd.DataFrame({"x": range(10), "r": range(10)})
        self.assertTrue(np.isnan(m._quintile_spread(frame, "x", "r")))

    def test_bh_is_monotonic_and_conservative(self):
        adjusted = m.benjamini_hochberg([0.001, 0.01, 0.2, 0.5])
        self.assertEqual(len(adjusted), 4)
        self.assertTrue(all(0 <= x <= 1 for x in adjusted))
        self.assertGreaterEqual(adjusted[0], 0.001)

    def test_validation_is_deterministic(self):
        data = make_data()
        a = m.validate(data, (("SIDEWAYS", "intelligence_score"),))
        b = m.validate(data, (("SIDEWAYS", "intelligence_score"),))
        pd.testing.assert_frame_equal(a, b)

    def test_validation_does_not_mutate_input(self):
        data = make_data()
        before = data.copy(deep=True)
        m.validate(data, (("SIDEWAYS", "intelligence_score"),))
        pd.testing.assert_frame_equal(data, before)

    def test_all_requested_horizons_are_present(self):
        data = make_data()
        result = m.validate(data, (("SIDEWAYS", "intelligence_score"),))
        self.assertEqual(set(result["horizon_days"]), {1, 5, 10, 20})

    def test_conservative_classification_with_too_few_windows(self):
        cls = m._classify(2, 2, 0.5, 100, 0.1, 0.9, 0.001)
        self.assertEqual(cls, "INSUFFICIENT_OOS_WINDOWS")


if __name__ == "__main__":
    unittest.main()
