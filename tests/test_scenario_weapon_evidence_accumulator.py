import unittest

import pandas as pd

from research.scenario_weapon_evidence_accumulator import (
    build_accumulation,
    classify_evidence,
)


def make_row(
    candidate="WEAPON_A",
    scenario_id="UNEXPLORED_20",
    fingerprint="fp1",
    oos_windows=5,
    positive_pct=60.0,
    mean_spread=0.5,
):
    positive = int(round(oos_windows * positive_pct / 100.0))

    return {
        "candidate": candidate,
        "scenario_id": scenario_id,
        "primary_scenario": "TREND_DOWN",
        "fingerprint": fingerprint,
        "oos_windows": oos_windows,
        "positive_oos_windows": positive,
        "negative_oos_windows": oos_windows - positive,
        "positive_oos_pct": positive_pct,
        "mean_oos_spread": mean_spread,
        "median_oos_spread": mean_spread,
        "worst_oos_spread": -2.0,
        "best_oos_spread": 3.0,
    }


class ScenarioWeaponEvidenceAccumulatorTests(unittest.TestCase):

    def test_insufficient_evidence(self):
        self.assertEqual(
            classify_evidence(4, 75.0),
            "INSUFFICIENT",
        )

    def test_early_evidence(self):
        self.assertEqual(
            classify_evidence(5, 60.0),
            "EARLY",
        )

        self.assertEqual(
            classify_evidence(9, 80.0),
            "EARLY",
        )

    def test_eligible_evidence(self):
        self.assertEqual(
            classify_evidence(10, 50.0),
            "ELIGIBLE",
        )

    def test_validation_ready_requires_twenty_windows(self):
        self.assertEqual(
            classify_evidence(19, 80.0),
            "ELIGIBLE",
        )

        self.assertEqual(
            classify_evidence(20, 60.0),
            "VALIDATION_READY",
        )

    def test_twenty_windows_with_weak_positive_rate_is_not_ready(self):
        self.assertEqual(
            classify_evidence(20, 59.9),
            "ELIGIBLE",
        )

    def test_build_accumulation(self):
        frame = pd.DataFrame(
            [
                make_row(
                    candidate="A",
                    oos_windows=5,
                    positive_pct=60.0,
                ),
                make_row(
                    candidate="B",
                    oos_windows=10,
                    positive_pct=50.0,
                ),
            ]
        )

        result = build_accumulation(frame)

        self.assertEqual(
            list(result["evidence_status"]),
            ["EARLY", "ELIGIBLE"],
        )

    def test_input_is_not_mutated(self):
        frame = pd.DataFrame(
            [
                make_row(),
            ]
        )

        original = frame.copy(deep=True)

        build_accumulation(frame)

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_multiple_scenarios_are_preserved(self):
        frame = pd.DataFrame(
            [
                make_row(
                    candidate="A",
                    scenario_id="UNEXPLORED_20",
                    fingerprint="fp1",
                ),
                make_row(
                    candidate="B",
                    scenario_id="UNEXPLORED_33",
                    fingerprint="fp2",
                ),
            ]
        )

        result = build_accumulation(frame)

        self.assertEqual(
            len(result),
            2,
        )

        self.assertEqual(
            set(result["scenario_id"]),
            {"UNEXPLORED_20", "UNEXPLORED_33"},
        )

    def test_missing_columns_raise_clear_error(self):
        frame = pd.DataFrame(
            {
                "candidate": ["A"],
            }
        )

        with self.assertRaises(ValueError):
            build_accumulation(frame)

    def test_result_is_deterministic(self):
        frame = pd.DataFrame(
            [
                make_row(candidate="B"),
                make_row(candidate="A"),
            ]
        )

        first = build_accumulation(frame)
        second = build_accumulation(frame)

        pd.testing.assert_frame_equal(
            first,
            second,
        )


if __name__ == "__main__":
    unittest.main()
