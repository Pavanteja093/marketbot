import unittest

import pandas as pd

from research.scenario_weapon_evidence_expansion_planner import (
    build_plan,
)


class ScenarioWeaponEvidenceExpansionPlannerTests(unittest.TestCase):

    def sample(self):
        return pd.DataFrame(
            [
                {
                    "scenario_id": "UNEXPLORED_20",
                    "primary_scenario": "TREND_DOWN",
                    "fingerprint": "abc",
                    "candidate": "TRACK_B_BASELINE_FAILURE",
                    "oos_windows": 5,
                    "positive_oos_pct": 60.0,
                    "mean_oos_spread": 0.5,
                    "evidence_status": "EARLY",
                    "research_decision": "CONTINUE_OOS",
                },
                {
                    "scenario_id": "UNEXPLORED_30",
                    "primary_scenario": "CHOPPY",
                    "fingerprint": "def",
                    "candidate": "TRACK_B_CONDITIONAL_SCORE",
                    "oos_windows": 12,
                    "positive_oos_pct": 55.0,
                    "mean_oos_spread": 0.2,
                    "evidence_status": "ELIGIBLE",
                    "research_decision": "RESEARCH_REVIEW",
                },
                {
                    "scenario_id": "UNEXPLORED_40",
                    "primary_scenario": "TREND_UP",
                    "fingerprint": "ghi",
                    "candidate": "TRACK_C_REGIME_AWARE",
                    "oos_windows": 22,
                    "positive_oos_pct": 65.0,
                    "mean_oos_spread": 0.8,
                    "evidence_status": "VALIDATION_READY",
                    "research_decision": "VALIDATION_CANDIDATE",
                },
            ]
        )

    def test_windows_to_10(self):
        result = build_plan(self.sample())

        row = result[
            result["scenario_id"] == "UNEXPLORED_20"
        ].iloc[0]

        self.assertEqual(row["windows_to_10"], 5)

    def test_windows_to_20(self):
        result = build_plan(self.sample())

        row = result[
            result["scenario_id"] == "UNEXPLORED_20"
        ].iloc[0]

        self.assertEqual(row["windows_to_20"], 15)

    def test_early_candidate_is_high_priority(self):
        result = build_plan(self.sample())

        row = result[
            result["scenario_id"] == "UNEXPLORED_20"
        ].iloc[0]

        self.assertEqual(row["priority"], "HIGH")
        self.assertEqual(
            row["recommended_action"],
            "ACCUMULATE_TO_ELIGIBLE",
        )

    def test_validation_candidate_is_review(self):
        result = build_plan(self.sample())

        row = result[
            result["scenario_id"] == "UNEXPLORED_40"
        ].iloc[0]

        self.assertEqual(
            row["priority"],
            "VALIDATION_REVIEW",
        )
        self.assertEqual(
            row["recommended_action"],
            "VALIDATE_CANDIDATE",
        )

    def test_input_is_not_mutated(self):
        source = self.sample()
        original = source.copy(deep=True)

        build_plan(source)

        pd.testing.assert_frame_equal(source, original)

    def test_deterministic(self):
        first = build_plan(self.sample())
        second = build_plan(self.sample())

        pd.testing.assert_frame_equal(first, second)

    def test_missing_columns_raise_clear_error(self):
        frame = pd.DataFrame(
            [
                {
                    "scenario_id": "X",
                    "candidate": "Y",
                }
            ]
        )

        with self.assertRaisesRegex(
            ValueError,
            "missing required columns",
        ):
            build_plan(frame)


if __name__ == "__main__":
    unittest.main()
