from __future__ import annotations

"""
MarketBot - Scenario × Weapon Validation

Research-only validation layer.

Purpose:
    Determine which scenario + weapon combinations have enough evidence
    to deserve further research.

This module:
    - reads the existing scenario × weapon matrix
    - applies minimum-evidence rules
    - never executes candidate research
    - never writes to SQLite
    - never changes production scoring
    - never promotes a weapon

Evidence states:

    N < 5      -> INSUFFICIENT
    N 5-9      -> EARLY
    N >= 10    -> ELIGIBLE

OOS validation is deliberately NOT claimed here because the current
scenario_weapon_matrix is an aggregated evidence artifact and does not
contain chronological day-level observations.
"""

import argparse
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_INPUT = (
    BASE_DIR
    / "research"
    / "artifacts"
    / "scenario_weapon_matrix.csv"
)

DEFAULT_OUTPUT = (
    BASE_DIR
    / "research"
    / "artifacts"
    / "scenario_weapon_validation.csv"
)

MIN_INSUFFICIENT = 5
MIN_ELIGIBLE = 10


REQUIRED_COLUMNS = {
    "candidate",
    "scenario_id",
    "primary_scenario",
    "observations",
    "average_spread",
    "median_spread",
    "positive_day_pct",
    "worst_day",
    "best_day",
}


def classify_evidence(n: int) -> str:
    """Classify evidence quantity only."""
    if n < MIN_INSUFFICIENT:
        return "INSUFFICIENT"

    if n < MIN_ELIGIBLE:
        return "EARLY"

    return "ELIGIBLE"


def validate_input(frame: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(frame.columns)

    if missing:
        raise ValueError(
            "Scenario weapon matrix is missing required columns: "
            + ", ".join(sorted(missing))
        )


def build_validation(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Add evidence classification and conservative research status.

    This does not judge whether the weapon is profitable.
    It only determines whether the evidence quantity is sufficient.

    The input matrix may or may not contain a `rank` column.
    Rank is useful for display but is NOT required for validation.
    """

    work = frame.copy(deep=True)

    validate_input(work)

    work["observations"] = pd.to_numeric(
        work["observations"],
        errors="coerce",
    ).fillna(0).astype(int)

    work["average_spread"] = pd.to_numeric(
        work["average_spread"],
        errors="coerce",
    )

    work["median_spread"] = pd.to_numeric(
        work["median_spread"],
        errors="coerce",
    )

    work["positive_day_pct"] = pd.to_numeric(
        work["positive_day_pct"],
        errors="coerce",
    )

    work["evidence_status"] = work["observations"].map(
        classify_evidence
    )

    work["oos_status"] = "NOT_AVAILABLE"

    work["research_status"] = work["evidence_status"].map(
        {
            "INSUFFICIENT": "INSUFFICIENT",
            "EARLY": "EARLY",
            "ELIGIBLE": "ELIGIBLE_NO_OOS",
        }
    )

    work["potential_signal"] = (
        (work["evidence_status"] == "ELIGIBLE")
        & (work["average_spread"] > 0)
        & (work["median_spread"] > 0)
        & (work["positive_day_pct"] >= 60)
    )

    # Rank is descriptive metadata, not a validation requirement.
    # If the source artifact does not contain it, derive a deterministic
    # rank within each scenario using average spread.
    if "rank" not in work.columns:
        work["rank"] = (
            work.groupby("scenario_id")["average_spread"]
            .rank(
                ascending=False,
                method="dense",
            )
            .astype(int)
        )

    columns = [
        "candidate",
        "scenario_id",
        "primary_scenario",
        "observations",
        "average_spread",
        "median_spread",
        "positive_day_pct",
        "worst_day",
        "best_day",
        "evidence_status",
        "oos_status",
        "research_status",
        "potential_signal",
        "rank",
    ]

    return work[columns].sort_values(
        [
            "primary_scenario",
            "scenario_id",
            "rank",
            "candidate",
        ],
        kind="stable",
    ).reset_index(drop=True)


def build_family_report(validation: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate eligible fingerprints into broad market-scenario families.

    This is deliberately descriptive.

    A weapon is NOT declared successful simply because its family
    average is positive.
    """

    eligible = validation[
        validation["evidence_status"] == "ELIGIBLE"
    ].copy()

    if eligible.empty:
        return pd.DataFrame(
            columns=[
                "primary_scenario",
                "candidate",
                "eligible_fingerprints",
                "mean_spread",
                "median_spread",
                "positive_fingerprint_pct",
                "best_fingerprint_spread",
                "worst_fingerprint_spread",
                "research_status",
            ]
        )

    grouped = []

    for (scenario, candidate), group in eligible.groupby(
        ["primary_scenario", "candidate"],
        sort=True,
    ):
        spreads = pd.to_numeric(
            group["average_spread"],
            errors="coerce",
        ).dropna()

        if spreads.empty:
            continue

        grouped.append(
            {
                "primary_scenario": scenario,
                "candidate": candidate,
                "eligible_fingerprints": int(len(group)),
                "mean_spread": float(spreads.mean()),
                "median_spread": float(spreads.median()),
                "positive_fingerprint_pct": float(
                    (spreads > 0).mean() * 100
                ),
                "best_fingerprint_spread": float(spreads.max()),
                "worst_fingerprint_spread": float(spreads.min()),
                "research_status": (
                    "ELIGIBLE_NO_OOS"
                    if len(group) > 0
                    else "INSUFFICIENT"
                ),
            }
        )

    return pd.DataFrame(grouped)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Validate scenario × weapon evidence "
            "without modifying MarketBot."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    args = parser.parse_args()

    frame = pd.read_csv(args.input)

    validation = build_validation(frame)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    validation.to_csv(args.output, index=False)

    family = build_family_report(validation)

    family_output = args.output.with_name(
        "scenario_weapon_family_report.csv"
    )

    family.to_csv(family_output, index=False)

    print("=" * 90)
    print("MARKETBOT - SCENARIO × WEAPON VALIDATION")
    print("=" * 90)

    print()
    print(f"Matrix rows       : {len(frame)}")
    print(
        "Eligible rows     : "
        f"{int((validation['evidence_status'] == 'ELIGIBLE').sum())}"
    )
    print(
        "Early rows        : "
        f"{int((validation['evidence_status'] == 'EARLY').sum())}"
    )
    print(
        "Insufficient rows : "
        f"{int((validation['evidence_status'] == 'INSUFFICIENT').sum())}"
    )

    print()
    print("EVIDENCE DISTRIBUTION")
    print(
        validation["evidence_status"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print()
    print("ELIGIBLE SCENARIO × WEAPON COMBINATIONS")

    eligible = validation[
        validation["evidence_status"] == "ELIGIBLE"
    ]

    if eligible.empty:
        print("None.")

    else:
        print(
            eligible[
                [
                    "candidate",
                    "scenario_id",
                    "primary_scenario",
                    "observations",
                    "average_spread",
                    "median_spread",
                    "positive_day_pct",
                    "potential_signal",
                ]
            ].to_string(index=False)
        )

    print()
    print("SCENARIO FAMILY SUMMARY")

    if family.empty:
        print("No eligible scenario families.")

    else:
        print(family.to_string(index=False))

    print()
    print(f"Saved: {args.output}")
    print(f"Saved: {family_output}")
    print()
    print(
        "Research only: no candidate execution, database writes, "
        "production changes, or weapon promotion occurred."
    )


if __name__ == "__main__":
    main()