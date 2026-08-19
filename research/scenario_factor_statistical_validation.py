from __future__ import annotations

"""MarketBot Track-B: conservative statistical validation of scenario × factor evidence.

READ-ONLY RESEARCH ONLY.

Inputs:
    scenario_factor_conditional_evidence.csv
    scenario_factor_reliability.csv
    scenario_factor_predictive_strength.csv

Important statistical limitation:
The existing artifacts contain aggregate means/rates, not the underlying 5-day
return observations. Therefore this module does NOT fabricate a t-test,
Cohen's d, bootstrap sample, or mean-difference confidence interval.

It computes exact/Wilson binomial confidence intervals for the observed positive
rate and uses the existing conditional-vs-scenario mean/positive-rate lifts.
Mean-difference CI and observation-level stability are explicitly marked
NOT_ASSESSABLE when the raw observations are unavailable.

The existing INSUFFICIENT/EARLY/PROMISING/ROBUST reliability status is preserved.
Statistical status is a separate research classification and never implies
predictive validity or production eligibility.
"""

import argparse
import math
from pathlib import Path
from typing import Final

import pandas as pd

BASE_DIR: Final = Path(__file__).resolve().parents[1]
ARTIFACT_DIR: Final = BASE_DIR / "research" / "artifacts"
DEFAULT_INPUT: Final = ARTIFACT_DIR / "scenario_factor_conditional_evidence.csv"
DEFAULT_RELIABILITY: Final = ARTIFACT_DIR / "scenario_factor_reliability.csv"
DEFAULT_PREDICTIVE: Final = ARTIFACT_DIR / "scenario_factor_predictive_strength.csv"
DEFAULT_OUTPUT: Final = ARTIFACT_DIR / "scenario_factor_statistical_validation.csv"

RELATIONSHIP_COLUMNS: Final = [
    "primary_scenario", "factor", "factor_state",
    "observations", "scenario_dates", "symbols",
    "positive_5d_pct", "mean_return_5d", "median_return_5d",
    "worst_return_5d", "best_return_5d",
]
RELIABILITY_COLUMNS: Final = RELATIONSHIP_COLUMNS + [
    "reliability_status", "reliability_score", "reliability_reason"
]
PREDICTIVE_COLUMNS: Final = RELATIONSHIP_COLUMNS + [
    "scenario_baseline_observations", "scenario_baseline_positive_5d_pct",
    "scenario_baseline_mean_return_5d",
    "global_baseline_observations", "global_baseline_positive_5d_pct",
    "global_baseline_mean_return_5d",
    "positive_rate_lift_vs_scenario", "mean_return_lift_vs_scenario",
    "positive_rate_lift_vs_global", "mean_return_lift_vs_global",
    "predictive_strength_status", "predictive_strength_reason",
]

OUTPUT_COLUMNS: Final = RELATIONSHIP_COLUMNS + [
    "reliability_status", "reliability_score",
    "scenario_positive_rate_lift",
    "scenario_mean_return_lift",
    "positive_rate_ci_low",
    "positive_rate_ci_high",
    "positive_rate_ci_excludes_50",
    "mean_difference_ci_low",
    "mean_difference_ci_high",
    "mean_difference_ci_status",
    "effect_size",
    "effect_size_method",
    "date_stability_status",
    "statistical_evidence_status",
    "statistical_evidence_reason",
]

MIN_OBSERVATIONS: Final = 30
ALPHA: Final = 0.05
Z95: Final = 1.959963984540054


def _require(df: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"{name} is missing required columns: {', '.join(missing)}")


def _numeric(df: pd.DataFrame, columns: list[str], name: str) -> pd.DataFrame:
    out = df.copy(deep=True)
    for col in columns:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    bad = [c for c in columns if out[c].isna().any()]
    if bad:
        raise ValueError(f"{name} contains missing/non-numeric values: {', '.join(bad)}")
    return out


def wilson_interval(positive_pct: float, observations: int,
                    alpha: float = ALPHA) -> tuple[float, float]:
    """Wilson 95% CI for a binomial proportion, returned as percentages."""
    if observations <= 0:
        raise ValueError("observations must be positive")
    p = max(0.0, min(1.0, positive_pct / 100.0))
    z = Z95 if alpha == ALPHA else 1.959963984540054
    denom = 1.0 + z * z / observations
    centre = (p + z * z / (2.0 * observations)) / denom
    half = z * math.sqrt(
        p * (1.0 - p) / observations + z * z / (4.0 * observations * observations)
    ) / denom
    return (max(0.0, centre - half) * 100.0,
            min(1.0, centre + half) * 100.0)


def _range_normalized_effect(mean_lift: float, worst: float, best: float) -> float:
    """A bounded descriptive effect proxy; not Cohen's d."""
    span = float(best) - float(worst)
    if span <= 0:
        return 0.0
    return float(mean_lift) / span


def validate_inputs(conditional: pd.DataFrame,
                    reliability: pd.DataFrame,
                    predictive: pd.DataFrame) -> None:
    _require(conditional, RELATIONSHIP_COLUMNS, "Conditional evidence artifact")
    _require(reliability, RELIABILITY_COLUMNS, "Reliability artifact")
    _require(predictive, PREDICTIVE_COLUMNS, "Predictive-strength artifact")


def validate_no_duplicate_keys(df: pd.DataFrame, name: str) -> None:
    keys = ["primary_scenario", "factor", "factor_state"]
    if df.duplicated(keys, keep=False).any():
        raise ValueError(f"{name} contains duplicate relationship keys.")


def _join_inputs(conditional: pd.DataFrame,
                 reliability: pd.DataFrame,
                 predictive: pd.DataFrame) -> pd.DataFrame:
    validate_inputs(conditional, reliability, predictive)
    validate_no_duplicate_keys(conditional, "Conditional evidence artifact")
    validate_no_duplicate_keys(reliability, "Reliability artifact")
    validate_no_duplicate_keys(predictive, "Predictive-strength artifact")

    base = _numeric(
        conditional,
        ["observations", "scenario_dates", "symbols", "positive_5d_pct",
         "mean_return_5d", "median_return_5d", "worst_return_5d", "best_return_5d"],
        "Conditional evidence artifact",
    )

    rel = reliability[
        ["primary_scenario", "factor", "factor_state",
         "reliability_status", "reliability_score"]
    ].copy(deep=True)

    pred = predictive[
        ["primary_scenario", "factor", "factor_state",
         "scenario_baseline_observations", "scenario_baseline_positive_5d_pct",
         "scenario_baseline_mean_return_5d",
         "positive_rate_lift_vs_scenario", "mean_return_lift_vs_scenario"]
    ].copy(deep=True)

    merged = base.merge(
        rel, on=["primary_scenario", "factor", "factor_state"], how="left", validate="one_to_one"
    ).merge(
        pred, on=["primary_scenario", "factor", "factor_state"], how="left", validate="one_to_one"
    )
    if merged["reliability_status"].isna().any():
        raise ValueError("Every conditional relationship must have matching reliability evidence.")
    if merged["mean_return_lift_vs_scenario"].isna().any():
        raise ValueError("Every conditional relationship must have matching predictive-strength evidence.")
    return merged


def _classify(row: pd.Series, ci_low: float, ci_high: float,
              effect: float) -> tuple[str, str]:
    obs = int(row["observations"])
    rel = str(row["reliability_status"])
    lift = float(row["mean_return_lift_vs_scenario"])
    excludes = ci_low > 50.0 or ci_high < 50.0

    if obs < MIN_OBSERVATIONS or rel == "INSUFFICIENT":
        return "INSUFFICIENT", (
            f"Only {obs} observations or upstream reliability is INSUFFICIENT; "
            "statistical significance is not credited to tiny samples."
        )

    if excludes:
        direction = "positive" if ci_low > 50 else "negative"
        if abs(lift) >= 0.25 and abs(effect) >= 0.05:
            return "STATISTICALLY_SUPPORTED", (
                f"Wilson 95% CI for positive-return rate excludes 50% "
                f"({ci_low:.2f}% to {ci_high:.2f}%) with {direction} direction; "
                "mean-lift CI remains unavailable from aggregate-only input."
            )
        return "DIRECTIONALLY_SUPPORTED", (
            f"Wilson 95% CI excludes 50% ({ci_low:.2f}% to {ci_high:.2f}%); "
            "effect magnitude is modest and mean-difference CI is unavailable."
        )

    if abs(lift) >= 0.5 and abs(effect) >= 0.10:
        return "NO_STATISTICAL_SUPPORT", (
            f"Descriptive mean lift is {lift:.4f}% but the Wilson 95% positive-rate "
            "CI includes 50%; observed predictive strength is not statistically supported."
        )

    return "NO_STATISTICAL_SUPPORT", (
        "Wilson 95% positive-rate CI includes 50%; aggregate evidence does not "
        "provide statistical support for directional prediction."
    )


def assess_statistical_validation(
    conditional: pd.DataFrame,
    reliability: pd.DataFrame,
    predictive: pd.DataFrame,
) -> pd.DataFrame:
    """Return deterministic statistical validation without mutating inputs."""
    work = _join_inputs(
        conditional.copy(deep=True),
        reliability.copy(deep=True),
        predictive.copy(deep=True),
    )

    rows = []
    for _, row in work.iterrows():
        obs = int(row["observations"])
        ci_low, ci_high = wilson_interval(row["positive_5d_pct"], obs)

        mean_lift = float(row["mean_return_lift_vs_scenario"])
        effect = _range_normalized_effect(
            mean_lift, row["worst_return_5d"], row["best_return_5d"]
        )

        status, reason = _classify(row, ci_low, ci_high, effect)

        rows.append({
            **{c: row[c] for c in RELATIONSHIP_COLUMNS},
            "reliability_status": row["reliability_status"],
            "reliability_score": float(row["reliability_score"]),
            "scenario_positive_rate_lift": float(row["positive_rate_lift_vs_scenario"]),
            "scenario_mean_return_lift": mean_lift,
            "positive_rate_ci_low": ci_low,
            "positive_rate_ci_high": ci_high,
            "positive_rate_ci_excludes_50": bool(ci_low > 50 or ci_high < 50),
            "mean_difference_ci_low": float("nan"),
            "mean_difference_ci_high": float("nan"),
            "mean_difference_ci_status": "NOT_ASSESSABLE_AGGREGATE_ONLY",
            "effect_size": effect,
            "effect_size_method": "range_normalized_mean_lift_NOT_COHENS_D",
            "date_stability_status": "NOT_ASSESSABLE_AGGREGATE_ONLY",
            "statistical_evidence_status": status,
            "statistical_evidence_reason": reason,
        })

    out = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    return out.sort_values(
        ["statistical_evidence_status", "positive_rate_ci_excludes_50",
         "reliability_score", "observations",
         "primary_scenario", "factor", "factor_state"],
        ascending=[True, False, False, False, True, True, True],
        kind="mergesort",
    ).reset_index(drop=True)


def run(
    input_path: Path = DEFAULT_INPUT,
    reliability_path: Path = DEFAULT_RELIABILITY,
    predictive_path: Path = DEFAULT_PREDICTIVE,
    output_path: Path = DEFAULT_OUTPUT,
) -> pd.DataFrame:
    conditional = pd.read_csv(input_path)
    reliability = pd.read_csv(reliability_path)
    predictive = pd.read_csv(predictive_path)
    result = assess_statistical_validation(conditional, reliability, predictive)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Research-only statistical validation of Scenario × Factor evidence."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--reliability", type=Path, default=DEFAULT_RELIABILITY)
    parser.add_argument("--predictive", type=Path, default=DEFAULT_PREDICTIVE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    result = run(args.input, args.reliability, args.predictive, args.output)
    counts = result["statistical_evidence_status"].value_counts()

    print("\nMARKETBOT - SCENARIO × FACTOR STATISTICAL VALIDATION")
    print("=" * 72)
    print(f"Relationships evaluated : {len(result)}")
    print(f"STATISTICALLY_SUPPORTED : {counts.get('STATISTICALLY_SUPPORTED', 0)}")
    print(f"DIRECTIONALLY_SUPPORTED : {counts.get('DIRECTIONALLY_SUPPORTED', 0)}")
    print(f"NO_STATISTICAL_SUPPORT  : {counts.get('NO_STATISTICAL_SUPPORT', 0)}")
    print(f"INSUFFICIENT            : {counts.get('INSUFFICIENT', 0)}")
    print("\nTop statistically supported relationships:")
    cols = [
        "primary_scenario", "factor", "factor_state", "observations",
        "positive_5d_pct", "positive_rate_ci_low", "positive_rate_ci_high",
        "scenario_mean_return_lift", "statistical_evidence_status",
    ]
    supported = result[result["statistical_evidence_status"].isin(
        ["STATISTICALLY_SUPPORTED", "DIRECTIONALLY_SUPPORTED"]
    )]
    print((supported[cols].head(10) if not supported.empty else result[cols].head(10)).to_string(index=False))
    print(f"\nSaved: {args.output}")
    print("\nREAD-ONLY:")
    print("No SQLite writes, production scoring changes, factor-weight changes, candidate promotion, or trading changes.")
    print("No raw-return bootstrap/mean-difference CI was fabricated; aggregate-only limitations are reported explicitly.")


if __name__ == "__main__":
    main()
