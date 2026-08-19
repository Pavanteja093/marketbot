from __future__ import annotations

"""
MarketBot - Scenario × Weapon Walk-Forward OOS

Research-only chronological validation.

This module:
    - consumes the existing date-level scenario × weapon evidence ledger
    - never shuffles observations
    - never uses future observations for an earlier OOS test
    - performs repeated chronological OOS evaluations
    - writes CSV research artifacts only
    - never writes to SQLite
    - never changes production scoring
    - never changes Track B or Track C
    - never promotes a weapon

The purpose is simple:

    historical evidence
        ↓
    chronological train
        ↓
    next unseen observation/window
        ↓
    record OOS result
        ↓
    expand training history
        ↓
    repeat

This produces repeated out-of-sample evidence instead of relying on
one final holdout.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_INPUT = (
    BASE_DIR
    / "research"
    / "artifacts"
    / "scenario_weapon_evidence.csv"
)

DEFAULT_OUTPUT = (
    BASE_DIR
    / "research"
    / "artifacts"
    / "scenario_weapon_walk_forward.csv"
)

DEFAULT_LEDGER_OUTPUT = (
    BASE_DIR
    / "research"
    / "artifacts"
    / "scenario_weapon_walk_forward_ledger.csv"
)

DEFAULT_SUMMARY_OUTPUT = (
    BASE_DIR
    / "research"
    / "artifacts"
    / "scenario_weapon_walk_forward_summary.csv"
)

MIN_TOTAL_OBSERVATIONS = 10
MIN_TRAIN_OBSERVATIONS = 5
MIN_OOS_OBSERVATIONS = 1
MAX_WALK_FORWARD_WINDOWS = 5

REQUIRED_COLUMNS = {
    "trade_date",
    "candidate",
    "scenario_id",
    "primary_scenario",
    "spread",
}


def validate_input(frame: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(frame.columns)

    if missing:
        raise ValueError(
            "Walk-forward evidence is missing required columns: "
            + ", ".join(sorted(missing))
        )


def _metrics(values: pd.Series) -> dict:
    series = pd.to_numeric(values, errors="coerce").dropna()

    if series.empty:
        return {
            "observations": 0,
            "average_spread": None,
            "median_spread": None,
            "positive_day_pct": None,
            "worst_day": None,
            "best_day": None,
        }

    return {
        "observations": int(len(series)),
        "average_spread": float(series.mean()),
        "median_spread": float(series.median()),
        "positive_day_pct": float((series > 0).mean() * 100),
        "worst_day": float(series.min()),
        "best_day": float(series.max()),
    }


def _prepare_group(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy(deep=True)

    work["trade_date"] = pd.to_datetime(
        work["trade_date"],
        errors="coerce",
    )

    work["spread"] = pd.to_numeric(
        work["spread"],
        errors="coerce",
    )

    work = (
        work
        .dropna(subset=["trade_date", "spread"])
        .sort_values("trade_date", kind="stable")
        .drop_duplicates("trade_date", keep="last")
        .reset_index(drop=True)
    )

    return work


def _window_starts(
    n: int,
    max_windows: int = MAX_WALK_FORWARD_WINDOWS,
) -> list[int]:
    """
    Return chronological OOS positions.

    Example with n=10:

        train: 0..4
        OOS:   5

        train: 0..5
        OOS:   6

        ...

    The OOS observations therefore always occur strictly after
    the observations used for training.
    """

    if n < MIN_TOTAL_OBSERVATIONS:
        return []

    first_oos = MIN_TRAIN_OBSERVATIONS

    possible = list(range(first_oos, n))

    if not possible:
        return []

    return possible[:max_windows]


def evaluate_group(
    frame: pd.DataFrame,
    max_windows: int = MAX_WALK_FORWARD_WINDOWS,
) -> tuple[list[dict], list[dict]]:
    """
    Evaluate one scenario × weapon sequence chronologically.

    Each OOS observation is tested only after it becomes unseen
    relative to the preceding training history.
    """

    work = _prepare_group(frame)

    if len(work) < MIN_TOTAL_OBSERVATIONS:
        return [], []

    starts = _window_starts(
        len(work),
        max_windows=max_windows,
    )

    results = []
    ledger = []

    for window_number, oos_position in enumerate(starts, start=1):
        train = work.iloc[:oos_position].copy()
        oos = work.iloc[oos_position:oos_position + MIN_OOS_OBSERVATIONS].copy()

        if len(train) < MIN_TRAIN_OBSERVATIONS or oos.empty:
            continue

        train_metrics = _metrics(train["spread"])
        oos_metrics = _metrics(oos["spread"])

        oos_average = oos_metrics["average_spread"]

        if oos_average is None:
            oos_result = "NOT_READY"
        elif oos_average > 0:
            oos_result = "POSITIVE_OOS"
        else:
            oos_result = "NEGATIVE_OOS"

        results.append(
            {
                "candidate": str(work["candidate"].iloc[0]),
                "scenario_id": str(work["scenario_id"].iloc[0]),
                "primary_scenario": str(
                    work["primary_scenario"].iloc[0]
                ),
                "window_number": window_number,
                "train_observations": int(len(train)),
                "oos_observations": int(len(oos)),
                "train_start": train["trade_date"].min(),
                "train_end": train["trade_date"].max(),
                "oos_start": oos["trade_date"].min(),
                "oos_end": oos["trade_date"].max(),
                "train_average_spread": train_metrics[
                    "average_spread"
                ],
                "train_median_spread": train_metrics[
                    "median_spread"
                ],
                "train_positive_day_pct": train_metrics[
                    "positive_day_pct"
                ],
                "oos_average_spread": oos_metrics[
                    "average_spread"
                ],
                "oos_median_spread": oos_metrics[
                    "median_spread"
                ],
                "oos_positive_day_pct": oos_metrics[
                    "positive_day_pct"
                ],
                "oos_worst_day": oos_metrics["worst_day"],
                "oos_best_day": oos_metrics["best_day"],
                "oos_result": oos_result,
            }
        )

        for _, row in oos.iterrows():
            ledger.append(
                {
                    "trade_date": row["trade_date"],
                    "candidate": row["candidate"],
                    "scenario_id": row["scenario_id"],
                    "primary_scenario": row[
                        "primary_scenario"
                    ],
                    "fingerprint": row.get(
                        "fingerprint",
                        None,
                    ),
                    "window_number": window_number,
                    "spread": float(row["spread"]),
                    "oos_result": oos_result,
                }
            )

    return results, ledger


def build_walk_forward(
    evidence: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build repeated chronological OOS results for every
    scenario × weapon sequence.
    """

    validate_input(evidence)

    rows = []
    ledger_rows = []

    groups = evidence.groupby(
        ["scenario_id", "candidate"],
        sort=True,
    )

    for _, group in groups:
        results, ledger = evaluate_group(group)

        rows.extend(results)
        ledger_rows.extend(ledger)

    report = pd.DataFrame(rows)
    ledger = pd.DataFrame(ledger_rows)

    if not report.empty:
        report = report.sort_values(
            [
                "primary_scenario",
                "scenario_id",
                "candidate",
                "window_number",
            ],
            kind="stable",
        ).reset_index(drop=True)

    if not ledger.empty:
        ledger = ledger.sort_values(
            [
                "trade_date",
                "candidate",
                "scenario_id",
                "window_number",
            ],
            kind="stable",
        ).reset_index(drop=True)

    return report, ledger


def build_summary(
    report: pd.DataFrame,
) -> pd.DataFrame:
    """
    Summarize repeated OOS evidence by scenario × weapon.
    """

    columns = [
        "candidate",
        "scenario_id",
        "primary_scenario",
        "oos_windows",
        "positive_oos_windows",
        "negative_oos_windows",
        "positive_oos_pct",
        "mean_oos_spread",
        "median_oos_spread",
        "worst_oos_spread",
        "best_oos_spread",
        "research_status",
    ]

    if report.empty:
        return pd.DataFrame(columns=columns)

    rows = []

    for (
        candidate,
        scenario_id,
        primary_scenario,
    ), group in report.groupby(
        [
            "candidate",
            "scenario_id",
            "primary_scenario",
        ],
        sort=True,
    ):
        spreads = pd.to_numeric(
            group["oos_average_spread"],
            errors="coerce",
        ).dropna()

        positive = int((spreads > 0).sum())
        negative = int((spreads <= 0).sum())
        windows = int(len(spreads))

        if windows == 0:
            status = "OOS_NOT_READY"
        elif windows >= 3 and positive / windows >= 0.60:
            status = "PERSISTENTLY_POSITIVE_OOS"
        else:
            status = "OOS_EVIDENCE_ACCUMULATING"

        rows.append(
            {
                "candidate": candidate,
                "scenario_id": scenario_id,
                "primary_scenario": primary_scenario,
                "oos_windows": windows,
                "positive_oos_windows": positive,
                "negative_oos_windows": negative,
                "positive_oos_pct": (
                    float(positive / windows * 100)
                    if windows
                    else None
                ),
                "mean_oos_spread": (
                    float(spreads.mean())
                    if windows
                    else None
                ),
                "median_oos_spread": (
                    float(spreads.median())
                    if windows
                    else None
                ),
                "worst_oos_spread": (
                    float(spreads.min())
                    if windows
                    else None
                ),
                "best_oos_spread": (
                    float(spreads.max())
                    if windows
                    else None
                ),
                "research_status": status,
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values(
            [
                "primary_scenario",
                "scenario_id",
                "candidate",
            ],
            kind="stable",
        )
        .reset_index(drop=True)
    )


def run(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    ledger_path: Path = DEFAULT_LEDGER_OUTPUT,
    summary_path: Path = DEFAULT_SUMMARY_OUTPUT,
) -> dict:
    """
    Execute the read-only walk-forward research pipeline.
    """

    evidence = pd.read_csv(input_path)

    report, ledger = build_walk_forward(evidence)

    summary = build_summary(report)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report.to_csv(
        output_path,
        index=False,
    )

    ledger.to_csv(
        ledger_path,
        index=False,
    )

    summary.to_csv(
        summary_path,
        index=False,
    )

    return {
        "evidence": evidence,
        "report": report,
        "ledger": ledger,
        "summary": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "MarketBot scenario × weapon "
            "chronological walk-forward OOS validation."
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

    parser.add_argument(
        "--ledger",
        type=Path,
        default=DEFAULT_LEDGER_OUTPUT,
    )

    parser.add_argument(
        "--summary",
        type=Path,
        default=DEFAULT_SUMMARY_OUTPUT,
    )

    args = parser.parse_args()

    result = run(
        input_path=args.input,
        output_path=args.output,
        ledger_path=args.ledger,
        summary_path=args.summary,
    )

    report = result["report"]
    summary = result["summary"]

    print()
    print("=" * 100)
    print(
        "MARKETBOT - SCENARIO × WEAPON "
        "CHRONOLOGICAL WALK-FORWARD OOS"
    )
    print("=" * 100)

    print()
    print(
        f"Input observations       : "
        f"{len(result['evidence']):,}"
    )

    print(
        f"Walk-forward OOS windows : "
        f"{len(report):,}"
    )

    print(
        f"Scenario × weapon groups : "
        f"{len(summary):,}"
    )

    print()

    if summary.empty:
        print("No scenario × weapon groups have enough history.")
    else:
        print("WALK-FORWARD SUMMARY")
        print()

        display = [
            "candidate",
            "scenario_id",
            "primary_scenario",
            "oos_windows",
            "positive_oos_windows",
            "negative_oos_windows",
            "positive_oos_pct",
            "mean_oos_spread",
            "research_status",
        ]

        print(
            summary[display]
            .round(4)
            .to_string(index=False)
        )

    print()
    print("Saved:")
    print(f"  {args.output}")
    print(f"  {args.ledger}")
    print(f"  {args.summary}")

    print()
    print(
        "READ-ONLY: no SQLite writes, candidate changes, "
        "production scoring changes, factor-weight changes, "
        "or weapon promotion occurred."
    )


if __name__ == "__main__":
    main()
