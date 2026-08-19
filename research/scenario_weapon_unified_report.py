from __future__ import annotations

"""
MarketBot - Unified Scenario × Weapon Research Report

Consumes the stable research-decision-gate artifact and produces
a read-only consolidated research report.

This module:
- does NOT modify previous research modules
- does NOT write to SQLite
- does NOT modify Track B or Track C
- does NOT modify production scoring
- does NOT promote candidates
- does NOT generate trading signals

Input:
    research/artifacts/scenario_weapon_decision_gate.csv

Outputs:
    research/artifacts/scenario_weapon_unified_report.csv

The report is intentionally descriptive rather than predictive.
"""

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_INPUT = (
    Path(__file__).resolve().parent
    / "artifacts"
    / "scenario_weapon_decision_gate.csv"
)

DEFAULT_OUTPUT = (
    Path(__file__).resolve().parent
    / "artifacts"
    / "scenario_weapon_unified_report.csv"
)

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
    "research_decision",
    "decision_reason",
}


DECISION_PRIORITY = {
    "VALIDATION_CANDIDATE": 1,
    "RESEARCH_REVIEW": 2,
    "CONTINUE_OOS": 3,
    "COLLECT_MORE_EVIDENCE": 4,
}


EVIDENCE_PRIORITY = {
    "VALIDATION_READY": 1,
    "ELIGIBLE": 2,
    "EARLY": 3,
    "INSUFFICIENT": 4,
}


def validate_input(frame: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))

    if missing:
        raise ValueError(
            "Unified research report input is missing required columns: "
            + ", ".join(missing)
        )


def _numeric(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    work = frame.copy()

    for column in columns:
        work[column] = pd.to_numeric(
            work[column],
            errors="coerce",
        )

    return work


def _rank_candidates(work: pd.DataFrame) -> pd.DataFrame:
    """
    Rank candidates independently inside each scenario/fingerprint.

    Ranking preference:
    1. research decision priority
    2. evidence strength
    3. positive OOS percentage
    4. mean OOS spread
    5. candidate name for deterministic ordering
    """

    work = work.copy()

    work["_decision_rank"] = work["research_decision"].map(
        DECISION_PRIORITY
    ).fillna(99)

    work["_evidence_rank"] = work["evidence_status"].map(
        EVIDENCE_PRIORITY
    ).fillna(99)

    work = work.sort_values(
        [
            "scenario_id",
            "fingerprint",
            "_decision_rank",
            "_evidence_rank",
            "positive_oos_pct",
            "mean_oos_spread",
            "candidate",
        ],
        ascending=[
            True,
            True,
            True,
            True,
            False,
            False,
            True,
        ],
        kind="mergesort",
    )

    work["rank_within_scenario"] = (
        work.groupby(
            ["scenario_id", "fingerprint"],
            dropna=False,
        ).cumcount()
        + 1
    )

    return work.drop(
        columns=["_decision_rank", "_evidence_rank"]
    )


def build_report(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Build the unified research report from Decision Gate output.

    The returned dataframe is deterministic and does not mutate input.
    """

    validate_input(frame)

    work = frame.copy()

    work = _numeric(
        work,
        [
            "oos_windows",
            "positive_oos_windows",
            "negative_oos_windows",
            "positive_oos_pct",
            "mean_oos_spread",
            "median_oos_spread",
            "worst_oos_spread",
            "best_oos_spread",
        ],
    )

    work = _rank_candidates(work)

    work["scenario_weapon_status"] = work["research_decision"].map(
        {
            "VALIDATION_CANDIDATE": "CANDIDATE",
            "RESEARCH_REVIEW": "REVIEW",
            "CONTINUE_OOS": "WATCH",
            "COLLECT_MORE_EVIDENCE": "INSUFFICIENT",
        }
    ).fillna("UNKNOWN")

    work["research_conclusion"] = work.apply(
        _build_conclusion,
        axis=1,
    )

    columns = [
        "scenario_id",
        "primary_scenario",
        "fingerprint",
        "candidate",
        "rank_within_scenario",
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
        "scenario_weapon_status",
        "decision_reason",
        "research_conclusion",
    ]

    return work[columns].reset_index(drop=True)


def _build_conclusion(row: pd.Series) -> str:
    decision = row["research_decision"]
    evidence = row["evidence_status"]

    if decision == "VALIDATION_CANDIDATE":
        return (
            "Research-quality candidate; proceed to deeper validation "
            "before any production consideration."
        )

    if decision == "RESEARCH_REVIEW":
        return (
            "Relationship deserves deeper research review; "
            "do not promote yet."
        )

    if decision == "CONTINUE_OOS":
        return (
            "Interesting relationship, but genuine OOS evidence "
            "is still accumulating."
        )

    if decision == "COLLECT_MORE_EVIDENCE":
        return (
            "Insufficient evidence to judge this scenario-weapon "
            "relationship."
        )

    return f"Unclassified research state: {evidence}"


def run(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
) -> pd.DataFrame:
    input_path = Path(input_path)
    output_path = Path(output_path)

    frame = pd.read_csv(input_path)

    report = build_report(frame)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(output_path, index=False)

    return report


def print_report(report: pd.DataFrame) -> None:
    print()
    print("=" * 100)
    print("MARKETBOT - UNIFIED SCENARIO × WEAPON RESEARCH REPORT")
    print("=" * 100)
    print()

    print(
        "Scenario × weapon relationships : "
        f"{len(report)}"
    )

    print(
        "Distinct scenarios               : "
        f"{report['scenario_id'].nunique()}"
    )

    print(
        "Distinct weapons                 : "
        f"{report['candidate'].nunique()}"
    )

    print()

    display_columns = [
        "scenario_id",
        "primary_scenario",
        "candidate",
        "rank_within_scenario",
        "oos_windows",
        "positive_oos_pct",
        "mean_oos_spread",
        "evidence_status",
        "research_decision",
    ]

    print(
        report[display_columns].to_string(index=False)
    )

    print()
    print("RESEARCH DECISION COUNTS")
    print(
        report["research_decision"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print()
    print("SCENARIO SUMMARY")

    for scenario_id, group in report.groupby(
        ["scenario_id", "primary_scenario"],
        sort=True,
    ):
        scenario_id_value, primary_scenario = scenario_id

        best = group.iloc[0]

        print(
            f"{scenario_id_value:<16} "
            f"{primary_scenario:<12} "
            f"BEST={best['candidate']:<32} "
            f"RANK=1 "
            f"OOS={int(best['oos_windows']) if pd.notna(best['oos_windows']) else 0} "
            f"POS={best['positive_oos_pct']:.1f}% "
            f"MEAN={best['mean_oos_spread']:.4f} "
            f"DECISION={best['research_decision']}"
        )

    print()
    print(
        "READ-ONLY: no SQLite writes, candidate promotion, "
        "production scoring changes, factor-weight changes, "
        "Track B/C changes, or live trading."
    )


def main() -> None:
    parser = argparse.ArgumentParser()

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

    report = run(
        input_path=args.input,
        output_path=args.output,
    )

    print_report(report)

    print()
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
