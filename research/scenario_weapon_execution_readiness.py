from __future__ import annotations

"""MarketBot - Scenario × Weapon Execution Readiness Audit.

Research-only audit that checks whether queued relationships have enough
*overlapping* genuine candidate OOS dates to execute the existing holdout
methodology. It does not change queue/eligibility artifacts or SQLite.
"""

from pathlib import Path
import importlib
import sqlite3
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = BASE_DIR / "market_intelligence.db"
DEFAULT_QUEUE = BASE_DIR / "research" / "artifacts" / "scenario_weapon_research_queue.csv"
DEFAULT_OUTPUT = BASE_DIR / "research" / "artifacts" / "scenario_weapon_execution_readiness.csv"

TRACK_B = {
    "TRACK_B_BASELINE_FAILURE",
    "TRACK_B_CONDITIONAL_SCORE",
    "TRACK_B_FACTOR_AGREEMENT",
}
TRACK_C = {
    "TRACK_C_FACTOR_INTERACTION",
    "TRACK_C_REGIME_AWARE",
    "TRACK_C_SCENARIO_WEAPON",
}

REQUIRED_QUEUE = {
    "scenario_id", "primary_scenario", "fingerprint", "candidate",
    "scenario_observations", "oos_windows", "target_oos_windows",
    "eligibility_status", "research_priority", "queue_priority", "queue_action",
}

OUTPUT_COLUMNS = [
    "scenario_id", "primary_scenario", "fingerprint", "candidate",
    "scenario_observations", "candidate_oos_dates", "overlap_oos_dates",
    "overlap_pct_of_scenario", "current_oos_windows", "target_oos_windows",
    "queue_priority", "queue_action", "research_priority",
    "methodology_min_observations", "execution_readiness",
    "readiness_reason",
]


def _load_scenario_history(db_path: Path) -> pd.DataFrame:
    uri = f"file:{Path(db_path).resolve()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        frame = pd.read_sql_query(
            "SELECT trade_date, scenario_id, fingerprint FROM market_scenario_history",
            conn,
        )
    finally:
        conn.close()
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce").dt.normalize()
    return frame.dropna(subset=["trade_date", "scenario_id", "fingerprint"])


def _candidate_dates(db_path: Path) -> dict[str, set[pd.Timestamp]]:
    adapter = importlib.import_module("research.scenario_weapon_oos")
    loaders = {
        "TRACK_B_BASELINE_FAILURE": adapter.load_baseline_results,
        "TRACK_B_CONDITIONAL_SCORE": adapter.load_conditional_results,
        "TRACK_B_FACTOR_AGREEMENT": adapter.load_agreement_results,
    }
    out = {}
    for name, loader in loaders.items():
        frame = loader(db_path)
        dates = pd.to_datetime(frame["trade_date"], errors="coerce").dt.normalize().dropna()
        out[name] = set(dates)
    return out


def audit(queue: pd.DataFrame, db_path: Path = DEFAULT_DB) -> pd.DataFrame:
    missing = sorted(REQUIRED_QUEUE - set(queue.columns))
    if missing:
        raise ValueError("Queue missing required columns: " + ", ".join(missing))

    history = _load_scenario_history(db_path)
    candidate_dates = _candidate_dates(db_path)

    scenario_map = {}
    for key, group in history.groupby(["scenario_id", "fingerprint"], sort=True):
        scenario_map[key] = set(group["trade_date"])

    rows = []
    for _, r in queue.iterrows():
        scenario_id = str(r["scenario_id"])
        fingerprint = str(r["fingerprint"])
        candidate = str(r["candidate"])
        scenario_dates = scenario_map.get((scenario_id, fingerprint), set())
        scenario_count = len(scenario_dates)

        if candidate in TRACK_B:
            c_dates = candidate_dates.get(candidate, set())
            overlap = len(scenario_dates & c_dates)
            minimum = 20
            if overlap >= minimum:
                readiness = "READY_FOR_OOS"
                reason = f"{overlap} exact scenario/OOS dates meet the existing >=20 observation holdout threshold."
            else:
                readiness = "BLOCKED_NO_HOLDOUT"
                reason = f"Only {overlap} exact overlapping OOS dates; existing Track-B holdout path requires >=20 observations."
            candidate_count = len(c_dates)
        elif candidate in TRACK_C:
            # Existing safe Track-C adapter requires 120 train + 20 test dates.
            c_dates = set()
            overlap = 0
            minimum = 140
            readiness = "BLOCKED_NO_HOLDOUT"
            reason = f"Track-C adapter requires {minimum} chronological observations; scenario has only {scenario_count}."
            candidate_count = 0
        else:
            candidate_count = 0
            overlap = 0
            minimum = 20
            readiness = "UNSUPPORTED_CANDIDATE"
            reason = "Candidate is not exposed by the current research execution boundary."

        rows.append({
            "scenario_id": scenario_id,
            "primary_scenario": r["primary_scenario"],
            "fingerprint": fingerprint,
            "candidate": candidate,
            "scenario_observations": scenario_count,
            "candidate_oos_dates": candidate_count,
            "overlap_oos_dates": overlap,
            "overlap_pct_of_scenario": round((overlap / scenario_count * 100.0), 2) if scenario_count else 0.0,
            "current_oos_windows": int(r["oos_windows"]),
            "target_oos_windows": int(r["target_oos_windows"]),
            "queue_priority": r["queue_priority"],
            "queue_action": r["queue_action"],
            "research_priority": r["research_priority"],
            "methodology_min_observations": minimum,
            "execution_readiness": readiness,
            "readiness_reason": reason,
        })

    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def run(db_path: Path = DEFAULT_DB, queue_path: Path = DEFAULT_QUEUE,
        output_path: Path = DEFAULT_OUTPUT) -> pd.DataFrame:
    queue = pd.read_csv(queue_path)
    result = audit(queue, db_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    print("=" * 92)
    print("MARKETBOT - SCENARIO × WEAPON EXECUTION READINESS AUDIT")
    print("=" * 92)
    print(f"Relationships audited : {len(result):,}")
    print("\nReadiness:")
    print(result["execution_readiness"].value_counts().to_string())
    print("\nTop executable relationships:")
    ready = result[result["execution_readiness"] == "READY_FOR_OOS"]
    print(ready.head(20).to_string(index=False) if not ready.empty else "NONE")
    print(f"\nSaved: {output_path}")
    print("READ-ONLY: no SQLite writes, queue mutation, or production changes.")
    return result


if __name__ == "__main__":
    run()
