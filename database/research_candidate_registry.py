from __future__ import annotations

"""Research candidate registry.

Stores candidate metadata/results without touching production scoring. This is
our first step toward a champion/challenger workflow.
"""

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS research_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    decision TEXT NOT NULL,
    average_spread REAL,
    median_spread REAL,
    positive_window_pct REAL,
    worst_window REAL,
    windows INTEGER,
    artifact_path TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(candidate_name, model_version)
)
"""


def register(db_path: Path, candidate_name: str, model_version: str, gate_result: dict, artifact_path: str | None = None) -> None:
    metrics = gate_result.get("metrics", {})
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(SCHEMA)
        conn.execute(
            """
            INSERT OR REPLACE INTO research_candidates
            (candidate_name, model_version, decision, average_spread,
             median_spread, positive_window_pct, worst_window, windows,
             artifact_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate_name,
                model_version,
                gate_result.get("decision", "UNKNOWN"),
                metrics.get("average_spread"),
                metrics.get("median_spread"),
                metrics.get("positive_window_pct"),
                metrics.get("worst_window"),
                metrics.get("windows"),
                artifact_path,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Register a MarketBot research candidate")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--name", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--gate-json", type=Path, required=True)
    parser.add_argument("--artifact", default=None)
    args = parser.parse_args()
    gate = json.loads(args.gate_json.read_text(encoding="utf-8"))
    register(args.db, args.name, args.version, gate, args.artifact)
    print(f"Registered research candidate: {args.name} {args.version} [{gate.get('decision')}]")


if __name__ == "__main__":
    main()
