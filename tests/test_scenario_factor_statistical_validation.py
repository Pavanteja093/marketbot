import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from research.scenario_factor_statistical_validation import (
    OUTPUT_COLUMNS,
    assess_statistical_validation,
    wilson_interval,
)


def row(
    scenario="CHOPPY", factor="intelligence_score", state="HIGH",
    obs=200, dates=20, symbols=30, pct=60.0, mean=1.0,
    median=0.8, worst=-5.0, best=8.0,
):
    return {
        "primary_scenario": scenario, "factor": factor, "factor_state": state,
        "observations": obs, "scenario_dates": dates, "symbols": symbols,
        "positive_5d_pct": pct, "mean_return_5d": mean,
        "median_return_5d": median, "worst_return_5d": worst, "best_return_5d": best,
    }


def reliability(df):
    out = df.copy(deep=True)
    out["reliability_status"] = "PROMISING"
    out["reliability_score"] = 80.0
    out["reliability_reason"] = "test"
    return out


def predictive(df, lift=0.8):
    out = df.copy(deep=True)
    out["scenario_baseline_observations"] = 1000
    out["scenario_baseline_positive_5d_pct"] = 50.0
    out["scenario_baseline_mean_return_5d"] = 0.2
    out["global_baseline_observations"] = 10000
    out["global_baseline_positive_5d_pct"] = 51.0
    out["global_baseline_mean_return_5d"] = 0.2
    out["positive_rate_lift_vs_scenario"] = out["positive_5d_pct"] - 50.0
    out["mean_return_lift_vs_scenario"] = lift
    out["positive_rate_lift_vs_global"] = out["positive_5d_pct"] - 51.0
    out["mean_return_lift_vs_global"] = lift
    out["predictive_strength_status"] = "POSITIVE"
    out["predictive_strength_reason"] = "test"
    return out


class ScenarioFactorStatisticalValidationTests(unittest.TestCase):
    def test_wilson_interval_deterministic(self):
        self.assertEqual(wilson_interval(60.0, 200), wilson_interval(60.0, 200))

    def test_input_not_mutated(self):
        d = pd.DataFrame([row()])
        r = reliability(d)
        p = predictive(d)
        d0, r0, p0 = d.copy(deep=True), r.copy(deep=True), p.copy(deep=True)
        assess_statistical_validation(d, r, p)
        pd.testing.assert_frame_equal(d, d0)
        pd.testing.assert_frame_equal(r, r0)
        pd.testing.assert_frame_equal(p, p0)

    def test_relationships_preserved(self):
        d = pd.DataFrame([row(), row(state="LOW", factor="trend_score", scenario="TREND_UP")])
        out = assess_statistical_validation(d, reliability(d), predictive(d))
        self.assertEqual(len(out), 2)
        self.assertEqual(set(out["factor_state"]), {"HIGH", "LOW"})

    def test_tiny_sample_insufficient(self):
        d = pd.DataFrame([row(obs=1, dates=1, symbols=1, pct=100.0)])
        r = reliability(d)
        r["reliability_status"] = "ROBUST"  # statistical layer must still honor sample size
        out = assess_statistical_validation(d, r, predictive(d))
        self.assertEqual(out.iloc[0].statistical_evidence_status, "INSUFFICIENT")

    def test_insufficient_upstream_reliability(self):
        d = pd.DataFrame([row(obs=100)])
        r = reliability(d)
        r["reliability_status"] = "INSUFFICIENT"
        out = assess_statistical_validation(d, r, predictive(d))
        self.assertEqual(out.iloc[0].statistical_evidence_status, "INSUFFICIENT")

    def test_statistically_supported_direction(self):
        d = pd.DataFrame([row(obs=1000, pct=65.0, mean=1.0)])
        out = assess_statistical_validation(d, reliability(d), predictive(d, lift=1.0))
        self.assertEqual(out.iloc[0].statistical_evidence_status, "STATISTICALLY_SUPPORTED")
        self.assertTrue(out.iloc[0].positive_rate_ci_excludes_50)

    def test_no_statistical_support(self):
        d = pd.DataFrame([row(obs=100, pct=51.0, mean=0.1)])
        out = assess_statistical_validation(d, reliability(d), predictive(d, lift=0.8))
        self.assertEqual(out.iloc[0].statistical_evidence_status, "NO_STATISTICAL_SUPPORT")

    def test_multiple_scenarios(self):
        d = pd.DataFrame([row(), row(scenario="TREND_UP", factor="trend_score", state="LOW")])
        out = assess_statistical_validation(d, reliability(d), predictive(d))
        self.assertEqual(set(out.primary_scenario), {"CHOPPY", "TREND_UP"})

    def test_multiple_factors(self):
        d = pd.DataFrame([row(), row(factor="liquidity_score", state="MEDIUM")])
        out = assess_statistical_validation(d, reliability(d), predictive(d))
        self.assertEqual(set(out.factor), {"intelligence_score", "liquidity_score"})

    def test_multiple_factor_states(self):
        d = pd.DataFrame([row(state="HIGH"), row(state="MEDIUM"), row(state="LOW")])
        out = assess_statistical_validation(d, reliability(d), predictive(d))
        self.assertEqual(set(out.factor_state), {"HIGH", "MEDIUM", "LOW"})

    def test_required_output_columns(self):
        d = pd.DataFrame([row()])
        out = assess_statistical_validation(d, reliability(d), predictive(d))
        self.assertEqual(list(out.columns), OUTPUT_COLUMNS)

    def test_missing_required_column(self):
        d = pd.DataFrame([row()]).drop(columns=["symbols"])
        with self.assertRaises(ValueError):
            assess_statistical_validation(d, reliability(d), predictive(d))

    def test_duplicate_relationship_rejected(self):
        d = pd.DataFrame([row(), row()])
        with self.assertRaises(ValueError):
            assess_statistical_validation(d, reliability(d), predictive(d))

    def test_mean_difference_ci_not_fabricated(self):
        d = pd.DataFrame([row()])
        out = assess_statistical_validation(d, reliability(d), predictive(d))
        self.assertEqual(out.iloc[0].mean_difference_ci_status, "NOT_ASSESSABLE_AGGREGATE_ONLY")
        self.assertTrue(pd.isna(out.iloc[0].mean_difference_ci_low))

    def test_stability_not_fabricated(self):
        d = pd.DataFrame([row()])
        out = assess_statistical_validation(d, reliability(d), predictive(d))
        self.assertEqual(out.iloc[0].date_stability_status, "NOT_ASSESSABLE_AGGREGATE_ONLY")

    def test_no_sqlite_access(self):
        source = Path(__import__("research.scenario_factor_statistical_validation",
                                  fromlist=["__file__"]).__file__).read_text(encoding="utf-8")
        self.assertNotIn("sqlite3", source)
        self.assertNotIn("connect(", source)


if __name__ == "__main__":
    unittest.main()
