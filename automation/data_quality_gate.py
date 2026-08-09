from __future__ import annotations

"""MarketBot daily data quality gate.

Read-only validation. It never repairs or mutates data. A non-zero exit code
means downstream analytics should not be trusted for that run.
"""

import argparse
import json
import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


@dataclass
class Check:
    name: str
    passed: bool
    message: str
    value: Any = None


def _scalar(conn, sql: str):
    return conn.execute(sql).fetchone()[0]


def run_checks(db_path: Path, expected_stock_count: int = 49, tolerance: int = 1) -> list[Check]:
    conn = sqlite3.connect(str(db_path))
    checks: list[Check] = []
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        required = ["stocks_daily", "indices_daily", "fii_dii_daily", "prediction_history", "prediction_outcomes", "factor_history"]
        for table in required:
            checks.append(Check(f"table:{table}", table in tables, "present" if table in tables else "missing"))

        if "stocks_daily" in tables:
            latest = _scalar(conn, "SELECT MAX(trade_date) FROM stocks_daily")
            count = _scalar(conn, "SELECT COUNT(DISTINCT symbol) FROM stocks_daily WHERE trade_date=(SELECT MAX(trade_date) FROM stocks_daily)")
            dup = _scalar(conn, "SELECT COUNT(*) FROM (SELECT trade_date, symbol, COUNT(*) c FROM stocks_daily GROUP BY trade_date, symbol HAVING c > 1)")
            bad_ohlc = _scalar(conn, "SELECT COUNT(*) FROM stocks_daily WHERE open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL")
            checks += [
                Check("stocks:latest_date", latest is not None, f"latest={latest}", latest),
                Check("stocks:universe", abs(int(count) - expected_stock_count) <= tolerance, f"latest-day symbols={count}", int(count)),
                Check("stocks:duplicates", int(dup) == 0, f"duplicate groups={dup}", int(dup)),
                Check("stocks:ohlc", int(bad_ohlc) == 0, f"bad OHLC rows={bad_ohlc}", int(bad_ohlc)),
            ]

        if "indices_daily" in tables:
            latest = _scalar(conn, "SELECT MAX(trade_date) FROM indices_daily")
            rows = pd.read_sql_query(
                """
                SELECT index_name, COUNT(*) AS n
                FROM indices_daily
                WHERE trade_date=(SELECT MAX(trade_date) FROM indices_daily)
                GROUP BY index_name
                """,
                conn,
            )
            required_indices = {"NIFTY50", "SENSEX", "BANKNIFTY"}
            found = set(rows["index_name"].astype(str))
            checks += [
                Check("indices:latest_date", latest is not None, f"latest={latest}", latest),
                Check("indices:core_universe", required_indices.issubset(found), f"found={sorted(found)}", sorted(found)),
            ]

        if "fii_dii_daily" in tables:
            latest = _scalar(conn, "SELECT MAX(trade_date) FROM fii_dii_daily")
            checks.append(Check("fii_dii:latest_date", latest is not None, f"latest={latest}", latest))

        if "factor_history" in tables:
            latest = _scalar(conn, "SELECT MAX(trade_date) FROM factor_history")
            checks.append(Check("factors:latest_date", latest is not None, f"latest={latest}", latest))

        if "prediction_history" in tables:
            latest = _scalar(conn, "SELECT MAX(trade_date) FROM prediction_history")
            checks.append(Check("predictions:latest_date", latest is not None, f"latest={latest}", latest))

        if "prediction_outcomes" in tables:
            latest = _scalar(conn, "SELECT MAX(prediction_date) FROM prediction_outcomes")
            checks.append(Check("outcomes:latest_date", latest is not None, f"latest={latest}", latest))
    finally:
        conn.close()
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the read-only MarketBot data quality gate")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--expected-stocks", type=int, default=49)
    args = parser.parse_args()
    checks = run_checks(args.db, args.expected_stocks)
    payload = {"passed": all(c.passed for c in checks), "checks": [asdict(c) for c in checks]}
    print(json.dumps(payload, indent=2, default=str))
    raise SystemExit(0 if payload["passed"] else 1)


if __name__ == "__main__":
    main()
