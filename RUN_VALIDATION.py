from __future__ import annotations

import ast
import importlib
import py_compile
import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "market_intelligence.db"
LOG_DIR = ROOT / "validation_logs"
LOG_DIR.mkdir(exist_ok=True)

RESULTS = []


def log_name(name):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)


def run_command(name, command, timeout=300):
    print(f"\n{'-' * 70}")
    print(f"TRACK: {name}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log = LOG_DIR / f"{stamp}_{log_name(name)}.log"

    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )

        log.write_text(
            result.stdout or "",
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode == 0:
            print("STATUS : PASS")
            RESULTS.append((name, "PASS", None))
            return True

        print(f"STATUS : FAIL (exit code {result.returncode})")
        print("ERROR DETAILS:")

        lines = (result.stdout or "").splitlines()

        patterns = (
            "Traceback",
            "Error:",
            "ERROR",
            "FAILED",
            "FAIL:",
            "ModuleNotFoundError",
            "ImportError",
            "SyntaxError",
            "DatabaseError",
            "OperationalError",
            "FileNotFoundError",
            "PermissionError",
            "KeyError",
            "TypeError",
            "ValueError",
        )

        found = []
        capture = False

        for line in lines:
            if any(p in line for p in patterns):
                capture = True

            if capture:
                found.append(line)

            if len(found) >= 25:
                break

        print("\n".join(found) if found else "\n".join(lines[-25:]))
        print(f"FULL LOG : {log}")

        RESULTS.append((name, "FAIL", log))
        return False

    except subprocess.TimeoutExpired:
        print(f"STATUS : FAIL")
        print("ERROR DETAILS:")
        print(f"TIMEOUT: command exceeded {timeout} seconds")
        print(f"FULL LOG : {log}")
        RESULTS.append((name, "FAIL", log))
        return False


def compile_all():
    name = "PYTHON COMPILATION"
    print(f"\n{'-' * 70}")
    print(f"TRACK: {name}")

    files = list(ROOT.rglob("*.py"))
    failures = []

    for path in files:
        try:
            py_compile.compile(
                str(path),
                doraise=True,
            )
        except Exception as exc:
            failures.append((path, exc))

    if failures:
        print("STATUS : FAIL")
        print(f"Files checked : {len(files)}")
        print(f"Failures     : {len(failures)}")

        for path, exc in failures[:20]:
            print(f"\n{path}")
            print(exc)

        RESULTS.append((name, "FAIL", None))
        return False

    print("STATUS : PASS")
    print(f"Files checked : {len(files)}")
    print("Compile failures : 0")

    RESULTS.append((name, "PASS", None))
    return True


def import_audit():
    name = "IMPORT/API STABILITY"

    modules = [
        "analytics.alpha_signal_test",
        "analytics.capital_flow",
        "analytics.intelligence_pipeline",
        "analytics.macro_interpreter",
        "analytics.market_explainer",
        "analytics.morning_report",
        "analytics.signal_engine",
        "analytics.stock_reason_engine",
        "analytics.trading_playbook",
        "analytics.stock_scoring",
        "research.prediction_history",
        "research.forward_returns",
        "research.factor_research",
        "research.factor_performance",
        "research.walk_forward",
        "learning.learning_engine",
        "learning.weight_optimizer",
    ]

    print(f"\n{'-' * 70}")
    print(f"TRACK: {name}")

    failures = []

    for module in modules:
        try:
            importlib.import_module(module)
        except Exception as exc:
            failures.append((module, exc))

    if failures:
        print("STATUS : FAIL")
        for module, exc in failures:
            print(f"\n{module}")
            print(f"{type(exc).__name__}: {exc}")

        RESULTS.append((name, "FAIL", None))
        return False

    print(f"STATUS : PASS")
    print(f"Modules checked : {len(modules)}")

    RESULTS.append((name, "PASS", None))
    return True


def feature_engine_contract():
    name = "FEATURE ENGINE CONTRACT"

    print(f"\n{'-' * 70}")
    print(f"TRACK: {name}")

    try:
        from analytics.feature_engine import FeatureEngine

        engine = FeatureEngine()

        if not hasattr(engine, "build_features"):
            raise AssertionError(
                "FeatureEngine.build_features is missing"
            )

        signature = __import__("inspect").signature(
            engine.build_features
        )

        required = [
            "history_df",
            "stock_return",
            "market_return",
        ]

        missing = [
            x for x in required
            if x not in signature.parameters
        ]

        if missing:
            raise AssertionError(
                f"Missing parameters: {missing}"
            )

        print("STATUS : PASS")
        print("FeatureEngine.build_features : VALID")
        RESULTS.append((name, "PASS", None))
        return True

    except Exception as exc:
        print("STATUS : FAIL")
        print(f"{type(exc).__name__}: {exc}")
        RESULTS.append((name, "FAIL", None))
        return False


def database_contract():
    name = "DATABASE INTEGRITY"

    print(f"\n{'-' * 70}")
    print(f"TRACK: {name}")

    required = {
        "stocks_daily": [
            "trade_date",
            "symbol",
            "close",
        ],
        "indices_daily": [
            "trade_date",
            "index_name",
            "close",
        ],
        "factor_history": [
            "trade_date",
            "index_name",
        ],
        "prediction_history": [
            "trade_date",
            "index_name",
        ],
        "forward_returns": [
            "trade_date",
            "index_name",
        ],
        "option_chain_history": [
            "trade_time",
            "symbol",
            "expiry",
            "strike",
            "call_oi",
            "put_oi",
            "spot_price",
        ],
        "factor_library": [
            "trade_date",
            "index_name",
            "position_52w",
            "breakout_distance",
            "volume_expansion",
        ],
    }

    try:
        conn = sqlite3.connect(DB_PATH)

        integrity = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise AssertionError(
                f"SQLite integrity check: {integrity}"
            )

        existing = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table'"
            )
        }

        missing_tables = [
            table
            for table in required
            if table not in existing
        ]

        if missing_tables:
            raise AssertionError(
                f"Missing tables: {missing_tables}"
            )

        missing_columns = {}

        for table, columns in required.items():
            actual = {
                row[1]
                for row in conn.execute(
                    f'PRAGMA table_info("{table}")'
                )
            }

            missing = [
                column
                for column in columns
                if column not in actual
            ]

            if missing:
                missing_columns[table] = missing

        conn.close()

        if missing_columns:
            raise AssertionError(
                f"Missing columns: {missing_columns}"
            )

        print("STATUS : PASS")
        print("SQLite integrity : OK")
        print(f"Tables checked   : {len(required)}")

        RESULTS.append((name, "PASS", None))
        return True

    except Exception as exc:
        print("STATUS : FAIL")
        print(f"{type(exc).__name__}: {exc}")
        RESULTS.append((name, "FAIL", None))
        return False


def learning_contract():
    name = "LEARNING DATA GATE"

    print(f"\n{'-' * 70}")
    print(f"TRACK: {name}")

    try:
        conn = sqlite3.connect(DB_PATH)

        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table'"
            )
        }

        if "learning_history" not in tables:
            raise AssertionError(
                "learning_history table is missing"
            )

        count = conn.execute(
            "SELECT COUNT(*) FROM learning_history"
        ).fetchone()[0]

        conn.close()

        if count == 0:
            print("STATUS : DATA-GATED")
            print("learning_history rows : 0")
            print(
                "This is a valid data-gated state, "
                "not a software failure."
            )
            RESULTS.append((name, "PASS", None))
            return True

        print("STATUS : PASS")
        print(f"learning_history rows : {count}")

        RESULTS.append((name, "PASS", None))
        return True

    except Exception as exc:
        print("STATUS : FAIL")
        print(f"{type(exc).__name__}: {exc}")
        RESULTS.append((name, "FAIL", None))
        return False


def main():
    print("=" * 70)
    print("MARKETBOT — REPOSITORY STABILITY VALIDATION")
    print("=" * 70)
    print(f"ROOT: {ROOT}")

    compile_all()
    import_audit()
    feature_engine_contract()
    database_contract()
    learning_contract()

    command_tracks = [
        (
            "PCR CONTRACT",
            ["python", "-m",
             "tests.test_pcr_engine_contract"],
        ),
        (
            "MAX PAIN CONTRACT",
            ["python", "-m",
             "tests.test_max_pain_engine_contract"],
        ),
        (
            "OI REGRESSION CONTRACT",
            ["python", "-m",
             "tests.test_oi_engine_contract"],
        ),
        (
            "OPTION INTELLIGENCE CONTRACT",
            ["python", "option_intelligence_test.py"],
        ),
        (
            "FORWARD RETURNS",
            ["python", "-m",
             "research.forward_returns"],
        ),
        (
            "FACTOR RESEARCH",
            ["python", "-m",
             "research.factor_research"],
        ),
        (
            "WALK FORWARD",
            ["python", "-m",
             "research.walk_forward"],
        ),
        (
            "FACTOR PERFORMANCE",
            ["python", "-m",
             "research.factor_performance"],
        ),
        (
            "WEIGHT RESEARCH",
            ["python", "-m",
             "learning.weight_optimizer"],
        ),
    ]

    for name, command in command_tracks:
        run_command(name, command)

    print("\n" + "=" * 70)
    print("FINAL MARKETBOT STABILITY REPORT")
    print("=" * 70)

    passed = sum(
        1 for _, status, _ in RESULTS
        if status == "PASS"
    )

    failed = sum(
        1 for _, status, _ in RESULTS
        if status == "FAIL"
    )

    for name, status, log in RESULTS:
        print(f"{name:<35} {status}")

    print("-" * 70)
    print(f"PASS : {passed}")
    print(f"FAIL : {failed}")

    if failed:
        print("STATUS : FAIL")
        print(
            "ACTION : Fix ONLY the failed tracks "
            "listed above."
        )
        return 1

    print("STATUS : PASS")
    print("ACTION : All configured stability tracks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
