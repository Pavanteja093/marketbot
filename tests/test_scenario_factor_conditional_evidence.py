import unittest

import pandas as pd

from research.scenario_factor_conditional_evidence import build_evidence


def make_frame():
    rows = []

    for scenario in ["TREND_UP", "TREND_DOWN"]:
        for i, value in enumerate([30, 50, 70, 90]):
            rows.append(
                {
                    "trade_date": f"2026-01-{i + 1:02d}",
                    "index_name": f"STOCK{i}",
                    "primary_scenario": scenario,
                    "scenario_id": f"S{i}",
                    "fingerprint": f"F{i}",
                    "intelligence_score": value,
                    "relative_strength": value,
                    "trend_score": value,
                    "momentum_score": value,
                    "volatility_score": value,
                    "liquidity_score": value,
                    "return_5d": float(i - 1),
                }
            )

    return pd.DataFrame(rows)


class ScenarioFactorConditionalEvidenceTests(unittest.TestCase):

    def test_output_contains_expected_columns(self):
        result = build_evidence(make_frame())

        expected = {
            "primary_scenario",
            "factor",
            "factor_state",
            "observations",
            "scenario_dates",
            "symbols",
            "positive_5d_pct",
            "mean_return_5d",
            "median_return_5d",
            "worst_return_5d",
            "best_return_5d",
        }

        self.assertTrue(expected.issubset(result.columns))

    def test_multiple_scenarios_are_preserved(self):
        result = build_evidence(make_frame())

        self.assertEqual(
            set(result["primary_scenario"]),
            {"TREND_UP", "TREND_DOWN"},
        )

    def test_factor_states_are_created(self):
        result = build_evidence(make_frame())

        self.assertEqual(
            set(result["factor_state"]),
            {"LOW", "MEDIUM", "HIGH", "VERY_HIGH"},
        )

    def test_all_configured_factors_are_present(self):
        result = build_evidence(make_frame())

        self.assertEqual(
            result["factor"].nunique(),
            6,
        )

    def test_input_is_not_mutated(self):
        frame = make_frame()
        original = frame.copy(deep=True)

        build_evidence(frame)

        pd.testing.assert_frame_equal(frame, original)

    def test_deterministic_output(self):
        frame = make_frame()

        first = build_evidence(frame)
        second = build_evidence(frame)

        pd.testing.assert_frame_equal(first, second)

    def test_return_statistics_are_correct(self):
        frame = make_frame()

        result = build_evidence(frame)

        row = result[
            (result["primary_scenario"] == "TREND_UP")
            & (result["factor"] == "intelligence_score")
            & (result["factor_state"] == "HIGH")
        ].iloc[0]

        self.assertEqual(row["observations"], 1)
        self.assertEqual(row["mean_return_5d"], 1.0)
        self.assertEqual(row["positive_5d_pct"], 100.0)

    def test_missing_columns_raise_clear_error(self):
        frame = make_frame().drop(columns=["trend_score"])

        with self.assertRaisesRegex(
            ValueError,
            "trend_score",
        ):
            build_evidence(frame)


if __name__ == "__main__":
    unittest.main()
