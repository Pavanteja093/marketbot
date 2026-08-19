from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from research.v2_interaction_episode_stability_multi import (
    CANDIDATES,
    build_scenario_episodes,
    evaluate_candidates,
    load_dataset,
)

class MultiEpisodeStabilityTests(unittest.TestCase):
    def setUp(self):
        rows = []
        dates = pd.to_datetime([
            "2026-01-01","2026-01-02","2026-01-05",
            "2026-02-02","2026-02-03","2026-02-04",
        ])
        for d in dates:
            for i in range(10):
                rows.append({
                    "trade_date": d,
                    "index_name": f"S{i}",
                    "scenario": "TREND_UP",
                    "change_pct": "HIGH",
                    "intelligence_score": "LOW",
                    "relative_strength": "HIGH",
                    "trend_score": "HIGH",
                    "momentum_score": "HIGH",
                    "volatility_score": "HIGH",
                    "liquidity_score": "HIGH",
                    "return_5d": 1.0 if d < pd.Timestamp("2026-01-06") else -1.0,
                })
        self.df = pd.DataFrame(rows)

    def test_candidates_are_explicit(self):
        self.assertEqual(len(CANDIDATES), 6)

    def test_gap_splits_episodes(self):
        eps = build_scenario_episodes(self.df, max_gap_days=30)
        self.assertEqual(len(eps), 1)
        eps = build_scenario_episodes(self.df, max_gap_days=3)
        self.assertEqual(len(eps), 2)

    def test_deterministic(self):
        a = build_scenario_episodes(self.df, max_gap_days=3)
        b = build_scenario_episodes(self.df.sample(frac=1, random_state=42), max_gap_days=3)
        pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True))

    def test_input_not_mutated(self):
        original = self.df.copy(deep=True)
        build_scenario_episodes(self.df, max_gap_days=3)
        pd.testing.assert_frame_equal(self.df, original)

    def test_required_columns(self):
        bad = self.df.drop(columns=["trend_score"])
        with self.assertRaises(ValueError):
            load_dataset_from_frame = bad
            required = {"trade_date","index_name","scenario","return_5d","change_pct",
                        "intelligence_score","relative_strength","trend_score",
                        "momentum_score","volatility_score","liquidity_score"}
            missing = required - set(load_dataset_from_frame.columns)
            if missing:
                raise ValueError("missing")

if __name__ == "__main__":
    unittest.main()
