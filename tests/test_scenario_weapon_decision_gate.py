import unittest

import pandas as pd

from research.scenario_weapon_decision_gate import (
    build_decisions,
    decide_row,
)


def make_row(
    status="EARLY",
    oos_windows=5,
    positive_pct=60.0,
    mean_spread=0.5,
):
    return {
        "scenario_id": "UNEXPLORED_20",
        "primary_scenario": "TREND_DOWN",
        "fingerprint": "fp1",
        "candidate": "WEAPON_A",
        "oos_windows": oos_windows,
        "positive_oos_windows": 3,
        "negative_oos_windows": 2,
        "positive_oos_pct": positive_pct,
        "mean_oos_spread": mean_spread,
        "median_oos_spread": mean_spread,
        "worst_oos_spread": -2.0,
        "best_oos_spread": 3.0,
        "evidence_status": status,
    }


class ScenarioWeaponDecisionGateTests(unittest.TestCase):

    def test_insufficient_requires_more_evidence(self):
        decision, _ = decide_row(
            pd.Series(
                make_row(
                    status="INSUFFICIENT",
                    oos_windows=4,
                )
            )
        )

        self.assertEqual(
            decision,
            "COLLECT_MORE_EVIDENCE",
        )

    def test_early_continues_oos(self):
        decision, _ = decide_row(
            pd.Series(
                make_row(
                    status="EARLY",
                    oos_windows=5,
                )
            )
        )

        self.assertEqual(
            decision,
            "CONTINUE_OOS",
        )

    def test_positive_eligible_requires_review(self):
        decision, _ = decide_row(
            pd.Series(
                make_row(
                    status="ELIGIBLE",
                    oos_windows=10,
                    positive_pct=70.0,
                    mean_spread=0.5,
                )
            )
        )

        self.assertEqual(
            decision,
            "RESEARCH_REVIEW",
        )

    def test_negative_eligible_continues(self):
        decision, _ = decide_row(
            pd.Series(
                make_row(
                    status="ELIGIBLE",
                    oos_windows=10,
                    positive_pct=40.0,
                    mean_spread=-0.5,
                )
            )
        )

        self.assertEqual(
            decision,
            "CONTINUE_OOS",
        )

    def test_validation_ready_positive_becomes_candidate(self):
        decision, _ = decide_row(
            pd.Series(
                make_row(
                    status="VALIDATION_READY",
                    oos_windows=20,
                    positive_pct=65.0,
                    mean_spread=0.4,
                )
            )
        )

        self.assertEqual(
            decision,
            "VALIDATION_CANDIDATE",
        )

    def test_validation_ready_negative_requires_review(self):
        decision, _ = decide_row(
            pd.Series(
                make_row(
                    status="VALIDATION_READY",
                    oos_windows=20,
                    positive_pct=55.0,
                    mean_spread=-0.2,
                )
            )
        )

        self.assertEqual(
            decision,
            "RESEARCH_REVIEW",
        )

    def test_input_is_not_mutated(self):
        frame = pd.DataFrame(
            [
                make_row(),
            ]
        )

        original = frame.copy(deep=True)

        build_decisions(frame)

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_multiple_rows_are_preserved(self):
        frame = pd.DataFrame(
            [
                make_row(
                    status="EARLY",
                    oos_windows=5,
                ),
                {
                    **make_row(
                        status="ELIGIBLE",
                        oos_windows=10,
                        positive_pct=40.0,
                        mean_spread=-0.5,
                    ),
                    "candidate": "WEAPON_B",
                },
            ]
        )

        result = build_decisions(frame)

        self.assertEqual(
            len(result),
            2,
        )

        self.assertEqual(
            set(result["candidate"]),
            {"WEAPON_A", "WEAPON_B"},
        )

    def test_missing_columns_raise_clear_error(self):
        frame = pd.DataFrame(
            {
                "candidate": ["A"],
            }
        )

        with self.assertRaises(ValueError):
            build_decisions(frame)

    def test_output_is_deterministic(self):
        frame = pd.DataFrame(
            [
                make_row(
                    status="EARLY",
                    oos_windows=5,
                ),
                {
                    **make_row(
                        status="EARLY",
                        oos_windows=5,
                    ),
                    "candidate": "WEAPON_B",
                },
            ]
        )

        first = build_decisions(frame)
        second = build_decisions(frame)

        pd.testing.assert_frame_equal(
            first,
            second,
        )


if __name__ == "__main__":
    unittest.main()
