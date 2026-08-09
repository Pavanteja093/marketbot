from __future__ import annotations

import importlib.util
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"
PYTHON = sys.executable


@dataclass(frozen=True)
class Task:
    name: str
    module: str
    critical: bool = True


SYNCHRONIZATION = [
    Task("Market Data Repair", "automation.repair_market_data"),
    Task("Database Doctor", "automation.database_doctor"),
]

DATA_COLLECTION = [
    Task("Stocks Collector", "data_collectors.stocks"),
    Task("Indices Collector", "data_collectors.indices"),
    Task("FII/DII Collector", "data_collectors.fii_dii", False),
]


def module_exists(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def preflight() -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not DB_PATH.exists():
        return False, [f"Database not found: {DB_PATH}"]

    with sqlite3.connect(DB_PATH) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

    required = {"stocks_daily", "indices_daily", "signal_history_v2"}
    missing = sorted(required - tables)
    if missing:
        errors.append("Missing required V2 tables: " + ", ".join(missing))

    for package in ("data_collectors", "analytics"):
        if not (BASE_DIR / package).is_dir():
            errors.append(f"Required package missing: {package}")

    for module in (
        "analytics.stock_scoring_v2",
        "analytics.trend_intelligence",
        "analytics.sector_mapping",
    ):
        if not module_exists(module):
            errors.append(f"Required module missing: {module}")

    return not errors, errors


def run_module(task: Task) -> bool:
    print("\n" + "-" * 70)
    print(task.name)
    print("-" * 70)
    try:
        result = subprocess.run(
            [PYTHON, "-m", task.module],
            cwd=BASE_DIR,
            text=True,
            capture_output=True,
        )
    except OSError as exc:
        print(f"ERROR: could not start {task.module}: {exc}")
        return False

    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip())

    ok = result.returncode == 0
    print(f"STATUS: {'SUCCESS' if ok else 'FAILED'}")
    return ok


def validate_signal_history_schema() -> bool:
    required = {"trade_date", "index_name", "sector", "intelligence_score", "rank"}
    with sqlite3.connect(DB_PATH) as conn:
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(signal_history_v2)")
        }
    missing = sorted(required - columns)
    if missing:
        print("ERROR: signal_history_v2 missing: " + ", ".join(missing))
        return False
    return True


def save_v2_signals() -> tuple[bool, int]:
    # This imports the existing V2 scorer without changing its scoring logic.
    from analytics.stock_scoring_v2 import get_stock_scores_v2

    if not validate_signal_history_schema():
        return False, 0

    df = get_stock_scores_v2()
    if df is None or df.empty:
        print("ERROR: V2 scorer returned no stocks.")
        return False, 0

    required_output = {"symbol", "sector", "intelligence_score", "grade"}
    missing = sorted(required_output - set(df.columns))
    if missing:
        print("ERROR: V2 scorer output missing: " + ", ".join(missing))
        return False, 0

    df = df.dropna(subset=["symbol", "intelligence_score"]).copy()
    if df.empty:
        print("ERROR: V2 scorer returned no valid scores.")
        return False, 0

    with sqlite3.connect(DB_PATH) as conn:
        latest_date = conn.execute(
            "SELECT MAX(trade_date) FROM stocks_daily"
        ).fetchone()[0]
        if not latest_date:
            print("ERROR: no latest stocks trade date.")
            return False, 0

        top10 = df.head(10)
        conn.execute(
            "DELETE FROM signal_history_v2 WHERE trade_date = ?",
            (latest_date,),
        )

        rows = [
            (
                latest_date,
                str(row["symbol"]),
                None if row["sector"] is None else str(row["sector"]),
                float(row["intelligence_score"]),
                rank,
            )
            for rank, (_, row) in enumerate(top10.iterrows(), start=1)
        ]

        conn.executemany(
            """
            INSERT INTO signal_history_v2
            (trade_date, index_name, sector, intelligence_score, rank)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()

        saved = conn.execute(
            "SELECT COUNT(*) FROM signal_history_v2 WHERE trade_date = ?",
            (latest_date,),
        ).fetchone()[0]

    print(f"Saved {saved} V2 signals for {latest_date}.")
    return saved == len(rows) and saved > 0, saved


def run_v2_scoring() -> bool:
    print("\n" + "-" * 70)
    print("Production Stock Scoring V2")
    print("-" * 70)
    try:
        ok, saved = save_v2_signals()
    except Exception as exc:
        print(f"V2 scoring/persistence failed: {exc}")
        return False
    print(f"STATUS: {'SUCCESS' if ok else 'FAILED'}")
    return ok


def verify_core_output() -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        latest_date = conn.execute(
            "SELECT MAX(trade_date) FROM stocks_daily"
        ).fetchone()[0]
        signals = conn.execute(
            "SELECT COUNT(*) FROM signal_history_v2 WHERE trade_date = ?",
            (latest_date,),
        ).fetchone()[0]

    print(f"Latest stocks date : {latest_date}")
    print(f"V2 signals saved   : {signals}")
    ok = bool(latest_date and signals > 0)
    print(f"STATUS: {'SUCCESS' if ok else 'FAILED'}")
    return ok


def main() -> int:
    print("\n" + "=" * 78)
    print("MARKETBOT PRODUCTION DAILY UPDATE V2")
    print("=" * 78)

    ok, errors = preflight()
    if not ok:
        print("\nPREFLIGHT FAILED")
        for error in errors:
            print(f"- {error}")
        return 2

    failures: list[str] = []

    print("\n" + "=" * 78)
    print("DATABASE SYNCHRONIZATION")
    print("=" * 78)
    for task in SYNCHRONIZATION:
        if not run_module(task):
            failures.append(task.name)
            if task.critical:
                print("\nCRITICAL FAILURE: synchronization stopped.")
                return 2

    print("\n" + "=" * 78)
    print("DATA COLLECTION")
    print("=" * 78)
    for task in DATA_COLLECTION:
        if not run_module(task):
            failures.append(task.name)
            if task.critical:
                print(f"\nCRITICAL FAILURE: {task.name}")
                return 2

    print("\nOPTION CHAIN COLLECTOR")
    print("-" * 70)
    print(
        "SKIPPED: current option_chain_upstox.py writes to "
        "option_chain_history/system_status, which do not exist in the "
        "current database. No schema is changed by V2."
    )

    print("\n" + "=" * 78)
    print("FEATURE ENGINEERING")
    print("=" * 78)
    print(
        "SKIPPED: current standalone feature_builder expects "
        "option_chain_history/market_features and is not a dependency "
        "of stock_scoring_v2."
    )

    print("\n" + "=" * 78)
    print("MARKET INTELLIGENCE")
    print("=" * 78)
    if not run_v2_scoring():
        failures.append("Production Stock Scoring V2")
        return 2

    print("\n" + "=" * 78)
    print("HISTORY")
    print("=" * 78)
    print("V2 ranking history persisted to signal_history_v2.")
    print(
        "Prediction history not generated: current V2 scorer does not "
        "produce prediction/confidence/risk values, so V2 will not invent them."
    )

    print("\n" + "=" * 78)
    print("LEARNING / OUTCOMES")
    print("=" * 78)

    if not run_module(
        Task("V2 Outcome Tracker", "learning.v2_outcome_tracker", False)
    ):
        failures.append("V2 Outcome Tracker")
        print(
            "NON-CRITICAL: V2 outcome tracking failed. "
            "Core V2 scoring remains valid."
        )

    print("\n" + "=" * 78)
    print("REPORTING")
    print("=" * 78)
    print(
        "SKIPPED: reporting dependencies are not yet part of the verified "
        "V2 production contract."
    )

    print("\n" + "=" * 78)
    print("FINAL VALIDATION")
    print("=" * 78)
    if not verify_core_output():
        failures.append("V2 Core Output Validation")
        return 2

    print("\n" + "=" * 78)
    print("V2 DAILY UPDATE SUMMARY")
    print("=" * 78)
    if failures:
        print("STATUS: CORE COMPLETED WITH NON-CRITICAL GAPS")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("STATUS: SUCCESS")
    print("Core V2 production pipeline completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
