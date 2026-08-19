import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from research.scenario_factor_reliability import REQUIRED_COLUMNS, assess_evidence, run


def row(scenario="CHOPPY", factor="intelligence_score", state="HIGH", obs=100, dates=10, symbols=10,
        pct=55.0, mean=0.2, median=0.1, worst=-2.0, best=3.0):
    return {
        "primary_scenario": scenario, "factor": factor, "factor_state": state,
        "observations": obs, "scenario_dates": dates, "symbols": symbols,
        "positive_5d_pct": pct, "mean_return_5d": mean, "median_return_5d": median,
        "worst_return_5d": worst, "best_return_5d": best,
    }


class ScenarioFactorReliabilityTests(unittest.TestCase):
    def test_deterministic_output(self):
        df = pd.DataFrame([row(), row(state="LOW", obs=350, dates=25, symbols=30, pct=40, mean=-.2, median=-.1)])
        a = assess_evidence(df)
        b = assess_evidence(df)
        pd.testing.assert_frame_equal(a, b)

    def test_input_not_mutated(self):
        df = pd.DataFrame([row()])
        before = df.copy(deep=True)
        assess_evidence(df)
        pd.testing.assert_frame_equal(df, before)

    def test_all_input_relationships_preserved(self):
        df = pd.DataFrame([row(state="HIGH"), row(state="LOW")])
        out = assess_evidence(df)
        self.assertEqual(len(out), len(df))
        self.assertEqual(set(out["factor_state"]), {"HIGH", "LOW"})

    def test_tiny_samples_remain_insufficient(self):
        out = assess_evidence(pd.DataFrame([row(obs=1, dates=1, symbols=1, pct=100)]))
        self.assertEqual(out.iloc[0].reliability_status, "INSUFFICIENT")

    def test_insufficient_observations(self):
        out = assess_evidence(pd.DataFrame([row(obs=29, dates=20, symbols=20)]))
        self.assertEqual(out.iloc[0].reliability_status, "INSUFFICIENT")

    def test_adequate_sample_classification(self):
        out = assess_evidence(pd.DataFrame([row(obs=150, dates=12, symbols=12)]))
        self.assertEqual(out.iloc[0].reliability_status, "PROMISING")

    def test_multiple_scenarios(self):
        out = assess_evidence(pd.DataFrame([row(scenario="CHOPPY"), row(scenario="TREND_UP")]))
        self.assertEqual(set(out.primary_scenario), {"CHOPPY", "TREND_UP"})

    def test_multiple_factors(self):
        out = assess_evidence(pd.DataFrame([row(factor="intelligence_score"), row(factor="liquidity_score")]))
        self.assertEqual(set(out.factor), {"intelligence_score", "liquidity_score"})

    def test_multiple_factor_states(self):
        out = assess_evidence(pd.DataFrame([row(state="HIGH"), row(state="MEDIUM"), row(state="LOW")]))
        self.assertEqual(set(out.factor_state), {"HIGH", "MEDIUM", "LOW"})

    def test_required_output_columns(self):
        out = assess_evidence(pd.DataFrame([row()]))
        self.assertEqual(list(out.columns), REQUIRED_COLUMNS + ["reliability_status", "reliability_score", "reliability_reason"])

    def test_missing_required_columns(self):
        df = pd.DataFrame([row()]).drop(columns=["symbols"])
        with self.assertRaises(ValueError):
            assess_evidence(df)

    def test_no_sqlite_access(self):
        import research.scenario_factor_reliability as mod
        with patch("sqlite3.connect", side_effect=AssertionError("SQLite access is forbidden")):
            with tempfile.TemporaryDirectory() as td:
                inp = Path(td) / "input.csv"
                out = Path(td) / "output.csv"
                pd.DataFrame([row()]).to_csv(inp, index=False)
                result = mod.run(inp, out)
                self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
