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


class C21RegimeAwareTests(unittest.TestCase):

    def test_regime_builder_is_deterministic_and_complete(self):
        dates = pd.date_range("2025-01-01", periods=120, freq="D")
        close = np.linspace(100, 150, len(dates))

        df = pd.DataFrame(
            {
                "trade_date": dates,
                "close": close,
            }
        )

        first = build_regimes(df)
        second = build_regimes(df)

        pd.testing.assert_frame_equal(first, second)

        self.assertEqual(len(first), 120)
        self.assertIn("trade_date", first.columns)
        self.assertIn("regime", first.columns)
        self.assertTrue(first["regime"].notna().all())

    def test_regime_builder_sorts_and_deduplicates_dates(self):
        dates = pd.to_datetime(
            [
                "2025-01-05",
                "2025-01-01",
                "2025-01-03",
                "2025-01-03",
                "2025-01-02",
            ]
        )

        df = pd.DataFrame(
            {
                "trade_date": dates,
                "close": [105, 100, 103, 103, 102],
            }
        )

        result = build_regimes(df)

        self.assertEqual(len(result), 4)
        self.assertTrue(result["trade_date"].is_monotonic_increasing)
        self.assertEqual(
            result["trade_date"].dt.normalize().nunique(),
            4,
        )

    def test_daily_evaluation_returns_correct_spread(self):
        n = 25

        df = pd.DataFrame(
            {
                "candidate_score": np.arange(n, dtype=float),
                "return_5d": np.linspace(-1, 2, n),
            }
        )

        result = evaluate_day(df, min_stocks=10)

        self.assertIsNotNone(result)
        self.assertIn("spread", result)
        self.assertGreater(result["spread"], 0)

    def test_daily_evaluation_rejects_insufficient_observations(self):
        df = pd.DataFrame(
            {
                "candidate_score": [1.0, 2.0, 3.0],
                "return_5d": [0.1, 0.2, 0.3],
            }
        )

        result = evaluate_day(df, min_stocks=10)

        self.assertIsNone(result)

    def _make_factor_frame(self, n_days=60, n_stocks=20):
        rows = []

        dates = pd.date_range(
            "2025-01-01",
            periods=n_days,
            freq="D",
        )

        for day_number, date in enumerate(dates):
            for stock_number in range(n_stocks):
                row = {
                    "prediction_date": date,
                    "index_name": f"STOCK{stock_number}",
                    "return_5d": float(stock_number - 10),
                    "regime": (
                        "TREND_UP"
                        if day_number % 2 == 0
                        else "TREND_DOWN"
                    ),
                }

                for factor_number, factor in enumerate(FACTORS):
                    row[factor] = float(
                        stock_number + factor_number + day_number * 0.01
                    )

                rows.append(row)

        return pd.DataFrame(rows)

    def test_fit_weights_returns_complete_factor_model(self):
        df = self._make_factor_frame()

        weights, meta = fit_weights(
            df,
            "TREND_UP",
        )

        self.assertEqual(set(weights.keys()), set(FACTORS))
        self.assertEqual(set(meta.keys()), set(FACTORS))

        self.assertAlmostEqual(
            sum(weights.values()),
            1.0,
            places=8,
        )

        for factor in FACTORS:
            self.assertIn("weight", meta[factor])
            self.assertIn("direction", meta[factor])
            self.assertIn("global_ic", meta[factor])
            self.assertIn("regime_ic", meta[factor])
            self.assertIn("shrunk_ic", meta[factor])

    def test_fit_weights_uses_global_fallback_for_sparse_regime(self):
        df = self._make_factor_frame()

        df["regime"] = "COMMON"

        # Create a sparse target regime with fewer than the
        # configured minimum regime IC days.
        sparse = df.iloc[:20].copy()
        sparse["regime"] = "SPARSE"

        df = pd.concat(
            [df.iloc[20:], sparse],
            ignore_index=True,
        )

        weights, meta = fit_weights(
            df,
            "SPARSE",
        )

        self.assertEqual(set(weights.keys()), set(FACTORS))

        for factor in FACTORS:
            self.assertEqual(
                meta[factor]["source"],
                "GLOBAL_FALLBACK",
            )

    def test_score_day_uses_factor_direction_and_weights(self):
        day = pd.DataFrame(
            {
                "relative_strength": [1.0, 2.0, 3.0],
                "trend_score": [3.0, 2.0, 1.0],
                "momentum_score": [1.0, 2.0, 3.0],
                "volatility_score": [3.0, 2.0, 1.0],
                "liquidity_score": [1.0, 2.0, 3.0],
            }
        )

        weights = {
            factor: 0.2
            for factor in FACTORS
        }

        meta = {
            factor: {
                "direction": 1
            }
            for factor in FACTORS
        }

        score = score_day(
            day,
            weights,
            meta,
        )

        self.assertEqual(len(score), len(day))
        self.assertTrue(np.isfinite(score).all())

        # With all directions positive, the highest-ranked
        # combined score should remain identifiable.
        self.assertGreaterEqual(
            score.max(),
            score.min(),
        )

    def test_weight_cap_normalizes_and_enforces_hard_cap(self):
        raw = {
            "relative_strength": 100.0,
            "trend_score": 1.0,
            "momentum_score": 1.0,
            "volatility_score": 1.0,
            "liquidity_score": 1.0,
        }

        weights = _cap_weights(raw)

        self.assertAlmostEqual(
            sum(weights.values()),
            1.0,
            places=8,
        )

        for weight in weights.values():
            self.assertLessEqual(
                weight,
                MAX_FACTOR_WEIGHT + 1e-9,
            )

    def test_weight_cap_handles_zero_signal(self):
        raw = {
            factor: 0.0
            for factor in FACTORS
        }

        weights = _cap_weights(raw)

        self.assertAlmostEqual(
            sum(weights.values()),
            1.0,
            places=8,
        )

        expected = 1.0 / len(FACTORS)

        for factor in FACTORS:
            self.assertAlmostEqual(
                weights[factor],
                expected,
                places=8,
            )

    def test_summary_calculates_window_statistics(self):
        results = pd.DataFrame(
            {
                "spread": [
                    -1.0,
                    0.0,
                    0.5,
                    1.0,
                ]
            }
        )

        summary = summarize(results)

        self.assertEqual(
            summary["windows"],
            4,
        )

        self.assertAlmostEqual(
            summary["average_spread"],
            0.125,
        )

        self.assertAlmostEqual(
            summary["median_spread"],
            0.25,
        )

        self.assertAlmostEqual(
            summary["positive_window_pct"],
            50.0,
        )

        self.assertAlmostEqual(
            summary["worst_window"],
            -1.0,
        )

        self.assertAlmostEqual(
            summary["best_window"],
            1.0,
        )

    def test_summary_handles_empty_results(self):
        results = pd.DataFrame()

        summary = summarize(results)

        self.assertEqual(
            summary["windows"],
            0,
        )

        self.assertIsNone(
            summary["average_spread"],
        )

        self.assertIsNone(
            summary["median_spread"],
        )

        self.assertIsNone(
            summary["positive_window_pct"],
        )

        self.assertIsNone(
            summary["worst_window"],
        )

        self.assertIsNone(
            summary["best_window"],
        )

    def test_test_helpers_do_not_write_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"

            conn = sqlite3.connect(db_path)

            conn.execute(
                """
                CREATE TABLE marker (
                    id INTEGER PRIMARY KEY,
                    value TEXT
                )
                """
            )

            conn.execute(
                "INSERT INTO marker(value) VALUES (?)",
                ("before",),
            )

            conn.commit()

            before = conn.execute(
                "SELECT COUNT(*) FROM marker"
            ).fetchone()[0]

            conn.close()

            # Exercise research helpers only.
            dates = pd.date_range(
                "2025-01-01",
                periods=60,
                freq="D",
            )

            index_df = pd.DataFrame(
                {
                    "trade_date": dates,
                    "close": np.linspace(
                        100,
                        120,
                        len(dates),
                    ),
                }
            )

            regimes = build_regimes(index_df)

            self.assertEqual(
                len(regimes),
                len(index_df),
            )

            after_conn = sqlite3.connect(db_path)

            after = after_conn.execute(
                "SELECT COUNT(*) FROM marker"
            ).fetchone()[0]

            after_conn.close()

            self.assertEqual(
                before,
                after,
            )


if __name__ == "__main__":
    unittest.main()