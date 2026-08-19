from __future__ import annotations

import unittest
import pandas as pd

from v2_track_c_cross_episode_temporal_robustness import (
    CANDIDATES,
    MIN_EPISODE_OBSERVATIONS,
    analyze,
)


KEYS = ["scenario", "factor_a", "state_a", "factor_b", "state_b"]


def episode_row(
    episode_id,
    factor_a="trend_score",
    state_a="HIGH",
    factor_b="momentum_score",
    state_b="HIGH",
    observations=20,
    dominant_outcome="UP",
    mean_return_5d=1.0,
):
    return {
        "episode_id": episode_id,
        "test_start": "2026-01-01",
        "test_end": "2026-01-30",
        "scenario": "TREND_UP",
        "factor_a": factor_a,
        "factor_b": factor_b,
        "state_a": state_a,
        "state_b": state_b,
        "observations": observations,
        "dominant_outcome": dominant_outcome,
        "dominant_probability_pct": 60.0,
        "baseline_probability_pct": 45.0,
        "probability_uplift_pct": 15.0,
        "mean_return_5d": mean_return_5d,
        "median_return_5d": mean_return_5d,
        "down_pct": 20.0,
        "flat_pct": 10.0,
        "up_pct": 70.0,
    }


def oos_frame():
    return pd.DataFrame([{
        "scenario": "TREND_UP",
        "factor_a": "trend_score",
        "state_a": "HIGH",
        "factor_b": "momentum_score",
        "state_b": "HIGH",
        "observations": 100,
        "up_pct": 60.0,
        "mean_return_5d": 1.0,
        "oos_folds": 8,
        "oos_stability": "REPEATED",
    }])


class TestCrossEpisode(unittest.TestCase):

    def test_candidate_count(self):
        self.assertEqual(len(CANDIDATES), 6)

    def test_candidate_matching_and_oos(self):
        df = pd.DataFrame([
            episode_row(1),
            episode_row(2),
        ])
        out = analyze(df, oos_frame())
        target = out[
            (out.factor_a == "trend_score")
            & (out.factor_b == "momentum_score")
        ].iloc[0]
        self.assertEqual(int(target.oos_observations), 100)
        self.assertEqual(int(target.qualifying_episode_count_ge_20), 2)

    def test_missing_oos(self):
        df = pd.DataFrame([episode_row(1)])
        empty_oos = oos_frame().iloc[0:0]
        out = analyze(df, empty_oos)
        target = out[
            (out.factor_a == "trend_score")
            & (out.factor_b == "momentum_score")
        ].iloc[0]
        self.assertEqual(target.oos_stability, "NO_OOS_EVIDENCE")

    def test_zero_observation_candidate(self):
        df = pd.DataFrame(columns=[
            "episode_id", "test_start", "test_end",
            *KEYS,
            "observations", "dominant_outcome",
            "dominant_probability_pct", "baseline_probability_pct",
            "probability_uplift_pct", "mean_return_5d",
            "median_return_5d", "down_pct", "flat_pct", "up_pct",
        ])
        out = analyze(df, oos_frame())
        self.assertTrue(
            (out.temporal_robustness_classification == "NO_HISTORICAL_EVIDENCE").all()
        )

    def test_strict_threshold_preserved(self):
        df = pd.DataFrame([
            episode_row(1, observations=MIN_EPISODE_OBSERVATIONS - 1),
            episode_row(2, observations=MIN_EPISODE_OBSERVATIONS - 1),
        ])
        out = analyze(df, oos_frame())
        target = out.iloc[
            ((out.factor_a == "trend_score") & (out.factor_b == "momentum_score")).to_numpy().nonzero()[0][0]
        ]
        self.assertEqual(int(target.qualifying_episode_count_ge_20), 0)
        self.assertEqual(target.temporal_robustness_classification, "RECURRENT_BUT_SPARSE")

    def test_multiple_qualifying_consistent_episodes(self):
        df = pd.DataFrame([
            episode_row(1, dominant_outcome="UP", mean_return_5d=1.0),
            episode_row(2, dominant_outcome="UP", mean_return_5d=2.0),
        ])
        out = analyze(df, oos_frame())
        target = out[
            (out.factor_a == "trend_score")
            & (out.factor_b == "momentum_score")
        ].iloc[0]
        self.assertEqual(target.temporal_robustness_classification, "MULTI_EPISODE_STABLE")

    def test_multiple_qualifying_inconsistent(self):
        df = pd.DataFrame([
            episode_row(1, dominant_outcome="UP", mean_return_5d=1.0),
            episode_row(2, dominant_outcome="DOWN", mean_return_5d=-1.0),
        ])
        out = analyze(df, oos_frame())
        target = out[
            (out.factor_a == "trend_score")
            & (out.factor_b == "momentum_score")
        ].iloc[0]
        self.assertEqual(
            target.temporal_robustness_classification,
            "MULTI_EPISODE_INCONSISTENT",
        )

    def test_concentration_is_conservative(self):
        df = pd.DataFrame([
            episode_row(1, observations=100, dominant_outcome="UP", mean_return_5d=1.0),
            episode_row(2, observations=20, dominant_outcome="UP", mean_return_5d=1.0),
            episode_row(3, observations=20, dominant_outcome="UP", mean_return_5d=1.0),
        ])
        out = analyze(df, oos_frame())
        target = out[
            (out.factor_a == "trend_score")
            & (out.factor_b == "momentum_score")
        ].iloc[0]
        self.assertEqual(target.temporal_robustness_classification, "MULTI_EPISODE_INCONSISTENT")
        self.assertGreater(float(target.max_episode_concentration_pct), 50.0)

    def test_deterministic(self):
        df = pd.DataFrame([
            episode_row(1),
            episode_row(2),
        ])
        a = analyze(df, oos_frame())
        b = analyze(df, oos_frame())
        pd.testing.assert_frame_equal(a, b)

    def test_inputs_not_mutated(self):
        df = pd.DataFrame([episode_row(1)])
        before = df.copy(deep=True)
        oos = oos_frame()
        oos_before = oos.copy(deep=True)
        analyze(df, oos)
        pd.testing.assert_frame_equal(df, before)
        pd.testing.assert_frame_equal(oos, oos_before)

    def test_required_validation(self):
        df = pd.DataFrame([episode_row(1)]).drop(columns=["mean_return_5d"])
        with self.assertRaises(ValueError):
            analyze(df, oos_frame())

    def test_missing_candidate_oos_does_not_infer(self):
        df = pd.DataFrame([
            episode_row(
                1,
                factor_a="intelligence_score",
                factor_b="trend_score",
            )
        ])
        out = analyze(df, oos_frame())
        target = out[
            (out.factor_a == "intelligence_score")
            & (out.factor_b == "trend_score")
        ].iloc[0]
        self.assertEqual(target.oos_stability, "NO_OOS_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
