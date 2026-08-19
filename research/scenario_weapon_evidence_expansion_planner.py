"""
MarketBot - Scenario × Weapon Evidence Expansion Planner

Consumes the stable unified research report and identifies where
additional genuine chronological OOS evidence is most valuable.

READ-ONLY:
- No SQLite writes
- No candidate modification
- No factor-weight changes
- No Track B/C changes
- No promotion
- No live-trading changes
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_INPUT = (
    Path(__file__).resolve().parent
    / "artifacts"
    / "scenario_weapon_unified_report.csv"
)

DEFAULT_OUTPUT = (
    Path(__file__).resolve().parent
    / "artifacts"
    / "scenario_weapon_evidence_expansion_plan.csv"
)

REQUIRED_COLUMNS = {
    "scenario_id",
    "primary_scenario",
    "fingerprint",
    "candidate",
    "oos_windows",
    "positive_oos_pct",
    "mean_oos_spread",
    "evidence_status",
    "research_decision",
}


def validate_input(frame: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(
            "Evidence expansion input is missing required columns: "
            + ", ".join(missing)
        )


def classify_priority(row: pd.Series) -> str:
    n = int(row["oos_windows"])

    decision = str(row["research_decision"])
    evidence = str(row["evidence_status"])

    if decision == "VALIDATION_CANDIDATE":
        return "VALIDATION_REVIEW"

    if n < 5:
        return "HIGH"

    if n < 10:
        return "HIGH"

    if n < 20:
        return "MEDIUM"

    if evidence in {"VALIDATION_READY", "PROMISING"}:
        return "VALIDATION_REVIEW"

    return "LOW"


def classify_action(row: pd.Series) -> str:
    n = int(row["oos_windows"])

    if row["research_decision"] == "VALIDATION_CANDIDATE":
        return "VALIDATE_CANDIDATE"

    if n < 5:
        return "ACCUMULATE_OOS"

    if n < 10:
        return "ACCUMULATE_TO_ELIGIBLE"

    if n < 20:
        return "ACCUMULATE_TO_VALIDATION"

    return "REVIEW_EVIDENCE"


def build_plan(frame: pd.DataFrame) -> pd.DataFrame:
    validate_input(frame)

    work = frame.copy()

    numeric_columns = [
        "oos_windows",
        "positive_oos_pct",
        "mean_oos_spread",
    ]

    for column in numeric_columns:
        work[column] = pd.to_numeric(work[column], errors="coerce")

    work["oos_windows"] = work["oos_windows"].fillna(0).astype(int)

    work["windows_to_10"] = (
        10 - work["oos_windows"]
    ).clip(lower=0)

    work["windows_to_20"] = (
        20 - work["oos_windows"]
    ).clip(lower=0)

    work["priority"] = work.apply(classify_priority, axis=1)
    work["recommended_action"] = work.apply(classify_action, axis=1)

    priority_order = {
        "HIGH": 0,
        "MEDIUM": 1,
        "LOW": 2,
        "VALIDATION_REVIEW": 3,
    }

    work["_priority_order"] = work["priority"].map(priority_order)

    columns = [
        "scenario_id",
        "primary_scenario",
        "fingerprint",
        "candidate",
        "oos_windows",
        "windows_to_10",
        "windows_to_20",
        "positive_oos_pct",
        "mean_oos_spread",
        "evidence_status",
        "research_decision",
        "priority",
        "recommended_action",
    ]

    return (
        work[columns + ["_priority_order"]]
        .sort_values(
            [
                "_priority_order",
                "windows_to_10",
                "windows_to_20",
                "positive_oos_pct",
                "mean_oos_spread",
                "scenario_id",
                "candidate",
            ],
            ascending=[
                True,
                True,
                True,
                False,
                False,
                True,
                True,
            ],
            kind="mergesort",
        )
        .drop(columns="_priority_order")
        .reset_index(drop=True)
    )


def run(
    input_path: str | Path = DEFAULT_INPUT,
    output_path: str | Path = DEFAULT_OUTPUT,
) -> pd.DataFrame:
    input_path = Path(input_path)
    output_path = Path(output_path)

    frame = pd.read_csv(input_path)
    result = build_plan(frame)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)

    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    result = run(args.input, args.output)

    print("# MARKETBOT - EVIDENCE EXPANSION PLANNER")
    print()
    print(
        result[
            [
                "scenario_id",
                "primary_scenario",
                "candidate",
                "oos_windows",
                "windows_to_10",
                "windows_to_20",
                "positive_oos_pct",
                "mean_oos_spread",
                "evidence_status",
                "priority",
                "recommended_action",
            ]
        ].to_string(index=False)
    )

    print()
    print("PRIORITY COUNTS")
    print(result["priority"].value_counts().sort_index().to_string())

    print()
    print("Saved:")
    print(Path(args.output).resolve())

    print()
    print(
        "READ-ONLY: no SQLite writes, candidate changes, production scoring "
        "changes, factor-weight changes, Track B/C changes, promotion, "
        "or live trading."
    )


if __name__ == "__main__":
    main()
