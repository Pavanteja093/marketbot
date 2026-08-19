from __future__ import annotations

"""Safe candidate-specific Track-C OOS adapter.

Orchestrates existing Track-C research functions only. It never writes SQLite,
changes Track-C methodology, or executes an unauthorized relationship.
"""

import importlib
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = BASE_DIR / "market_intelligence.db"

TRACK_C_CANDIDATES = {
    "TRACK_C_FACTOR_INTERACTION": "research.factor_interaction_walk_forward",
    "TRACK_C_REGIME_AWARE": "research.regime_aware_walk_forward",
    "TRACK_C_SCENARIO_WEAPON": "research.scenario_weapon_candidate",
}
TRAIN_DAYS = 120
TEST_DAYS = 20
MIN_TOTAL_OBSERVATIONS = TRAIN_DAYS + TEST_DAYS
MIN_HOLDOUT_OBSERVATIONS = 1


def validate_relationship(scenario_id: str, fingerprint: str, candidate: str) -> None:
    if not str(scenario_id).strip() or not str(fingerprint).strip():
        raise ValueError("scenario_id and fingerprint must be non-empty.")
    if candidate not in TRACK_C_CANDIDATES:
        raise ValueError(f"Unsupported Track-C candidate: {candidate}")


def load_scenario_history(db_path: Path = DEFAULT_DB) -> pd.DataFrame:
    """Read scenario history through SQLite read-only mode."""
    uri = f"file:{Path(db_path).resolve()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        frame = pd.read_sql_query(
            """
            SELECT trade_date, scenario_id, primary_scenario, fingerprint
            FROM market_scenario_history
            ORDER BY trade_date
            """,
            conn,
        )
    finally:
        conn.close()
    required = {"trade_date", "scenario_id", "primary_scenario", "fingerprint"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError("market_scenario_history missing: " + ", ".join(missing))
    frame = frame.copy(deep=True)
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce")
    return frame.dropna(subset=["trade_date", "scenario_id", "fingerprint"])


def filter_relationship(data: pd.DataFrame, history: pd.DataFrame,
                        scenario_id: str, fingerprint: str) -> pd.DataFrame:
    """Restrict candidate input to the exact scenario/fingerprint date set."""
    h = history.loc[
        (history["scenario_id"].astype(str) == str(scenario_id))
        & (history["fingerprint"].astype(str) == str(fingerprint))
    ].copy(deep=True)
    if h.empty:
        return data.iloc[0:0].copy()
    dates = set(h["trade_date"])
    work = data.copy(deep=True)
    date_col = "prediction_date" if "prediction_date" in work.columns else "trade_date"
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    return work.loc[work[date_col].isin(dates)].copy()


def _insufficient(candidate, scenario_id, fingerprint, observations, reason=None):
    return {
        "candidate": candidate, "scenario_id": scenario_id, "fingerprint": fingerprint,
        "research_status": "INSUFFICIENT_HOLDOUT_HISTORY", "oos_result": "NOT_READY",
        "holdout_observations": 0, "scenario_matched_observations": int(observations),
        "execution_reason": reason or "Insufficient chronological history for the existing Track-C walk-forward geometry.",
    }


def _unsupported(candidate, scenario_id, fingerprint, reason):
    return {
        "candidate": candidate, "scenario_id": scenario_id, "fingerprint": fingerprint,
        "research_status": "UNSUPPORTED_OOS_PATH", "oos_result": "NOT_READY",
        "holdout_observations": 0, "scenario_matched_observations": 0,
        "execution_reason": reason,
    }


def _normalise(result: Any, candidate: str, scenario_id: str, fingerprint: str) -> dict:
    if isinstance(result, tuple):
        result = result[0]
    if isinstance(result, dict):
        result = result.get("results", result.get("summary", result))
    if not isinstance(result, pd.DataFrame) or result.empty:
        return _insufficient(candidate, scenario_id, fingerprint, 0)
    work = result.copy(deep=True)
    spread_col = "incremental_spread" if "incremental_spread" in work.columns else "spread" if "spread" in work.columns else None
    if spread_col is None:
        return _unsupported(candidate, scenario_id, fingerprint, "Existing Track-C function returned no OOS spread field.")
    spreads = pd.to_numeric(work[spread_col], errors="coerce").dropna()
    if len(spreads) < MIN_HOLDOUT_OBSERVATIONS:
        return _insufficient(candidate, scenario_id, fingerprint, len(spreads))
    return {
        "candidate": candidate, "scenario_id": scenario_id, "fingerprint": fingerprint,
        "research_status": "EXECUTED", "oos_result": "OOS_AVAILABLE",
        "holdout_observations": int(len(spreads)),
        "oos_average_spread": float(spreads.mean()),
        "oos_median_spread": float(spreads.median()),
        "oos_positive_day_pct": float((spreads > 0).mean() * 100),
        "oos_worst_day": float(spreads.min()), "oos_best_day": float(spreads.max()),
    }


def execute_track_c_relationship(scenario_id: str, fingerprint: str,
                                  candidate: str, db_path: Path = DEFAULT_DB) -> dict:
    """Execute exactly one authorized Track-C relationship."""
    validate_relationship(scenario_id, fingerprint, candidate)
    module = importlib.import_module(TRACK_C_CANDIDATES[candidate])
    history = load_scenario_history(db_path)

    if candidate == "TRACK_C_FACTOR_INTERACTION":
        if not all(hasattr(module, x) for x in ("load_data", "run_walk_forward")):
            return _unsupported(candidate, scenario_id, fingerprint, "Missing load_data/run_walk_forward interface.")
        data = module.load_data(db_path)
        subset = filter_relationship(data, history, scenario_id, fingerprint)
        dates = subset["trade_date"].dropna().nunique()
        if dates < MIN_TOTAL_OBSERVATIONS:
            return _insufficient(candidate, scenario_id, fingerprint, dates)
        result = module.run_walk_forward(subset)
        return _normalise(result, candidate, scenario_id, fingerprint)

    if candidate == "TRACK_C_REGIME_AWARE":
        if not all(hasattr(module, x) for x in ("load_data", "run")):
            return _unsupported(candidate, scenario_id, fingerprint, "Missing load_data/run interface.")
        data, _ = module.load_data(db_path)
        subset = filter_relationship(data, history, scenario_id, fingerprint)
        dates = subset["prediction_date"].dropna().nunique()
        if dates < MIN_TOTAL_OBSERVATIONS:
            return _insufficient(candidate, scenario_id, fingerprint, dates)
        result = module.run(subset, train_days=TRAIN_DAYS, test_days=TEST_DAYS)
        return _normalise(result, candidate, scenario_id, fingerprint)

    if candidate == "TRACK_C_SCENARIO_WEAPON":
        if not all(hasattr(module, x) for x in ("load_data", "run_scenario_walk_forward")):
            return _unsupported(candidate, scenario_id, fingerprint, "Missing load_data/run_scenario_walk_forward interface.")
        data, nifty_scenarios = module.load_data(db_path)
        subset = filter_relationship(data, history, scenario_id, fingerprint)
        dates = subset["trade_date"].dropna().nunique()
        if dates < MIN_TOTAL_OBSERVATIONS:
            return _insufficient(candidate, scenario_id, fingerprint, dates)
        nifty_scenarios = nifty_scenarios.copy(deep=True)
        nifty_scenarios["trade_date"] = pd.to_datetime(nifty_scenarios["trade_date"], errors="coerce")
        nifty_scenarios = nifty_scenarios.loc[nifty_scenarios["trade_date"].isin(set(subset["trade_date"]))].copy()
        result = module.run_scenario_walk_forward(subset, nifty_scenarios)
        return _normalise(result, candidate, scenario_id, fingerprint)

    return _unsupported(candidate, scenario_id, fingerprint, "No safe Track-C route exists.")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Execute one safe Track-C OOS relationship.")
    parser.add_argument("scenario_id")
    parser.add_argument("fingerprint")
    parser.add_argument("candidate")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    result = execute_track_c_relationship(args.scenario_id, args.fingerprint, args.candidate, args.db)
    print("\nMARKETBOT - SAFE TRACK-C OOS ADAPTER")
    for key, value in result.items():
        print(f"{key:<28}: {value}")
    print("\nREAD-ONLY: no SQLite writes or production changes.")


if __name__ == "__main__":
    main()