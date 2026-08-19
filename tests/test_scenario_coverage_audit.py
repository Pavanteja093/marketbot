import unittest

import pandas as pd

from research.scenario_coverage_audit import (
    WEAPONS,
    build_audit,
)


class ScenarioCoverageAuditTests(unittest.TestCase):

    def scenarios(self):
        return pd.DataFrame(
            [
                {
                    "scenario_id": "UNEXPLORED_20",
                    "primary_scenario": "TREND_DOWN",
                    "fingerprint": "abc",
                    "scenario_observations": 28,
                    "first_observation": "2026-01-01",
                    "last_observation": "2026-07-01",
                },
                {
                    "scenario_id": "UNEXPLORED_33",
                    "primary_scenario": "TREND_DOWN",
                    "fingerprint": "def",
                    "scenario_observations": 10,
                    "first_observation": "2026-02-01",
                    "last_observation": "2026-07-01",
                },
            ]
        )

    def matrix(self):
        return pd.DataFrame(
            [
                {
                    "scenario_id": "UNEXPLORED_20",
                    "primary_scenario": "TREND_DOWN",
                    "fingerprint": "abc",
                    "candidate": "TRACK_B_BASELINE_FAILURE",
                    "oos_windows": 5,
                    "evidence_status": "EARLY",
                },
                {
                    "scenario_id": "UNEXPLORED_20",
                    "primary_scenario": "TREND_DOWN",
                    "fingerprint": "abc",
                    "candidate": "TRACK_B_CONDITIONAL_SCORE",
                    "oos_windows": 5,
                    "evidence_status": "EARLY",
                },
            ]
        )

    def test_all_six_weapons_are_represented(self):
        result = build_audit(
            self.scenarios(),
            self.matrix(),
        )

        self.assertEqual(
            result["candidate"].nunique(),
            6,
        )

        self.assertEqual(
            set(result["candidate"]),
            set(WEAPONS),
        )

    def test_cross_product_is_created(self):
        result = build_audit(
            self.scenarios(),
            self.matrix(),
        )

        self.assertEqual(
            len(result),
            2 * 6,
        )

    def test_existing_evidence_is_detected(self):
        result = build_audit(
            self.scenarios(),
            self.matrix(),
        )

        rows = result[
            (result["scenario_id"] == "UNEXPLORED_20")
            & (
                result["candidate"]
                == "TRACK_B_BASELINE_FAILURE"
            )
        ]

        self.assertEqual(
            rows.iloc[0]["coverage_status"],
            "EVIDENCE_PRESENT",
        )

    def test_missing_weapon_evidence_is_detected(self):
        result = build_audit(
            self.scenarios(),
            self.matrix(),
        )

        rows = result[
            (result["scenario_id"] == "UNEXPLORED_20")
            & (
                result["candidate"]
                == "TRACK_C_REGIME_AWARE"
            )
        ]

        self.assertEqual(
            rows.iloc[0]["coverage_status"],
            "NO_WEAPON_EVIDENCE",
        )

    def test_oos_gap_is_calculated(self):
        result = build_audit(
            self.scenarios(),
            self.matrix(),
        )

        rows = result[
            (result["scenario_id"] == "UNEXPLORED_20")
            & (
                result["candidate"]
                == "TRACK_B_BASELINE_FAILURE"
            )
        ]

        self.assertEqual(
            rows.iloc[0]["oos_gap_to_10"],
            5,
        )

        self.assertEqual(
            rows.iloc[0]["oos_gap_to_20"],
            15,
        )

    def test_input_is_not_mutated(self):
        scenarios = self.scenarios()
        matrix = self.matrix()

        original_scenarios = scenarios.copy(deep=True)
        original_matrix = matrix.copy(deep=True)

        build_audit(scenarios, matrix)

        pd.testing.assert_frame_equal(
            scenarios,
            original_scenarios,
        )

        pd.testing.assert_frame_equal(
            matrix,
            original_matrix,
        )

    def test_deterministic(self):
        first = build_audit(
            self.scenarios(),
            self.matrix(),
        )

        second = build_audit(
            self.scenarios(),
            self.matrix(),
        )

        pd.testing.assert_frame_equal(
            first,
            second,
        )


if __name__ == "__main__":
    unittest.main()
