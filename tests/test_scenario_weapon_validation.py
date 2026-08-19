from __future__ import annotations

import unittest

import pandas as pd

from research.scenario_weapon_validation import (
    build_family_report,
    build_validation,
    classify_evidence,
)


class ScenarioWeaponValidationTests(unittest.TestCase):

    def test_evidence_classification(self):
        self.assertEqual(
            classify_evidence(1),
            "INSUFFICIENT",
        )

        self.assertEqual(
            classify_evidence(5),
            "EARLY",
        )

        self.assertEqual(
            classify_evidence(9),
            "EARLY",
        )

        self.assertEqual(
            classify_evidence(10),
            "ELIGIBLE",
        )

    def test_validation_does_not_mutate_input(self):
        frame = pd.DataFrame(
            [
                {
                    "candidate": "BASELINE",
                    "scenario_id": "UNEXPLORED_20",
                    "primary_scenario": "TREND_DOWN",
                    "observations": 10,
                    "average_spread": 0.79,
                    "median_spread": 0.68,
                    "positive_day_pct": 70.0,
                    "worst_day": -2.1,
                    "best_day": 4.0,
                    "rank": 1,
                }
            ]
        )

        original = frame.copy(deep=True)

        build_validation(frame)

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_eligible_candidate_is_flagged(self):
        frame = pd.DataFrame(
            [
                {
                    "candidate": "BASELINE",
                    "scenario_id": "UNEXPLORED_20",
                    "primary_scenario": "TREND_DOWN",
                    "observations": 10,
                    "average_spread": 0.79,
                    "median_spread": 0.68,
                    "positive_day_pct": 70.0,
                    "worst_day": -2.1,
                    "best_day": 4.0,
                    "rank": 1,
                }
            ]
        )

        result = build_validation(frame)

        self.assertEqual(
            result.iloc[0]["evidence_status"],
            "ELIGIBLE",
        )

        self.assertEqual(
            result.iloc[0]["research_status"],
            "ELIGIBLE_NO_OOS",
        )

        self.assertTrue(
            result.iloc[0]["potential_signal"]
        )

    def test_negative_candidate_is_not_signal(self):
        frame = pd.DataFrame(
            [
                {
                    "candidate": "BASELINE",
                    "scenario_id": "UNEXPLORED_33",
                    "primary_scenario": "TREND_DOWN",
                    "observations": 10,
                    "average_spread": -1.08,
                    "median_spread": -0.91,
                    "positive_day_pct": 40.0,
                    "worst_day": -4.1,
                    "best_day": 1.4,
                    "rank": 3,
                }
            ]
        )

        result = build_validation(frame)

        self.assertFalse(
            result.iloc[0]["potential_signal"]
        )

    def test_family_report_aggregates_only_eligible(self):
        frame = pd.DataFrame(
            [
                {
                    "candidate": "BASELINE",
                    "scenario_id": "A",
                    "primary_scenario": "TREND_DOWN",
                    "observations": 10,
                    "average_spread": 1.0,
                    "median_spread": 0.8,
                    "positive_day_pct": 70.0,
                    "worst_day": -1.0,
                    "best_day": 2.0,
                    "rank": 1,
                },
                {
                    "candidate": "BASELINE",
                    "scenario_id": "B",
                    "primary_scenario": "TREND_DOWN",
                    "observations": 4,
                    "average_spread": 5.0,
                    "median_spread": 5.0,
                    "positive_day_pct": 100.0,
                    "worst_day": 5.0,
                    "best_day": 5.0,
                    "rank": 1,
                },
            ]
        )

        validation = build_validation(frame)
        family = build_family_report(validation)

        self.assertEqual(
            len(family),
            1,
        )

        self.assertEqual(
            family.iloc[0]["eligible_fingerprints"],
            1,
        )

        self.assertAlmostEqual(
            family.iloc[0]["mean_spread"],
            1.0,
        )


if __name__ == "__main__":
    unittest.main()