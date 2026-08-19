"""
MarketBot - Scenario x Weapon Eligibility Engine

Consumes:
    research/artifacts/scenario_coverage_audit.csv

Produces:
    research/artifacts/scenario_weapon_eligibility.csv

Research-only module.

This module does NOT:
- write to SQLite
- modify Track B
- modify Track C
- modify production scoring
- modify factor weights
- promote candidates
- make trading decisions

It converts scenario/weapon coverage into a deterministic
research eligibility and priority map.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_INPUT = (
    Path(__file__).resolve().parent
    / "artifacts"
    / "scenario_coverage_audit.csv"
)

DEFAULT_OUTPUT = (
    Path(__file__).resolve().parent
    / "artifacts"
    / "scenario_weapon_eligibility.csv"
)


REQUIRED_COLUMNS = {
    "scenario_id",
    "primary_scenario",
    "fingerprint",
    "scenario_observations",
    "candidate",
    "oos_windows",
    "oos_gap_to_10",
    "oos_gap_to_20",
    "evidence_status",
    "coverage_status",
}


STATUS_ORDER = {
    "VALIDATION_READY": 1,
    "EVIDENCE_ELIGIBLE": 2,
    "EVIDENCE_PRESENT_EARLY": 3,
    "RESEARCHABLE_NO_EVIDENCE": 4,
    "INSUFFICIENT_SCENARIO_HISTORY": 5,
}


PRIORITY_ORDER = {
    "CRITICAL": 1,
    "HIGH": 2,
    "MEDIUM": 3,
    "LOW": 4,
}


def validate_input(frame: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))

    if missing:
        raise ValueError(
            "Scenario eligibility input is missing required columns: "
            + ", ".join(missing)
        )


def classify_eligibility(
    scenario_observations: int,
    oos_windows: int,
    positive_oos_pct: float | None,
) -> str:
    """
    Conservative evidence classification.

    Scenario history:
        <10 observations -> insufficient for weapon research.

    OOS evidence:
        0 windows       -> researchable, no weapon evidence
        5-9 windows     -> early evidence
        >=10 windows    -> eligible
        >=20 + >=60% positive -> validation ready
    """

    if scenario_observations < 10:
        return "INSUFFICIENT_SCENARIO_HISTORY"

    if oos_windows >= 20:
        if positive_oos_pct is not None and positive_oos_pct >= 60.0:
            return "VALIDATION_READY"
        return "EVIDENCE_ELIGIBLE"

    if oos_windows >= 10:
        return "EVIDENCE_ELIGIBLE"

    if oos_windows >= 5:
        return "EVIDENCE_PRESENT_EARLY"

    return "RESEARCHABLE_NO_EVIDENCE"


def classify_priority(
    eligibility_status: str,
    scenario_observations: int,
    oos_windows: int,
) -> str:
    """
    Research priority is deliberately simple.

    CRITICAL:
        Validation-ready evidence exists.

    HIGH:
        Eligible evidence, or sufficiently mature scenarios
        that currently have no weapon evidence.

    MEDIUM:
        Early evidence, or moderately mature scenarios
        that have no weapon evidence.

    LOW:
        Scenario itself does not yet have enough history.
    """

    if eligibility_status == "VALIDATION_READY":
        return "CRITICAL"

    if eligibility_status == "EVIDENCE_ELIGIBLE":
        return "HIGH"

    if eligibility_status == "EVIDENCE_PRESENT_EARLY":
        return "HIGH"

    if eligibility_status == "RESEARCHABLE_NO_EVIDENCE":
        if scenario_observations >= 20:
            return "HIGH"
        return "MEDIUM"

    return "LOW"


def recommended_action(
    eligibility_status: str,
    scenario_observations: int,
    oos_windows: int,
) -> str:
    if eligibility_status == "VALIDATION_READY":
        return "VALIDATION_REVIEW"

    if eligibility_status == "EVIDENCE_ELIGIBLE":
        return "RESEARCH_REVIEW"

    if eligibility_status == "EVIDENCE_PRESENT_EARLY":
        return "CONTINUE_OOS"

    if eligibility_status == "RESEARCHABLE_NO_EVIDENCE":
        return "START_OOS_RESEARCH"

    return "COLLECT_SCENARIO_HISTORY"


def build_eligibility(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Build the immutable eligibility artifact.

    Input is never mutated.
    """

    validate_input(frame)

    work = frame.copy(deep=True)

    work["scenario_observations"] = pd.to_numeric(
        work["scenario_observations"],
        errors="coerce",
    ).fillna(0)

    work["oos_windows"] = pd.to_numeric(
        work["oos_windows"],
        errors="coerce",
    ).fillna(0)

    positive_candidates = [
        column
        for column in (
            "positive_oos_pct",
            "positive_oos_day_pct",
        )
        if column in work.columns
    ]

    if positive_candidates:
        positive_column = positive_candidates[0]
        work["positive_oos_pct"] = pd.to_numeric(
            work[positive_column],
            errors="coerce",
        )
    else:
        work["positive_oos_pct"] = pd.NA

    work["scenario_observations"] = (
        work["scenario_observations"].astype(int)
    )

    work["oos_windows"] = work["oos_windows"].astype(int)

    work["eligibility_status"] = [
        classify_eligibility(
            int(observations),
            int(oos),
            None if pd.isna(positive) else float(positive),
        )
        for observations, oos, positive in zip(
            work["scenario_observations"],
            work["oos_windows"],
            work["positive_oos_pct"],
        )
    ]

    work["research_priority"] = [
        classify_priority(
            status,
            int(observations),
            int(oos),
        )
        for status, observations, oos in zip(
            work["eligibility_status"],
            work["scenario_observations"],
            work["oos_windows"],
        )
    ]

    work["recommended_action"] = [
        recommended_action(
            status,
            int(observations),
            int(oos),
        )
        for status, observations, oos in zip(
            work["eligibility_status"],
            work["scenario_observations"],
            work["oos_windows"],
        )
    ]

    work["_priority_rank"] = work["research_priority"].map(
        PRIORITY_ORDER
    )

    work["_status_rank"] = work["eligibility_status"].map(
        STATUS_ORDER
    )

    work = work.sort_values(
        by=[
            "_priority_rank",
            "_status_rank",
            "scenario_observations",
            "oos_windows",
            "scenario_id",
            "candidate",
        ],
        ascending=[
            True,
            True,
            False,
            False,
            True,
            True,
        ],
        kind="mergesort",
    ).reset_index(drop=True)

    columns = [
        "scenario_id",
        "primary_scenario",
        "fingerprint",
        "candidate",
        "scenario_observations",
        "oos_windows",
        "oos_gap_to_10",
        "oos_gap_to_20",
        "evidence_status",
        "coverage_status",
        "eligibility_status",
        "research_priority",
        "recommended_action",
    ]

    return work[columns].copy()


def run(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
) -> pd.DataFrame:

    frame = pd.read_csv(input_path)

    result = build_eligibility(frame)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build MarketBot scenario x weapon eligibility map."
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

    result = run(
        input_path=args.input,
        output_path=args.output,
    )

    print("# MARKETBOT - SCENARIO × WEAPON ELIGIBILITY")

    print()
    print(f"Relationships assessed : {len(result)}")
    print(
        f"Distinct scenarios     : "
        f"{result['scenario_id'].nunique()}"
    )
    print(
        f"Distinct weapons       : "
        f"{result['candidate'].nunique()}"
    )

    print()
    print("ELIGIBILITY COUNTS")
    print(
        result["eligibility_status"]
        .value_counts()
        .rename_axis("eligibility_status")
        .to_string()
    )

    print()
    print("PRIORITY COUNTS")
    print(
        result["research_priority"]
        .value_counts()
        .rename_axis("research_priority")
        .to_string()
    )

    print()
    print("TOP RESEARCH QUEUE")

    display_columns = [
        "scenario_id",
        "primary_scenario",
        "candidate",
        "scenario_observations",
        "oos_windows",
        "eligibility_status",
        "research_priority",
        "recommended_action",
    ]

    print(
        result[display_columns]
        .head(30)
        .to_string(index=False)
    )

    print()
    print(f"Saved: {DEFAULT_OUTPUT}")

    print()
    print(
        "READ-ONLY: no SQLite writes, production scoring changes, "
        "factor-weight changes, Track B/C changes, promotion, "
        "or live trading."
    )


if __name__ == "__main__":
    main()
