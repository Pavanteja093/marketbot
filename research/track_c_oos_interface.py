from __future__ import annotations

"""Safe, read-only candidate-specific Track-C OOS interface.

It reuses the existing Track-C walk-forward entry points, applies the exact
scenario_id/fingerprint/candidate identity boundary first, and never writes
SQLite or production state.
"""

import importlib
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = BASE_DIR / "market_intelligence.db"

TRACK_C_CANDIDATES = {
    "TRACK_C_FACTOR_INTERACTION": (
        ("research.factor_interaction_walk_forward",),
        "load_data", "run_walk_forward",
    ),
    "TRACK_C_REGIME_AWARE": (
        ("research.regime_aware_walk_forward_v3",
         "research.regime_aware_walk_forward",
         "research.regime_aware_model_v2"),
        "load_data", "run_walk_forward",
    ),
    "TRACK_C_SCENARIO_WEAPON": (
        ("research.scenario_weapon_candidate",),
        "load_data", "run_scenario_walk_forward",
    ),
}

MIN_TOTAL_OBSERVATIONS = 20
MIN_HOLDOUT_OBSERVATIONS = 5
TRAIN_DAYS = 120
TEST_DAYS = 20

RESULT_COLUMNS = [
    "candidate", "scenario_id", "fingerprint", "research_status",
    "oos_result", "scenario_matched_observations", "train_observations",
    "holdout_observations", "train_start", "train_end", "holdout_start",
    "holdout_end", "execution_reason",
]


def validate_relationship(scenario_id: str, fingerprint: str, candidate: str) -> None:
    if not str(scenario_id).strip() or not str(fingerprint).strip():
        raise ValueError("scenario_id and fingerprint must be non-empty.")
    if candidate not in TRACK_C_CANDIDATES:
        raise ValueError(f"Unsupported Track-C candidate: {candidate}")


def validate_relationships(frame: pd.DataFrame) -> None:
    required = {"scenario_id", "fingerprint", "candidate"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError("Relationship input missing: " + ", ".join(missing))
    if frame.duplicated(["scenario_id", "fingerprint", "candidate"], keep=False).any():
        raise ValueError("Duplicate Track-C relationship detected.")
    for r in frame.itertuples(index=False):
        validate_relationship(r.scenario_id, r.fingerprint, r.candidate)


def load_scenario_history(db_path: Path = DEFAULT_DB) -> pd.DataFrame:
    uri = f"file:{Path(db_path).resolve()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        out = pd.read_sql_query(
            """SELECT trade_date, scenario_id, primary_scenario, fingerprint
               FROM market_scenario_history
               ORDER BY DATE(trade_date), scenario_id, fingerprint""",
            conn,
        )
    finally:
        conn.close()
    required = {"trade_date", "scenario_id", "primary_scenario", "fingerprint"}
    missing = sorted(required - set(out.columns))
    if missing:
        raise ValueError("market_scenario_history missing: " + ", ".join(missing))
    out = out.copy(deep=True)
    out["trade_date"] = pd.to_datetime(out["trade_date"], errors="coerce")
    return out.dropna(subset=["trade_date"]).reset_index(drop=True)


def filter_relationship(data: pd.DataFrame, history: pd.DataFrame,
                        scenario_id: str, fingerprint: str,
                        candidate: str) -> pd.DataFrame:
    """Exact candidate + scenario_id + fingerprint date boundary."""
    validate_relationship(scenario_id, fingerprint, candidate)
    h = history.loc[
        (history["scenario_id"].astype(str) == str(scenario_id)) &
        (history["fingerprint"].astype(str) == str(fingerprint))
    ].copy(deep=True)
    if h.empty:
        return data.iloc[0:0].copy(deep=True)
    date_col = "prediction_date" if "prediction_date" in data.columns else "trade_date"
    if date_col not in data.columns:
        raise ValueError("Candidate data has no prediction_date/trade_date.")
    work = data.copy(deep=True)
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    out = work.loc[work[date_col].isin(set(h["trade_date"]))].copy(deep=True)
    if "candidate" in out.columns:
        out = out.loc[out["candidate"].astype(str) == str(candidate)].copy(deep=True)
    return out.reset_index(drop=True)


def chronological_holdout(frame: pd.DataFrame, date_col: str,
                           train_days: int = TRAIN_DAYS,
                           holdout_days: int = MIN_HOLDOUT_OBSERVATIONS):
    """Chronological split only; train is strictly earlier than holdout."""
    if date_col not in frame.columns:
        raise ValueError(f"Missing date column: {date_col}")
    work = frame.copy(deep=True)
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    work = work.dropna(subset=[date_col]).sort_values(date_col, kind="stable")
    dates = pd.Index(work[date_col].drop_duplicates())
    if len(dates) < train_days + holdout_days:
        return None
    train_dates = dates[:len(dates) - holdout_days][-train_days:]
    test_dates = dates[len(dates) - holdout_days:]
    train = work.loc[work[date_col].isin(train_dates)].copy()
    test = work.loc[work[date_col].isin(test_dates)].copy()
    if train.empty or test.empty or train[date_col].max() >= test[date_col].min():
        raise RuntimeError("Chronological OOS boundary violated.")
    return train.reset_index(drop=True), test.reset_index(drop=True)


def _insufficient(candidate, scenario_id, fingerprint, matched, reason):
    return {
        "candidate": candidate, "scenario_id": scenario_id,
        "fingerprint": fingerprint,
        "research_status": "INSUFFICIENT_HOLDOUT_HISTORY",
        "oos_result": "NOT_READY",
        "scenario_matched_observations": int(matched),
        "train_observations": 0, "holdout_observations": 0,
        "execution_reason": reason,
    }


def _import_candidate(candidate):
    modules, _, _ = TRACK_C_CANDIDATES[candidate]
    errors = []
    for name in modules:
        try:
            return importlib.import_module(name)
        except ImportError as exc:
            errors.append(f"{name}: {exc}")
    raise ImportError("No configured Track-C implementation: " + " | ".join(errors))


def _normalise(result: Any, candidate, scenario_id, fingerprint, matched):
    if isinstance(result, tuple):
        result = result[0]
    if isinstance(result, dict):
        result = result.get("results", result.get("summary", result))
    if not isinstance(result, pd.DataFrame) or result.empty:
        return _insufficient(candidate, scenario_id, fingerprint, matched,
                             "Existing Track-C methodology returned no OOS observations.")

    work = result.copy(deep=True)

    # Candidate-specific selector: never accept an all-weapon result.
    if candidate == "TRACK_C_FACTOR_INTERACTION" and "interaction" in work.columns:
        wanted = str(fingerprint).replace("__x__", " × ")
        work = work.loc[work["interaction"].astype(str) == wanted].copy()
    elif candidate == "TRACK_C_SCENARIO_WEAPON":
        if "weapon" not in work.columns:
            return _insufficient(candidate, scenario_id, fingerprint, matched,
                                 "No weapon identity in result; refusing non-specific execution.")
        work = work.loc[work["weapon"].astype(str) == str(fingerprint)].copy()
        if work.empty:
            r = _insufficient(candidate, scenario_id, fingerprint, matched,
                              "Fingerprint is not an existing fixed weapon; refusing all-weapon execution.")
            r["research_status"] = "UNSUPPORTED_OOS_PATH"
            return r

    spread_col = next((c for c in ("incremental_spread", "test_spread", "spread")
                       if c in work.columns), None)
    if spread_col is None:
        r = _insufficient(candidate, scenario_id, fingerprint, matched,
                          "Existing Track-C result has no recognised OOS spread field.")
        r["research_status"] = "UNSUPPORTED_OOS_PATH"
        return r

    spreads = pd.to_numeric(work[spread_col], errors="coerce").dropna()
    if len(spreads) < MIN_HOLDOUT_OBSERVATIONS:
        return _insufficient(candidate, scenario_id, fingerprint, matched,
                             "Fewer than 5 genuine OOS holdout observations.")

    return {
        "candidate": candidate, "scenario_id": scenario_id,
        "fingerprint": fingerprint, "research_status": "EXECUTED",
        "oos_result": "OOS_AVAILABLE",
        "scenario_matched_observations": int(matched),
        "train_observations": None, "holdout_observations": int(len(spreads)),
        "train_start": None, "train_end": None,
        "holdout_start": None, "holdout_end": None,
        "execution_reason": "Existing Track-C methodology executed after exact relationship filtering.",
    }


def execute_relationship(scenario_id: str, fingerprint: str, candidate: str,
                         db_path: Path = DEFAULT_DB) -> dict:
    validate_relationship(scenario_id, fingerprint, candidate)
    module = _import_candidate(candidate)
    history = load_scenario_history(db_path)
    modules, loader_name, runner_name = TRACK_C_CANDIDATES[candidate]
    loader = getattr(module, loader_name, None)
    runner = getattr(module, runner_name, None)
    if loader is None or runner is None:
        r = _insufficient(candidate, scenario_id, fingerprint, 0,
                          "Existing module lacks the required candidate-specific interface.")
        r["research_status"] = "UNSUPPORTED_OOS_PATH"
        return r

    loaded = loader(db_path)
    data = loaded[0] if isinstance(loaded, tuple) else loaded
    subset = filter_relationship(data, history, scenario_id, fingerprint, candidate)
    date_col = "prediction_date" if "prediction_date" in subset.columns else "trade_date"
    matched = subset[date_col].dropna().nunique()
    if matched < MIN_TOTAL_OBSERVATIONS:
        return _insufficient(candidate, scenario_id, fingerprint, matched,
                             "Insufficient genuine history for the existing walk-forward geometry.")

    if candidate == "TRACK_C_FACTOR_INTERACTION":
        result = runner(subset, train_days=TRAIN_DAYS, test_days=TEST_DAYS)
    elif candidate == "TRACK_C_REGIME_AWARE":
        cfg_cls = getattr(module, "Config", None) or getattr(module, "ModelConfig", None)
        if cfg_cls is None:
            r = _insufficient(candidate, scenario_id, fingerprint, matched,
                              "Regime module exposes no compatible Config/ModelConfig.")
            r["research_status"] = "UNSUPPORTED_OOS_PATH"
            return r
        result = runner(subset, cfg_cls(train_days=TRAIN_DAYS, test_days=TEST_DAYS))
    else:
        weapons = getattr(module, "WEAPONS", {})
        if fingerprint not in weapons:
            r = _insufficient(candidate, scenario_id, fingerprint, matched,
                              "Fingerprint is not a fixed weapon name; refusing all-weapon execution.")
            r["research_status"] = "UNSUPPORTED_OOS_PATH"
            return r
        scenarios = loaded[1].copy(deep=True)
        scenarios["trade_date"] = pd.to_datetime(scenarios["trade_date"], errors="coerce")
        scenarios = scenarios.loc[scenarios["trade_date"].isin(set(subset["trade_date"]))]
        cfg_cls = getattr(module, "Config", None)
        result = runner(subset, scenarios, fingerprint, config=cfg_cls() if cfg_cls else None)

    return _normalise(result, candidate, scenario_id, fingerprint, matched)


def execute_batch(relationships: pd.DataFrame, db_path: Path = DEFAULT_DB) -> pd.DataFrame:
    validate_relationships(relationships)
    rows = []
    ordered = relationships.sort_values(
        ["candidate", "scenario_id", "fingerprint"], kind="mergesort"
    )
    for r in ordered.itertuples(index=False):
        rows.append(execute_relationship(r.scenario_id, r.fingerprint, r.candidate, db_path))
    return pd.DataFrame(rows, columns=RESULT_COLUMNS)


def main():
    import argparse
    p = argparse.ArgumentParser(description="Safe candidate-specific Track-C OOS interface.")
    p.add_argument("scenario_id")
    p.add_argument("fingerprint")
    p.add_argument("candidate")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    a = p.parse_args()
    result = execute_relationship(a.scenario_id, a.fingerprint, a.candidate, a.db)
    print("\nMARKETBOT - TRACK-C SAFE OOS INTERFACE")
    for k, v in result.items():
        print(f"{k:<32}: {v}")
    print("\nREAD-ONLY: no SQLite writes or production changes.")


if __name__ == "__main__":
    main()
