import unittest

import pandas as pd

from research.scenario_weapon_matrix import build_matrix


def make_rows(
    candidate,
    scenario_id,
    fingerprint,
    positive_pct,
    mean_spread,
    status="EARLY",
):
    return {
        "candidate": candidate,
        "scenario_id": scenario_id,
        "primary_scenario": "TREND_DOWN",
        "fingerprint": fingerprint,
        "oos_windows": 10,
        "positive_oos_windows": int(positive_pct / 10),
        "negative_oos_windows": 10 - int(positive_pct / 10),
        "positive_oos_pct": positive_pct,
        "mean_oos_spread": mean_spread,
        "median_oos_spread": mean_spread,
        "worst_oos_spread": -2.0,
        "best_oos_spread": 3.0,
        "evidence_status": status,
    }


class ScenarioWeaponMatrixTests(unittest.TestCase):

    def test_candidates_are_ranked_within_same_scenario(self):
        frame = pd.DataFrame(
            [
                make_rows(
                    "WEAPON_A",
                    "UNEXPLORED_1",
                    "fp1",
                    60.0,
                    0.5,
                ),
                make_rows(
                    "WEAPON_B",
                    "UNEXPLORED_1",
                    "fp1",
                    40.0,
                    -0.5,
                ),
            ]
        )

        result = build_matrix(frame)

        self.assertEqual(
            list(result["candidate"]),
            ["WEAPON_A", "WEAPON_B"],
        )

        self.assertEqual(
            list(result["rank_within_scenario"]),
            [1, 2],
        )

    def test_status_has_priority(self):
        frame = pd.DataFrame(
            [
                make_rows(
                    "WEAPON_A",
                    "UNEXPLORED_1",
                    "fp1",
                    90.0,
                    2.0,
                    "EARLY",
                ),
                make_rows(
                    "WEAPON_B",
                    "UNEXPLORED_1",
                    "fp1",
                    60.0,
                    0.5,
                    "VALIDATION_READY",
                ),
            ]
        )

        result = build_matrix(frame)

        self.assertEqual(
            result.iloc[0]["candidate"],
            "WEAPON_B",
        )

        self.assertEqual(
            result.iloc[0]["rank_within_scenario"],
            1,
        )

    def test_different_fingerprints_rank_independently(self):
        frame = pd.DataFrame(
            [
                make_rows(
                    "A",
                    "UNEXPLORED_1",
                    "fp1",
                    60.0,
                    1.0,
                ),
                make_rows(
                    "B",
                    "UNEXPLORED_1",
                    "fp2",
                    40.0,
                    -1.0,
                ),
            ]
        )

        result = build_matrix(frame)

        self.assertEqual(
            list(result["rank_within_scenario"]),
            [1, 1],
        )

    def test_input_is_not_mutated(self):
        frame = pd.DataFrame(
            [
                make_rows(
                    "A",
                    "UNEXPLORED_1",
                    "fp1",
                    60.0,
                    1.0,
                )
            ]
        )

        original = frame.copy(deep=True)

        build_matrix(frame)

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_required_columns_are_preserved(self):
        frame = pd.DataFrame(
            [
                make_rows(
                    "A",
                    "UNEXPLORED_1",
                    "fp1",
                    60.0,
                    1.0,
                )
            ]
        )

        result = build_matrix(frame)

        for column in [
            "scenario_id",
            "primary_scenario",
            "fingerprint",
            "candidate",
            "oos_windows",
            "positive_oos_pct",
            "mean_oos_spread",
            "evidence_status",
            "rank_within_scenario",
        ]:
            self.assertIn(
                column,
                result.columns,
            )

    def test_sorting_is_deterministic(self):
        frame = pd.DataFrame(
            [
                make_rows(
                    "B",
                    "UNEXPLORED_1",
                    "fp1",
                    50.0,
                    0.5,
                ),
                make_rows(
                    "A",
                    "UNEXPLORED_1",
                    "fp1",
                    50.0,
                    0.5,
                ),
            ]
        )

        first = build_matrix(frame)
        second = build_matrix(frame)

        pd.testing.assert_frame_equal(
            first,
            second,
        )

        self.assertEqual(
            list(first["candidate"]),
            ["A", "B"],
        )

    def test_missing_columns_raise_clear_error(self):
        frame = pd.DataFrame(
            {
                "candidate": ["A"],
            }
        )

        with self.assertRaises(ValueError):
            build_matrix(frame)


if __name__ == "__main__":
    unittest.main()