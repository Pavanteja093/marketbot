from __future__ import annotations

"""Read-only Scenario × Weapon research matrix."""

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
    "rank_within_scenario",
]


def validate_input(frame: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))

    if missing:
        raise ValueError(
            "Scenario weapon matrix is missing required columns: "
            + ", ".join(missing)
        )


def _status_priority(status: str) -> int:
    """
    Lower number = stronger evidence.

    This is only a research ordering.
    It does not promote or approve a candidate.
    """
    priorities = {
        "VALIDATION_READY": 0,
        "ELIGIBLE": 1,
        "EARLY": 2,
        "INSUFFICIENT": 3,
    }

    return priorities.get(str(status), 99)


def build_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Build a deterministic Scenario × Weapon comparison matrix.

    Input is never mutated.
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

    work["_status_priority"] = work["evidence_status"].map(
        _status_priority
    )

    # Stronger evidence first.
    # Within equal evidence status:
    #   1. more positive OOS %
    #   2. higher mean OOS spread
    #   3. higher median OOS spread
    #   4. deterministic candidate name
    work = work.sort_values(
        [
            "scenario_id",
            "fingerprint",
            "_status_priority",
            "positive_oos_pct",
            "mean_oos_spread",
            "median_oos_spread",
            "candidate",
        ],
        ascending=[
            True,
            True,
            True,
            False,
            False,
            False,
            True,
        ],
        kind="mergesort",
    ).reset_index(drop=True)

    # Rank only within the exact scenario fingerprint.
    work["rank_within_scenario"] = (
        work.groupby(
            ["scenario_id", "fingerprint"],
            sort=False,
            dropna=False,
        ).cumcount()
        + 1
    )

    return work[OUTPUT_COLUMNS].reset_index(drop=True)


def run(
    input_path: Path,
    output_path: Path,
) -> pd.DataFrame:

    evidence = pd.read_csv(input_path)

    result = build_matrix(evidence)

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
        description="Build read-only Scenario × Weapon research matrix."
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
            "scenario_weapon_matrix.csv"
        ),
    )

    args = parser.parse_args()

    result = run(
        args.input,
        args.output,
    )

    print()
    print("MARKETBOT - SCENARIO × WEAPON MATRIX")
    print("=" * 72)

    if result.empty:
        print("No accumulated evidence available.")
        return

    display_columns = [
        "scenario_id",
        "primary_scenario",
        "candidate",
        "oos_windows",
        "positive_oos_pct",
        "mean_oos_spread",
        "evidence_status",
        "rank_within_scenario",
    ]

    print(
        result[display_columns]
        .round(4)
        .to_string(index=False)
    )

    print()
    print("Saved:")
    print(args.output)

    print()
    print(
        "READ-ONLY: no SQLite writes, production scoring changes, "
        "factor-weight changes, Track B/C promotion, or live trading changes."
    )


if __name__ == "__main__":
    main()