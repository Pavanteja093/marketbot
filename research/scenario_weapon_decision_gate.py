from __future__ import annotations

"""Read-only research decision gate for Scenario × Weapon evidence."""

import argparse
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "scenario_id",
    "primary_scenario",
    "fingerprint",
    "candidate",
    "oos_windows",
    "positive_oos_windows",
    "negative_oos_windows",
    "positive_oos_pct",
    "mean_oos_spread",
    "median_oos_spread",
    "worst_oos_spread",
    "best_oos_spread",
    "evidence_status",
}


OUTPUT_COLUMNS = [
    "scenario_id",
    "primary_scenario",
    "fingerprint",
    "candidate",
    "oos_windows",
    "positive_oos_windows",
    "negative_oos_windows",
    "positive_oos_pct",
    "mean_oos_spread",
    "median_oos_spread",
    "worst_oos_spread",
    "best_oos_spread",
    "evidence_status",
    "research_decision",
    "decision_reason",
]


def validate_input(frame: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))

    if missing:
        raise ValueError(
            "Scenario weapon decision gate is missing required columns: "
            + ", ".join(missing)
        )


def decide_row(row: pd.Series) -> tuple[str, str]:
    """
    Apply a conservative research-only decision.

    This is NOT a trading decision.

    Rules:

    INSUFFICIENT
        -> COLLECT_MORE_EVIDENCE

    EARLY
        -> CONTINUE_OOS

    ELIGIBLE + positive mean spread + >= 60% positive OOS
        -> RESEARCH_REVIEW

    ELIGIBLE otherwise
        -> CONTINUE_OOS

    VALIDATION_READY + positive mean spread + >= 60% positive OOS
        -> VALIDATION_CANDIDATE

    VALIDATION_READY otherwise
        -> RESEARCH_REVIEW
    """

    status = str(row["evidence_status"])

    positive_pct = pd.to_numeric(
        row["positive_oos_pct"],
        errors="coerce",
    )

    mean_spread = pd.to_numeric(
        row["mean_oos_spread"],
        errors="coerce",
    )

    if status == "INSUFFICIENT":
        return (
            "COLLECT_MORE_EVIDENCE",
            "Fewer than 5 genuine OOS windows.",
        )

    if status == "EARLY":
        return (
            "CONTINUE_OOS",
            "Evidence is early; fewer than 10 genuine OOS windows.",
        )

    if pd.isna(positive_pct) or pd.isna(mean_spread):
        return (
            "CONTINUE_OOS",
            "Required OOS performance metrics are unavailable.",
        )

    positive = float(positive_pct)
    mean = float(mean_spread)

    if status == "ELIGIBLE":
        if mean > 0.0 and positive >= 60.0:
            return (
                "RESEARCH_REVIEW",
                "Eligible evidence is positive but requires deeper validation.",
            )

        return (
            "CONTINUE_OOS",
            "Evidence is eligible but does not meet the positive research threshold.",
        )

    if status == "VALIDATION_READY":
        if mean > 0.0 and positive >= 60.0:
            return (
                "VALIDATION_CANDIDATE",
                "At least 20 OOS windows with positive mean spread and >=60% positive OOS.",
            )

        return (
            "RESEARCH_REVIEW",
            "Evidence reached the validation threshold but performance is not sufficiently positive.",
        )

    return (
        "CONTINUE_OOS",
        "Unknown or non-promotable evidence state.",
    )


def build_decisions(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Build deterministic research decisions.

    Input is never mutated.
    No database writes occur.
    No production decisions occur.
    """

    validate_input(frame)

    work = frame.copy(deep=True)

    decisions = work.apply(
        decide_row,
        axis=1,
    )

    work["research_decision"] = [
        item[0] for item in decisions
    ]

    work["decision_reason"] = [
        item[1] for item in decisions
    ]

    return (
        work[OUTPUT_COLUMNS]
        .sort_values(
            [
                "scenario_id",
                "fingerprint",
                "candidate",
            ],
            kind="mergesort",
        )
        .reset_index(drop=True)
    )


def run(
    input_path: Path,
    output_path: Path,
) -> pd.DataFrame:

    frame = pd.read_csv(input_path)

    result = build_decisions(frame)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        output_path,
        index=False,
    )

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build read-only Scenario × Weapon research decisions."
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path(
            "research/artifacts/"
            "scenario_weapon_evidence_accumulation.csv"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "research/artifacts/"
            "scenario_weapon_decision_gate.csv"
        ),
    )

    args = parser.parse_args()

    result = run(
        args.input,
        args.output,
    )

    print()
    print("MARKETBOT - SCENARIO × WEAPON RESEARCH DECISION GATE")
    print("=" * 72)

    if result.empty:
        print("No evidence available.")
        return

    display_columns = [
        "scenario_id",
        "primary_scenario",
        "candidate",
        "oos_windows",
        "positive_oos_pct",
        "mean_oos_spread",
        "evidence_status",
        "research_decision",
    ]

    print(
        result[display_columns]
        .round(4)
        .to_string(index=False)
    )

    print()
    print("DECISION MEANINGS")
    print("COLLECT_MORE_EVIDENCE : insufficient history")
    print("CONTINUE_OOS          : keep collecting genuine OOS evidence")
    print("RESEARCH_REVIEW       : relationship deserves deeper validation")
    print("VALIDATION_CANDIDATE  : research-quality validation candidate")

    print()
    print("Saved:")
    print(args.output)

    print()
    print(
        "READ-ONLY: no SQLite writes, production scoring changes, "
        "factor-weight changes, Track B/C changes, candidate promotion, "
        "or live trading."
    )


if __name__ == "__main__":
    main()
