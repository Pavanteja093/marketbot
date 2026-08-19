from __future__ import annotations

import unittest

import pandas as pd

from research.v2_track_c_episode_qualification import (
    build_qualification_report,
    classify_candidate,
)


class EpisodeQualificationTests(unittest.TestCase):
    def test_no_evidence(self):
        self.assertEqual(
            classify_candidate(
                total_observations=0,
                total_scenario_episodes=10,
                occupied_episodes=0,
                coverage_pct=0,
                qualifying_episodes_ge_20=0,
                max_concentration_pct=0,
            ),
            "NO_HISTORICAL_EVIDENCE",
        )

    def test_recurrent_but_sparse(self):
        self.assertEqual(
            classify_candidate(
                total_observations=49,
                total_scenario_episodes=19,
                occupied_episodes=13,
                coverage_pct=68.4,
                qualifying_episodes_ge_20=0,
                max_concentration_pct=26.5,
            ),
            "RECURRENT_BUT_SPARSE",
        )

    def test_strict_episode_stable_candidate_requires_two_episodes(self):
        kwargs = dict(
            total_observations=50,
            total_scenario_episodes=10,
            occupied_episodes=8,
            coverage_pct=80,
            max_concentration_pct=30,
        )
        self.assertNotEqual(
            classify_candidate(qualifying_episodes_ge_20=1, **kwargs),
            "EPISODE_STABLE_CANDIDATE",
        )
        self.assertEqual(
            classify_candidate(qualifying_episodes_ge_20=2, **kwargs),
            "EPISODE_STABLE_CANDIDATE",
        )

    def test_concentration_warning(self):
        self.assertEqual(
            classify_candidate(
                total_observations=100,
                total_scenario_episodes=10,
                occupied_episodes=8,
                coverage_pct=80,
                qualifying_episodes_ge_20=0,
                max_concentration_pct=55,
            ),
            "CONCENTRATED_EVIDENCE",
        )

    def test_report_has_one_row_per_candidate(self):
        rows = []
        for day in pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-05"]):
            rows.append({
                "trade_date": day,
                "index_name": "S1",
                "scenario": "TREND_UP",
                "return_5d": 1.0,
                "trend_score": 80.0,
                "momentum_score": 80.0,
                "relative_strength": 20.0,
                "change_pct": 20.0,
                "volatility_score": 20.0,
                "intelligence_score": 20.0,
                "liquidity_score": 20.0,
            })
        dataset = pd.DataFrame(rows)
        episodes = pd.DataFrame([
            {
                "scenario": "TREND_UP",
                "episode_id": 1,
                "start_date": pd.Timestamp("2026-01-01"),
                "end_date": pd.Timestamp("2026-01-05"),
                "trading_days": 3,
                "observations": 3,
            }
        ])
        report = build_qualification_report(dataset, episodes)
        self.assertEqual(len(report), 6)
        self.assertIn("research_status", report.columns)
        self.assertIn("coverage_gate", report.columns)
        self.assertIn("strict_episode_gate", report.columns)


if __name__ == "__main__":
    unittest.main()

