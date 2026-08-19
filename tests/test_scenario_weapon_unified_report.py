from __future__ import annotations

import unittest

import pandas as pd

from research.scenario_weapon_unified_report import build_report


def make_input() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "scenario_id": "UNEXPLORED_20",
                "primary_scenario": "TREND_DOWN",
                "fingerprint": "abc123",
                "candidate": "TRACK_B_BASELINE_FAILURE",
                "oos_windows": 5,
                "positive_oos_windows": 3,
                "negative_oos_windows": 2,
                "positive_oos_pct": 60.0,
                "mean_oos_spread": 0.369,
                "median_oos_spread": 0.489,
                "worst_oos_spread": -2.16,
                "best_oos_spread": 4.07,
                "evidence_status": "EARLY",
                "research_decision": "CONTINUE_OOS",
                "decision_reason": "Evidence is early.",
            },
            {
                "scenario_id": "UNEXPLORED_20",
                "primary_scenario": "TREND_DOWN",
                "fingerprint": "abc123",
                "candidate": "TRACK_B_CONDITIONAL_SCORE",
                "oos_windows": 5,
                "positive_oos_windows": 2,
                "negative_oos_windows": 3,
                "positive_oos_pct": 40.0,
                "mean_oos_spread": -0.932,
                "median_oos_spread": -0.955,
                "worst_oos_spread": -5.36,
                "best_oos_spread": 2.48,
                "evidence_status": "EARLY",
                "research_decision": "CONTINUE_OOS",
                "decision_reason": "Evidence is early.",
            },
            {
                "scenario_id": "UNEXPLORED_33",
                "primary_scenario": "TREND_DOWN",
                "fingerprint": "xyz789",
                "candidate": "TRACK_B_FACTOR_AGREEMENT",
                "oos_windows": 20,
                "positive_oos_windows": 13,
                "negative_oos_windows": 7,
                "positive_oos_pct": 65.0,
                "mean_oos_spread": 0.75,
                "median_oos_spread": 0.61,
                "worst_oos_spread": -2.1,
                "best_oos_spread": 4.2,
                "evidence_status": "VALIDATION_READY",
                "research_decision": "VALIDATION_CANDIDATE",
                "decision_reason": "Validation threshold met.",
            },
        ]
    )


class UnifiedResearchReportTests(unittest.TestCase):

    def test_report_contains_required_output_columns(self):
        result = build_report(make_input())

        expected = {
            "scenario_id",
            "primary_scenario",
            "fingerprint",
            "candidate",
            "rank_within_scenario",
            "scenario_weapon_status",
            "research_conclusion",
        }

        self.assertTrue(expected.issubset(result.columns))

    def test_input_is_not_mutated(self):
        frame = make_input()
        before = frame.copy(deep=True)

        build_report(frame)

        pd.testing.assert_frame_equal(frame, before)

    def test_candidates_are_ranked_within_same_scenario(self):
        result = build_report(make_input())

        group = result[
            result["scenario_id"] == "UNEXPLORED_20"
        ].sort_values("rank_within_scenario")

        self.assertEqual(
            group.iloc[0]["candidate"],
            "TRACK_B_BASELINE_FAILURE",
        )

        self.assertEqual(
            group.iloc[0]["rank_within_scenario"],
            1,
        )

        self.assertEqual(
            group.iloc[1]["rank_within_scenario"],
            2,
        )

    def test_validation_candidate_is_identified(self):
        result = build_report(make_input())

        row = result[
            result["candidate"] == "TRACK_B_FACTOR_AGREEMENT"
        ].iloc[0]

        self.assertEqual(
            row["scenario_weapon_status"],
            "CANDIDATE",
        )

        self.assertIn(
            "Research-quality candidate",
            row["research_conclusion"],
        )

    def test_continue_oos_is_watch(self):
        result = build_report(make_input())

        row = result[
            result["candidate"] == "TRACK_B_BASELINE_FAILURE"
        ].iloc[0]

        self.assertEqual(
            row["scenario_weapon_status"],
            "WATCH",
        )

        self.assertEqual(
            row["research_decision"],
            "CONTINUE_OOS",
        )

    def test_output_is_deterministic(self):
        frame = make_input()

        first = build_report(frame)
        second = build_report(frame)

        pd.testing.assert_frame_equal(first, second)

    def test_missing_columns_raise_clear_error(self):
        frame = make_input().drop(columns=["fingerprint"])

        with self.assertRaises(ValueError) as context:
            build_report(frame)

        self.assertIn(
            "fingerprint",
            str(context.exception),
        )

    def test_multiple_scenarios_are_preserved(self):
        frame = pd.concat(
            [
                make_input(),
                make_input().assign(
                    scenario_id="UNEXPLORED_99",
                    fingerprint="different",
                ),
            ],
            ignore_index=True,
        )

        result = build_report(frame)

        # make_input() already contains two scenarios.
        # The appended dataframe introduces a third scenario.
        self.assertEqual(
            result["scenario_id"].nunique(),
            3,
        )


if __name__ == "__main__":
    unittest.main()
