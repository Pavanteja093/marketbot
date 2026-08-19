from __future__ import annotations

"""
MarketBot - Read-Only Research Candidate Gate Runner

Purpose
-------
Run the existing research candidates through the common candidate gate and
produce one unified research-decision table.

This module is READ-ONLY.

It does NOT:
- modify SQLite
- modify production scoring
- modify factor weights
- modify challenger logic
- modify live trading
- promote research candidates

Candidate adapters:
1. baseline_failure_decomposition
2. conditional_score_candidate
3. factor_agreement_candidate
4. regime_aware_c21
5. regime_aware_c22
6. factor_interaction_walk_forward

The runner intentionally treats candidate output as evidence. It does not
recalculate the research methodology of the underlying candidates.
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from research.candidate_gate import evaluate


BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = BASE_DIR / "research" / "artifacts"
DEFAULT_OUTPUT = ARTIFACT_DIR / "unified_candidate_gate.csv"


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    module: str
    metric: str


CANDIDATES = (
    CandidateSpec(
        "Baseline Failure Decomposition",
        "research.baseline_failure_decomposition",
        "spread",
    ),
    CandidateSpec(
        "Conditional Score",
        "research.conditional_score_candidate",
        "spread",
    ),
    CandidateSpec(
        "Factor Agreement",
        "research.factor_agreement_candidate",
        "spread",
    ),
    CandidateSpec(
        "C2.1 Regime-Aware",
        "research.regime_aware_walk_forward",
        "spread",
    ),
    CandidateSpec(
        "C2.2 Regime-Aware",
        "research.regime_aware_walk_forward",
        "spread",
    ),
    CandidateSpec(
        "C3.3 Factor Interaction",
        "research.factor_interaction_walk_forward",
        "incremental_spread",
    ),
)


def _number(value):
    if value is None:
        return None

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    return value if pd.notna(value) else None


def _parse_float(pattern: str, text: str):
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    if not match:
        return None

    return _number(match.group(1))


def _parse_int(pattern: str, text: str):
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    if not match:
        return None

    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def _run_module(module: str) -> str:
    """
    Execute an existing research module without importing it into this
    process. This isolates the runner from candidate-side global state.
    """
    proc = subprocess.run(
        [sys.executable, "-m", module],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    output = proc.stdout

    if proc.stderr:
        output += "\n" + proc.stderr

    if proc.returncode != 0:
        raise RuntimeError(
            f"{module} exited with code {proc.returncode}\n\n{output}"
        )

    return output


def _gate_from_spreads(
    spreads,
    source_decision=None,
    evidence_unit="windows",
):
    series = pd.to_numeric(pd.Series(spreads), errors="coerce").dropna()

    frame = pd.DataFrame({"spread": series})

    result = evaluate(frame)

    result["evidence_unit"] = evidence_unit

    if source_decision is not None:
        result["source_decision"] = source_decision

    return result


def _summary_row(
    candidate,
    metric,
    gate,
    status="OK",
    error=None,
):
    metrics = gate.get("metrics", {})

    return {
        "candidate": candidate,
        "metric": metric,
        "status": status,
        "decision": gate.get("decision"),
        "source_decision": gate.get("source_decision"),
        "evidence_unit": gate.get("evidence_unit"),
        "observations": metrics.get("windows"),
        "average": metrics.get("average_spread"),
        "median": metrics.get("median_spread"),
        "positive_pct": metrics.get("positive_window_pct"),
        "worst": metrics.get("worst_window"),
        "best": None,
        "passed_checks": gate.get("passed_checks"),
        "total_checks": gate.get("total_checks"),
        "error": error,
    }


def _adapter_baseline(text: str):
    """
    Parse the OVERALL BASELINE OOS summary emitted by
    research.baseline_failure_decomposition.

    Expected structure:

        OVERALL BASELINE OOS
        days  mean_spread  median_spread  positive_day_pct  worst_day  best_day
        100   -0.3577      -0.4014        41.0              -4.9624    4.0734

    Evidence unit is DAYS.
    """

    match = re.search(
        r"OVERALL\s+BASELINE\s+OOS\s+"
        r"days\s+mean_spread\s+median_spread\s+"
        r"positive_day_pct\s+worst_day\s+best_day\s+"
        r"(\d+)\s+"
        r"([+-]?\d+(?:\.\d+)?)\s+"
        r"([+-]?\d+(?:\.\d+)?)\s+"
        r"([+-]?\d+(?:\.\d+)?)\s+"
        r"([+-]?\d+(?:\.\d+)?)\s+"
        r"([+-]?\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE | re.DOTALL,
    )

    if not match:
        raise ValueError("Incomplete baseline OOS summary.")

    days = int(match.group(1))
    mean = float(match.group(2))
    median = float(match.group(3))
    positive = float(match.group(4))
    worst = float(match.group(5))
    best = float(match.group(6))

    return {
        "windows": days,
        "average": mean,
        "median": median,
        "positive_pct": positive,
        "worst": worst,
        "best": best,
    }

def _adapter_conditional(text: str):
    summary = re.search(
        r"OOS SUMMARY\s*\n\s*\{([^}]+)\}",
        text,
        re.IGNORECASE | re.DOTALL,
    )

    if not summary:
        raise ValueError("Could not locate Conditional Score OOS SUMMARY.")

    body = summary.group(1)

    days = _parse_int(r"'days'\s*:\s*(\d+)", body)

    mean = _parse_float(
        r"'average_spread'\s*:\s*([+-]?\d+(?:\.\d+)?)",
        body,
    )

    median = _parse_float(
        r"'median_spread'\s*:\s*([+-]?\d+(?:\.\d+)?)",
        body,
    )

    positive = _parse_float(
        r"'positive_day_pct'\s*:\s*([+-]?\d+(?:\.\d+)?)",
        body,
    )

    if None in (days, mean, median, positive):
        raise ValueError("Incomplete Conditional Score summary.")

    return {
        "windows": days,
        "average": mean,
        "median": median,
        "positive_pct": positive,
        "worst": None,
        "best": None,
    }


def _adapter_agreement(text: str):
    match = re.search(
        r"ALL_DAYS\s+(\d+)\s+"
        r"([+-]?\d+(?:\.\d+)?)\s+"
        r"([+-]?\d+(?:\.\d+)?)\s+"
        r"([+-]?\d+(?:\.\d+)?)\s+"
        r"([+-]?\d+(?:\.\d+)?)\s+"
        r"([+-]?\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE,
    )

    if not match:
        raise ValueError("Could not locate Factor Agreement ALL_DAYS row.")

    return {
        "windows": int(match.group(1)),
        "average": float(match.group(2)),
        "median": float(match.group(3)),
        "positive_pct": float(match.group(4)),
        "worst": float(match.group(5)),
        "best": float(match.group(6)),
    }


def _parse_window_spreads(text: str):
    """
    Parse the standard:

    WINDOW n
    ...
    Spread : +/-x%

    structure used by the regime-aware candidate.
    """
    blocks = re.split(
        r"\n\s*WINDOW\s+\d+",
        text,
        flags=re.IGNORECASE,
    )

    spreads = []

    for block in blocks[1:]:
        match = re.search(
            r"Spread\s*:\s*([+-]?\d+(?:\.\d+)?)%",
            block,
            re.IGNORECASE,
        )

        if match:
            spreads.append(float(match.group(1)))

    return spreads


def _adapter_regime(text: str):
    spreads = _parse_window_spreads(text)

    if not spreads:
        raise ValueError("No regime-aware window spreads found.")

    return {
        "spreads": spreads,
        "windows": len(spreads),
    }


def _adapter_interaction(text: str):
    """
    C3.3 reports incremental spread for each interaction/window.

    We deliberately use incremental spread rather than raw candidate spread.
    """
    values = re.findall(
        r"Incremental\s*:\s*([+-]?\d+(?:\.\d+)?)%",
        text,
        re.IGNORECASE,
    )

    if not values:
        raise ValueError("No C3.3 incremental spreads found.")

    return {
        "spreads": [float(v) for v in values],
        "windows": len(values),
    }


def _direct_gate_from_summary(summary):
    """
    Apply the common gate to a summary without pretending that daily
    observations are walk-forward windows.

    The gate thresholds remain identical; the evidence unit is explicitly
    labelled.
    """
    windows = int(summary["windows"])
    positive = float(summary["positive_pct"])
    average = float(summary["average"])
    median = float(summary["median"])

    worst = summary.get("worst")

    checks = {
        "minimum_windows": windows >= 5,
        "positive_window_rate": positive >= 60.0,
        "average_spread": average > 0.0,
        "median_spread": median > 0.0,
        "worst_window": (
            True
            if worst is None
            else worst >= -2.0
        ),
    }

    passed = sum(checks.values())

    decision = (
        "PASS"
        if all(checks.values())
        else "REVIEW"
        if passed >= 3
        else "FAIL"
    )

    return {
        "decision": decision,
        "checks": checks,
        "passed_checks": passed,
        "total_checks": len(checks),
        "evidence_unit": "days",
        "metrics": {
            "windows": windows,
            "average_spread": average,
            "median_spread": median,
            "positive_window_pct": positive,
            "worst_window": worst,
            "best_window": summary.get("best"),
        },
    }


def run_candidate(spec: CandidateSpec):
    text = _run_module(spec.module)

    if spec.name == "Baseline Failure Decomposition":
        summary = _adapter_baseline(text)
        return _direct_gate_from_summary(summary)

    if spec.name == "Conditional Score":
        summary = _adapter_conditional(text)
        return _direct_gate_from_summary(summary)

    if spec.name == "Factor Agreement":
        summary = _adapter_agreement(text)
        return _direct_gate_from_summary(summary)

    if spec.name in {
        "C2.1 Regime-Aware",
        "C2.2 Regime-Aware",
    }:
        spreads = _adapter_regime(text)["spreads"]
        return _gate_from_spreads(
            spreads,
            evidence_unit="walk_forward_windows",
        )

    if spec.name == "C3.3 Factor Interaction":
        spreads = _adapter_interaction(text)["spreads"]
        return _gate_from_spreads(
            spreads,
            evidence_unit="interaction_windows",
        )

    raise ValueError(f"No adapter defined for {spec.name}")


def run_all():
    rows = []

    for spec in CANDIDATES:
        print(f"\nRunning: {spec.name}")

        try:
            gate = run_candidate(spec)

            row = _summary_row(
                spec.name,
                spec.metric,
                gate,
            )

            print(
                f"  Decision: {row['decision']} "
                f"({row['passed_checks']}/{row['total_checks']} checks)"
            )

        except Exception as exc:
            row = {
                "candidate": spec.name,
                "metric": spec.metric,
                "status": "ERROR",
                "decision": "UNAVAILABLE",
                "source_decision": None,
                "evidence_unit": None,
                "observations": None,
                "average": None,
                "median": None,
                "positive_pct": None,
                "worst": None,
                "best": None,
                "passed_checks": None,
                "total_checks": None,
                "error": str(exc),
            }

            print(f"  ERROR: {exc}")

        rows.append(row)

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Run all MarketBot research candidates through the read-only gate."
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Also print the unified table as JSON.",
    )

    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)

    results = run_all()

    results.to_csv(args.output, index=False)

    print("\n" + "=" * 100)
    print("MARKETBOT - UNIFIED RESEARCH DECISION TABLE")
    print("=" * 100)

    display_columns = [
        "candidate",
        "metric",
        "evidence_unit",
        "observations",
        "average",
        "median",
        "positive_pct",
        "worst",
        "decision",
        "status",
    ]

    print(
        results[display_columns]
        .round(4)
        .to_string(index=False)
    )

    print("\nSaved:")
    print(args.output)

    print(
        "\nREAD-ONLY: database, production scoring, factor weights, "
        "challenger logic, and live trading were NOT changed."
    )

    if args.json:
        print("\nJSON")
        print(
            json.dumps(
                results.to_dict(orient="records"),
                indent=2,
                default=str,
            )
        )


if __name__ == "__main__":
    main()
