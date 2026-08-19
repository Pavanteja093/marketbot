from __future__ import annotations

"""Read-only Scenario × Weapon evidence accumulator."""

import argparse
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "candidate",
    "scenario_id",
    "primary_scenario",
    "fingerprint",
    "oos_windows",
    "positive_oos_windows",
    "negative_oos_windows",
    "positive_oos_pct",
    "mean_oos_spread",
    "median_oos_spread",
    "worst_oos_spread",
    "best_oos_spread",
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
]


def validate_input(frame: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))

    if missing:
        raise ValueError(
            "Evidence accumulation input is missing required columns: "
            + ", ".join(missing)
        )


def classify_evidence(
    oos_windows: int,
    positive_oos_pct: float,
) -> str:
    """
    Conservative evidence classification.

    N = number of genuine chronological OOS windows.

    N < 5:
        INSUFFICIENT

    N 5-9:
        EARLY

    N >= 10:
        ELIGIBLE

    N >= 20 and positive OOS rate >= 60%:
        VALIDATION_READY

    Persistent positive OOS performance is deliberately NOT
    labelled PROMISING here. That requires a separate stability
    assessment later.
    """

    if oos_windows < 5:
        return "INSUFFICIENT"

    if oos_windows < 10:
        return "EARLY"

    if oos_windows < 20:
        return "ELIGIBLE"

    if positive_oos_pct >= 60.0:
        return "VALIDATION_READY"

    return "ELIGIBLE"


def build_accumulation(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Build the accumulated evidence table.

    Input is never mutated.

    The input is expected to contain already-computed chronological
    OOS summaries. This module does not recompute trades or create
    future information.

    No database writes occur.
    No candidate promotion occurs.
    """

    validate_input(frame)

    work = frame.copy(deep=True)

    numeric_columns = [
        "oos_windows",
        "positive_oos_windows",
        "negative_oos_windows",
        "positive_oos_pct",
        "mean_oos_spread",
        "median_oos_spread",
        "worst_oos_spread",
        "best_oos_spread",
    ]

    for column in numeric_columns:
        work[column] = pd.to_numeric(
            work[column],
            errors="coerce",
        )

    work["evidence_status"] = [
        classify_evidence(
            int(windows) if pd.notna(windows) else 0,
            float(positive_pct)
            if pd.notna(positive_pct)
            else 0.0,
        )
        for windows, positive_pct in zip(
            work["oos_windows"],
            work["positive_oos_pct"],
        )
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

    result = build_accumulation(frame)

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
        description=(
            "Build read-only Scenario × Weapon "
            "evidence accumulation."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path(
            "research/artifacts/"
            "scenario_weapon_matrix.csv"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "research/artifacts/"
            "scenario_weapon_evidence_accumulation.csv"
        ),
    )

    args = parser.parse_args()

    result = run(
        args.input,
        args.output,
    )

    print()
    print("MARKETBOT - SCENARIO × WEAPON EVIDENCE ACCUMULATION")
    print("=" * 72)

    if result.empty:
        print("No OOS evidence available.")
        return

    display_columns = [
        "scenario_id",
        "primary_scenario",
        "candidate",
        "oos_windows",
        "positive_oos_pct",
        "mean_oos_spread",
        "evidence_status",
    ]

    print(
        result[display_columns]
        .round(4)
        .to_string(index=False)
    )

    print()
    print("Evidence classification:")
    print("N < 5       : INSUFFICIENT")
    print("N 5-9       : EARLY")
    print("N >= 10     : ELIGIBLE")
    print("N >= 20 + >=60% positive OOS : VALIDATION_READY")

    print()
    print("Saved:")
    print(args.output)

    print()
    print(
        "READ-ONLY: no SQLite writes, candidate promotion, "
        "production scoring changes, factor-weight changes, "
        "Track B/C changes, or live trading."
    )


if __name__ == "__main__":
    main()
