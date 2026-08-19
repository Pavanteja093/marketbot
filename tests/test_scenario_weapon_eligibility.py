import unittest

import pandas as pd

from research.scenario_weapon_eligibility import (
    build_eligibility,
    classify_eligibility,
)


class ScenarioWeaponEligibilityTests(unittest.TestCase):

    def base_frame(self):
        return pd.DataFrame(
            [
                {
                    "scenario_id": "UNEXPLORED_1",
                    "primary_scenario": "FLAT",
                    "fingerprint": "fp1",
                    "candidate": "TRACK_B_BASELINE_FAILURE",
                    "scenario_observations": 3,
                    "oos_windows": 0,
                    "oos_gap_to_10": 10,
                    "oos_gap_to_20": 20,
                    "evidence_status": "UNAVAILABLE",
                    "coverage_status": "NO_WEAPON_EVIDENCE",
                },
                {
                    "scenario_id": "UNEXPLORED_15",
                    "primary_scenario": "TREND_UP",
                    "fingerprint": "fp15",
                    "candidate": "TRACK_B_BASELINE_FAILURE",
                    "scenario_observations": 25,
                    "oos_windows": 0,
                    "oos_gap_to_10": 10,
                    "oos_gap_to_20": 20,
                    "evidence_status": "UNAVAILABLE",
                    "coverage_status": "NO_WEAPON_EVIDENCE",
                },
                {
                    "scenario_id": "UNEXPLORED_20",
                    "primary_scenario": "TREND_DOWN",
                    "fingerprint": "fp20",
                    "candidate": "TRACK_B_BASELINE_FAILURE",
                    "scenario_observations": 28,
                    "oos_windows": 5,
                    "oos_gap_to_10": 5,
                    "oos_gap_to_20": 15,
                    "evidence_status": "EARLY",
                    "coverage_status": "EVIDENCE_PRESENT",
                    "positive_oos_pct": 60.0,
                },
                {
                    "scenario_id": "UNEXPLORED_30",
                    "primary_scenario": "TREND_DOWN",
                    "fingerprint": "fp30",
                    "candidate": "TRACK_B_CONDITIONAL_SCORE",
                    "scenario_observations": 20,
                    "oos_windows": 10,
                    "oos_gap_to_10": 0,
                    "oos_gap_to_20": 10,
                    "evidence_status": "ELIGIBLE",
                    "coverage_status": "EVIDENCE_PRESENT",
                    "positive_oos_pct": 55.0,
                },
                {
                    "scenario_id": "UNEXPLORED_40",
                    "primary_scenario": "HIGH_VOL",
                    "fingerprint": "fp40",
                    "candidate": "TRACK_C_REGIME_AWARE",
                    "scenario_observations": 25,
                    "oos_windows": 20,
                    "oos_gap_to_10": 0,
                    "oos_gap_to_20": 0,
                    "evidence_status": "ELIGIBLE",
                    "coverage_status": "EVIDENCE_PRESENT",
                    "positive_oos_pct": 65.0,
                },
                {
                    "scenario_id": "UNEXPLORED_41",
                    "primary_scenario": "HIGH_VOL",
                    "fingerprint": "fp41",
                    "candidate": "TRACK_C_FACTOR_INTERACTION",
                    "scenario_observations": 25,
                    "oos_windows": 20,
                    "oos_gap_to_10": 0,
                    "oos_gap_to_20": 0,
                    "evidence_status": "ELIGIBLE",
                    "coverage_status": "EVIDENCE_PRESENT",
                    "positive_oos_pct": 45.0,
                },
            ]
        )

    def test_insufficient_scenario_history(self):
        frame = self.base_frame()
        result = build_eligibility(frame)

        row = result[
            result["scenario_id"] == "UNEXPLORED_1"
        ].iloc[0]

        self.assertEqual(
            row["eligibility_status"],
            "INSUFFICIENT_SCENARIO_HISTORY",
        )

        self.assertEqual(
            row["research_priority"],
            "LOW",
        )

        self.assertEqual(
            row["recommended_action"],
            "COLLECT_SCENARIO_HISTORY",
        )

    def test_researchable_without_evidence(self):
        frame = self.base_frame()
        result = build_eligibility(frame)

        row = result[
            result["scenario_id"] == "UNEXPLORED_15"
        ].iloc[0]

        self.assertEqual(
            row["eligibility_status"],
            "RESEARCHABLE_NO_EVIDENCE",
        )

        self.assertEqual(
            row["research_priority"],
            "HIGH",
        )

        self.assertEqual(
            row["recommended_action"],
            "START_OOS_RESEARCH",
        )

    def test_early_evidence_continues_oos(self):
        frame = self.base_frame()
        result = build_eligibility(frame)

        row = result[
            result["scenario_id"] == "UNEXPLORED_20"
        ].iloc[0]

        self.assertEqual(
            row["eligibility_status"],
            "EVIDENCE_PRESENT_EARLY",
        )

        self.assertEqual(
            row["research_priority"],
            "HIGH",
        )

        self.assertEqual(
            row["recommended_action"],
            "CONTINUE_OOS",
        )

    def test_ten_oos_windows_are_eligible(self):
        frame = self.base_frame()
        result = build_eligibility(frame)

        row = result[
            result["scenario_id"] == "UNEXPLORED_30"
        ].iloc[0]

        self.assertEqual(
            row["eligibility_status"],
            "EVIDENCE_ELIGIBLE",
        )

        self.assertEqual(
            row["recommended_action"],
            "RESEARCH_REVIEW",
        )

    def test_twenty_positive_oos_is_validation_ready(self):
        frame = self.base_frame()
        result = build_eligibility(frame)

        row = result[
            result["scenario_id"] == "UNEXPLORED_40"
        ].iloc[0]

        self.assertEqual(
            row["eligibility_status"],
            "VALIDATION_READY",
        )

        self.assertEqual(
            row["research_priority"],
            "CRITICAL",
        )

        self.assertEqual(
            row["recommended_action"],
            "VALIDATION_REVIEW",
        )

    def test_twenty_weak_oos_is_not_validation_ready(self):
        frame = self.base_frame()
        result = build_eligibility(frame)

        row = result[
            result["scenario_id"] == "UNEXPLORED_41"
        ].iloc[0]

        self.assertEqual(
            row["eligibility_status"],
            "EVIDENCE_ELIGIBLE",
        )

        self.assertNotEqual(
            row["eligibility_status"],
            "VALIDATION_READY",
        )

    def test_input_is_not_mutated(self):
        frame = self.base_frame()
        original = frame.copy(deep=True)

        build_eligibility(frame)

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_required_output_columns_exist(self):
        frame = self.base_frame()
        result = build_eligibility(frame)

        required = {
            "scenario_id",
            "primary_scenario",
            "fingerprint",
            "candidate",
            "scenario_observations",
            "oos_windows",
            "eligibility_status",
            "research_priority",
            "recommended_action",
        }

        self.assertTrue(
            required.issubset(result.columns)
        )

    def test_all_input_relationships_are_preserved(self):
        frame = self.base_frame()
        result = build_eligibility(frame)

        self.assertEqual(
            len(result),
            len(frame),
        )

        self.assertEqual(
            set(result["candidate"]),
            set(frame["candidate"]),
        )

    def test_deterministic_output(self):
        frame = self.base_frame()

        first = build_eligibility(frame)
        second = build_eligibility(frame)

        pd.testing.assert_frame_equal(
            first,
            second,
        )

    def test_classification_boundaries(self):
        self.assertEqual(
            classify_eligibility(9, 0, None),
            "INSUFFICIENT_SCENARIO_HISTORY",
        )

        self.assertEqual(
            classify_eligibility(10, 0, None),
            "RESEARCHABLE_NO_EVIDENCE",
        )

        self.assertEqual(
            classify_eligibility(10, 5, 50.0),
            "EVIDENCE_PRESENT_EARLY",
        )

        self.assertEqual(
            classify_eligibility(10, 10, 50.0),
            "EVIDENCE_ELIGIBLE",
        )

        self.assertEqual(
            classify_eligibility(20, 20, 59.9),
            "EVIDENCE_ELIGIBLE",
        )

        self.assertEqual(
            classify_eligibility(20, 20, 60.0),
            "VALIDATION_READY",
        )


if __name__ == "__main__":
    unittest.main()
