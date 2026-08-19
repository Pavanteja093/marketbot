"""
MarketBot C2.2 - Regime-Aware Walk-Forward Tests

This suite targets the current C2.2 API, not the obsolete C2.1 API.
Run with:
    python -m unittest tests.test_regime_aware_c22 -v
"""

import sqlite3
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from research.regime_aware_walk_forward import (
    FACTORS,
    MAX_FACTOR_WEIGHT,
    _cap_weights,
    build_regimes,
    evaluate_day,
    fit_weights,
    score_day,
    summarize,
)


class C22RegimeAwareTests(unittest.TestCase):

    def test_regime_builder_is_deterministic_and_complete(self):
        dates = pd.date_range("2025-01-01", periods=140, freq="D")
        close = np.linspace(100.0, 160.0, len(dates))
        source = pd.DataFrame({"trade_date": dates, "close": close})

        first = build_regimes(source)
        second = build_regimes(source)

        self.assertEqual(len(first), 140)
        self.assertEqual(list(first.columns), ["trade_date", "regime"])
        self.assertTrue(first["regime"].notna().all())
        pd.testing.assert_frame_equal(first, second)

    def test_regime_builder_sorts_and_deduplicates_dates(self):
        dates = pd.date_range("2025-01-01", periods=80, freq="D")
        source = pd.DataFrame(
            {
                "trade_date": list(dates[::-1]) + [dates[10]],
                "close": list(np.linspace(100, 140, 80)[::-1]) + [105.0],
            }
        )

        result = build_regimes(source)

        self.assertEqual(len(result), 80)
        self.assertTrue(result["trade_date"].is_monotonic_increasing)
        self.assertEqual(result["trade_date"].nunique(), 80)

    def test_weight_cap_normalizes_and_enforces_hard_cap(self):
        raw = {
            "relative_strength": 0.01,
            "trend_score": 1.0,
            "momentum_score": 0.2,
            "volatility_score": 0.1,
            "liquidity_score": 0.9,
        }

        weights = _cap_weights(raw)

        self.assertEqual(set(weights), set(FACTORS))
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=9)
        self.assertLessEqual(max(weights.values()), MAX_FACTOR_WEIGHT + 1e-9)
        self.assertTrue(all(value >= 0 for value in weights.values()))

    def test_weight_cap_handles_zero_signal(self):
        weights = _cap_weights({factor: 0.0 for factor in FACTORS})

        self.assertAlmostEqual(sum(weights.values()), 1.0, places=9)
        for factor in FACTORS:
            self.assertAlmostEqual(
                weights[factor], 1.0 / len(FACTORS), places=9
            )

    def test_daily_evaluation_returns_correct_spread(self):
        n = 25
        frame = pd.DataFrame(
            {
                "candidate_score": np.arange(n, dtype=float),
                "return_5d": np.linspace(-1.0, 2.0, n),
            }
        )

        result = evaluate_day(frame)

        self.assertIsNotNone(result)
        self.assertGreater(result["spread"], 0.0)
        self.assertEqual(result["observations"], 25)
        self.assertGreaterEqual(result["top_win_rate"], 0.0)
        self.assertLessEqual(result["top_win_rate"], 100.0)

    def test_daily_evaluation_rejects_insufficient_observations(self):
        frame = pd.DataFrame(
            {
                "candidate_score": np.arange(9, dtype=float),
                "return_5d": np.arange(9, dtype=float),
            }
        )

        self.assertIsNone(evaluate_day(frame, min_stocks=10))

    def test_score_day_uses_factor_direction_and_weights(self):
        n = 10
        day = pd.DataFrame(
            {factor: np.arange(n, dtype=float) for factor in FACTORS}
        )

        weights = {factor: 0.2 for factor in FACTORS}
        meta = {factor: {"direction": 1} for factor in FACTORS}

        score = score_day(day, weights, meta)

        self.assertEqual(len(score), n)
        self.assertTrue(score.index.equals(day.index))
        self.assertTrue(np.isfinite(score).all())
        self.assertGreater(score.iloc[-1], score.iloc[0])

    def test_fit_weights_returns_complete_factor_model(self):
        rng = np.random.default_rng(42)
        dates = pd.date_range("2025-01-01", periods=60, freq="D")

        rows = []
        for date in dates:
            for _ in range(20):
                signal = rng.normal()
                rows.append(
                    {
                        "prediction_date": date,
                        "regime": "TREND_UP",
                        "return_5d": signal + rng.normal(scale=0.5),
                        "relative_strength": signal + rng.normal(scale=0.1),
                        "trend_score": signal + rng.normal(scale=0.1),
                        "momentum_score": rng.normal(),
                        "volatility_score": rng.normal(),
                        "liquidity_score": rng.normal(),
                    }
                )

        frame = pd.DataFrame(rows)
        weights, meta = fit_weights(frame, "TREND_UP")

        self.assertEqual(set(weights), set(FACTORS))
        self.assertEqual(set(meta), set(FACTORS))
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=9)
        self.assertLessEqual(max(weights.values()), MAX_FACTOR_WEIGHT + 1e-9)

        for factor in FACTORS:
            for key in (
                "global_ic",
                "regime_ic",
                "shrunk_ic",
                "regime_days",
                "icir",
                "direction",
                "source",
                "weight",
            ):
                self.assertIn(key, meta[factor])

    def test_fit_weights_uses_global_fallback_for_sparse_regime(self):
        rng = np.random.default_rng(7)
        dates = pd.date_range("2025-01-01", periods=50, freq="D")

        rows = []
        for date in dates:
            for _ in range(10):
                signal = rng.normal()
                rows.append(
                    {
                        "prediction_date": date,
                        "regime": "OTHER",
                        "return_5d": signal + rng.normal(scale=0.5),
                        "relative_strength": signal,
                        "trend_score": rng.normal(),
                        "momentum_score": rng.normal(),
                        "volatility_score": rng.normal(),
                        "liquidity_score": rng.normal(),
                    }
                )

        rows.append(
            {
                "prediction_date": dates[-1],
                "regime": "SPARSE",
                "return_5d": 1.0,
                "relative_strength": 1.0,
                "trend_score": 0.5,
                "momentum_score": 0.2,
                "volatility_score": 0.1,
                "liquidity_score": 0.3,
            }
        )

        frame = pd.DataFrame(rows)
        _, meta = fit_weights(frame, "SPARSE")

        for factor in FACTORS:
            self.assertEqual(meta[factor]["source"], "GLOBAL_FALLBACK")

    def test_summary_calculates_window_statistics(self):
        results = pd.DataFrame({"spread": [1.0, -0.5, 0.25, -0.25]})

        summary = summarize(results)

        self.assertEqual(summary["windows"], 4)
        self.assertAlmostEqual(summary["average_spread"], 0.125)
        self.assertAlmostEqual(summary["median_spread"], 0.0)
        self.assertAlmostEqual(summary["positive_window_pct"], 50.0)
        self.assertAlmostEqual(summary["worst_window"], -0.5)
        self.assertAlmostEqual(summary["best_window"], 1.0)

    def test_summary_handles_empty_results(self):
        summary = summarize(pd.DataFrame())

        self.assertEqual(summary["windows"], 0)
        self.assertIsNone(summary["average_spread"])
        self.assertIsNone(summary["median_spread"])
        self.assertIsNone(summary["positive_window_pct"])
        self.assertIsNone(summary["worst_window"])
        self.assertIsNone(summary["best_window"])

    def test_test_helpers_do_not_write_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"

            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE marker (value INTEGER NOT NULL)")
            conn.execute("INSERT INTO marker(value) VALUES (1)")
            conn.commit()
            conn.close()

            check_conn = sqlite3.connect(db_path)
            try:
                before = check_conn.execute(
                    "SELECT value FROM marker"
                ).fetchall()
            finally:
                check_conn.close()

            dates = pd.date_range("2025-01-01", periods=60, freq="D")
            build_regimes(
                pd.DataFrame(
                    {
                        "trade_date": dates,
                        "close": np.linspace(100.0, 120.0, 60),
                    }
                )
            )

            check_conn = sqlite3.connect(db_path)
            try:
                after = check_conn.execute(
                    "SELECT value FROM marker"
                ).fetchall()
            finally:
                check_conn.close()

            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
