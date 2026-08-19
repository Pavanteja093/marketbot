"""Read-only qualification of Scenario x Factor conditional evidence.

This module consumes only research/artifacts/scenario_factor_conditional_evidence.csv
and writes research/artifacts/scenario_factor_reliability.csv.

Evidence-strength thresholds are deterministic and intentionally conservative:

INSUFFICIENT
    observations < 30, OR scenario_dates < 5, OR symbols < 5.

EARLY
    Meets the minimum breadth above but does not meet PROMISING requirements.

PROMISING
    observations >= 100, scenario_dates >= 10, symbols >= 10, and the evidence
    has non-negative median/mean agreement (both >= 0) OR positive_5d_pct is
    materially directional (<= 45% or >= 55%).

ROBUST
    observations >= 300, scenario_dates >= 20, symbols >= 20, and the same
    consistency condition as PROMISING.

The status describes evidence strength only. It does not mean predictive validity,
calibration, production readiness, or trading suitability.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Final

import pandas as pd

BASE_DIR: Final = Path(__file__).resolve().parents[1]
INPUT_ARTIFACT: Final = BASE_DIR / "research" / "artifacts" / "scenario_factor_conditional_evidence.csv"
OUTPUT_ARTIFACT: Final = BASE_DIR / "research" / "artifacts" / "scenario_factor_reliability.csv"

REQUIRED_COLUMNS: Final = [
    "primary_scenario", "factor", "factor_state", "observations", "scenario_dates",
    "symbols", "positive_5d_pct", "mean_return_5d", "median_return_5d",
    "worst_return_5d", "best_return_5d",
]
OUTPUT_COLUMNS: Final = REQUIRED_COLUMNS + ["reliability_status", "reliability_score", "reliability_reason"]

MIN_OBSERVATIONS: Final = 30
MIN_DATES: Final = 5
MIN_SYMBOLS: Final = 5
PROMISING_OBSERVATIONS: Final = 100
PROMISING_DATES: Final = 10
PROMISING_SYMBOLS: Final = 10
ROBUST_OBSERVATIONS: Final = 300
ROBUST_DATES: Final = 20
ROBUST_SYMBOLS: Final = 20


def _numeric(work: pd.DataFrame) -> pd.DataFrame:
    out = work.copy(deep=True)
    for col in REQUIRED_COLUMNS[3:]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    if out[REQUIRED_COLUMNS[3:]].isna().any().any():
        bad = [c for c in REQUIRED_COLUMNS[3:] if out[c].isna().any()]
        raise ValueError("Evidence artifact contains missing/non-numeric values: " + ", ".join(bad))
    return out


def _consistency(row: pd.Series) -> bool:
    pct = float(row["positive_5d_pct"])
    mean = float(row["mean_return_5d"])
    median = float(row["median_return_5d"])
    return (mean >= 0 and median >= 0) or pct <= 45 or pct >= 55


def _score(row: pd.Series) -> float:
    obs = float(row["observations"])
    dates = float(row["scenario_dates"])
    symbols = float(row["symbols"])
    pct = float(row["positive_5d_pct"])

    sample_score = min(obs / ROBUST_OBSERVATIONS, 1.0) * 50.0
    date_score = min(dates / ROBUST_DATES, 1.0) * 25.0
    symbol_score = min(symbols / ROBUST_SYMBOLS, 1.0) * 15.0
    directional_score = min(abs(pct - 50.0) / 50.0, 1.0) * 10.0
    return round(sample_score + date_score + symbol_score + directional_score, 2)


def classify_relationship(row: pd.Series) -> tuple[str, float, str]:
    obs = int(row["observations"])
    dates = int(row["scenario_dates"])
    symbols = int(row["symbols"])
    pct = float(row["positive_5d_pct"])
    mean = float(row["mean_return_5d"])
    median = float(row["median_return_5d"])
    consistent = _consistency(row)
    score = _score(row)

    if obs < MIN_OBSERVATIONS or dates < MIN_DATES or symbols < MIN_SYMBOLS:
        return (
            "INSUFFICIENT", score,
            f"Too little breadth: requires >= {MIN_OBSERVATIONS} observations, "
            f">= {MIN_DATES} scenario_dates, and >= {MIN_SYMBOLS} symbols; "
            f"observed {obs}/{dates}/{symbols}.",
        )

    if obs >= ROBUST_OBSERVATIONS and dates >= ROBUST_DATES and symbols >= ROBUST_SYMBOLS and consistent:
        return (
            "ROBUST", score,
            f"Strong sample and breadth ({obs} observations, {dates} dates, {symbols} symbols) "
            f"with consistent evidence (positive_5d_pct={pct:.2f}%, mean={mean:.4f}, median={median:.4f}). "
            "Evidence strength only; not predictive validation.",
        )

    if obs >= PROMISING_OBSERVATIONS and dates >= PROMISING_DATES and symbols >= PROMISING_SYMBOLS and consistent:
        return (
            "PROMISING", score,
            f"Adequate sample and breadth ({obs} observations, {dates} dates, {symbols} symbols) "
            f"with directional/central-tendency consistency (positive_5d_pct={pct:.2f}%, "
            f"mean={mean:.4f}, median={median:.4f}). Evidence strength only; not predictive validation.",
        )

    return (
        "EARLY", score,
        f"Minimum breadth is met ({obs} observations, {dates} dates, {symbols} symbols), "
        "but evidence has not reached the deterministic PROMISING/ROBUST thresholds.",
    )


def assess_evidence(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("Scenario × factor evidence artifact is missing required columns: " + ", ".join(missing))

    work = _numeric(df[REQUIRED_COLUMNS])
    rows = []
    for _, row in work.iterrows():
        status, score, reason = classify_relationship(row)
        item = row.to_dict()
        item.update({"reliability_status": status, "reliability_score": score, "reliability_reason": reason})
        rows.append(item)
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def run(input_path: Path = INPUT_ARTIFACT, output_path: Path = OUTPUT_ARTIFACT) -> pd.DataFrame:
    source = pd.read_csv(input_path)
    result = assess_evidence(source)
    result = result.sort_values(
        ["reliability_score", "observations", "primary_scenario", "factor", "factor_state"],
        ascending=[False, False, True, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only Scenario × Factor evidence reliability assessment.")
    parser.add_argument("--input", type=Path, default=INPUT_ARTIFACT)
    parser.add_argument("--output", type=Path, default=OUTPUT_ARTIFACT)
    args = parser.parse_args()

    result = run(args.input, args.output)
    counts = result["reliability_status"].value_counts().reindex(
        ["INSUFFICIENT", "EARLY", "PROMISING", "ROBUST"], fill_value=0
    )

    print("\nMARKETBOT - SCENARIO × FACTOR EVIDENCE RELIABILITY")
    print("=" * 72)
    print(f"Relationships assessed : {len(result)}")
    print(f"INSUFFICIENT : {counts['INSUFFICIENT']}")
    print(f"EARLY        : {counts['EARLY']}")
    print(f"PROMISING    : {counts['PROMISING']}")
    print(f"ROBUST       : {counts['ROBUST']}")
    print("\nTop relationships:")
    cols = ["primary_scenario", "factor", "factor_state", "observations", "reliability_status", "reliability_score"]
    print(result[cols].head(10).to_string(index=False))
    print(f"\nSaved: {args.output}")
    print("\nREAD-ONLY:")
    print("No SQLite writes, production changes, factor-weight changes, candidate promotion, or trading changes.")


if __name__ == "__main__":
    main()
