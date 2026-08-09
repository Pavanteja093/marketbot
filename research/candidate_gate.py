from __future__ import annotations

"""Reusable acceptance gate for research candidates."""

import argparse
import json
from pathlib import Path

import pandas as pd

DEFAULT_RULES = {
    "min_windows": 5,
    "min_positive_window_pct": 60.0,
    "min_average_spread": 0.0,
    "min_median_spread": 0.0,
    "max_worst_window": -2.0,
}


def evaluate(results: pd.DataFrame, rules: dict | None = None) -> dict:
    r = {**DEFAULT_RULES, **(rules or {})}

    spreads = pd.to_numeric(
        results.get("spread", pd.Series(dtype=float)),
        errors="coerce",
    ).dropna()

    checks = {
        "minimum_windows": len(spreads) >= r["min_windows"],
        "positive_window_rate": bool(
            len(spreads)
            and (spreads > 0).mean() * 100 >= r["min_positive_window_pct"]
        ),
        "average_spread": bool(
            len(spreads) and spreads.mean() > r["min_average_spread"]
        ),
        "median_spread": bool(
            len(spreads) and spreads.median() > r["min_median_spread"]
        ),
        "worst_window": bool(
            len(spreads) and spreads.min() >= r["max_worst_window"]
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
        "metrics": {
            "windows": int(len(spreads)),
            "average_spread": float(spreads.mean()) if len(spreads) else None,
            "median_spread": float(spreads.median()) if len(spreads) else None,
            "positive_window_pct": (
                float((spreads > 0).mean() * 100) if len(spreads) else None
            ),
            "worst_window": float(spreads.min()) if len(spreads) else None,
        },
        "rules": r,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    args = parser.parse_args()
    result = evaluate(pd.read_csv(args.csv))
    print(json.dumps(result, indent=2))
