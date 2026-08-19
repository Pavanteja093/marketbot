from __future__ import annotations

"""
MarketBot Market Scenario Registry

Purpose
-------
Create a small, deterministic historical registry of market environments.

This module:
- reads indices_daily
- uses index_name, not symbol
- derives daily market-state features
- classifies broad scenarios
- creates deterministic fingerprints
- assigns persistent scenario IDs
- stores historical observations in market_scenario_history

Current standard scenarios:
    TREND_UP
    TREND_DOWN
    HIGH_VOL
    LOW_VOL
    FLAT
    CHOPPY

Research / infrastructure only.
It does not modify production scoring, factor weights, Track B,
Track C, or trading decisions.
"""

import argparse
import hashlib
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = BASE_DIR / "market_intelligence.db"

TABLE_NAME = "market_scenario_history"

STANDARD_SCENARIOS = (
    "TREND_UP",
    "TREND_DOWN",
    "HIGH_VOL",
    "LOW_VOL",
    "FLAT",
    "CHOPPY",
)

REQUIRED_INDEX_COLUMNS = {
    "trade_date",
    "index_name",
    "open",
    "high",
    "low",
    "close",
    "change_pct",
}


def classify_scenario(
    trend: float,
    volatility: float,
    daily_return: float,
    range_pct: float,
) -> str:
    """
    Classify a daily market environment.

    Priority:
        1. HIGH_VOL
        2. TREND_UP
        3. TREND_DOWN
        4. FLAT
        5. LOW_VOL
        6. CHOPPY

    LOW_VOL represents a genuinely compressed-volatility environment,
    but does not override directional, flat, or choppy classifications.
    """

    if pd.isna(trend) or pd.isna(volatility):
        return "FLAT"

    # High volatility takes priority.
    if volatility >= 0.018:
        return "HIGH_VOL"

    # Strong directional movement.
    if trend >= 0.006:
        return "TREND_UP"

    if trend <= -0.006:
        return "TREND_DOWN"

    # Very small movement and compressed range.
    if (
        abs(daily_return) <= 0.002
        and range_pct <= 0.006
    ):
        return "FLAT"

    # Low-volatility, compressed but non-flat environment.
    if (
        volatility <= 0.006
        and range_pct <= 0.008
    ):
        return "LOW_VOL"

    # Remaining non-directional movement.
    return "CHOPPY"


def make_fingerprint(
    primary_scenario: str,
    trend_bucket: str,
    volatility_bucket: str,
    return_bucket: str,
    range_bucket: str,
) -> str:
    """
    Create a deterministic fingerprint for a market environment.
    """

    raw = "|".join(
        [
            primary_scenario,
            trend_bucket,
            volatility_bucket,
            return_bucket,
            range_bucket,
        ]
    )

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _bucket(value: float, thresholds: tuple[float, ...]) -> str:
    if pd.isna(value):
        return "NA"

    if value < thresholds[0]:
        return "LOW"

    if len(thresholds) == 1 or value < thresholds[1]:
        return "NORMAL"

    return "HIGH"


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date DATE NOT NULL,
            index_name TEXT NOT NULL,
            primary_scenario TEXT NOT NULL,
            scenario_id TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            trend REAL,
            volatility REAL,
            daily_return REAL,
            range_pct REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(trade_date, index_name)
        )
        """
    )

    conn.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_date
        ON {TABLE_NAME}(trade_date)
        """
    )

    conn.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_fingerprint
        ON {TABLE_NAME}(fingerprint)
        """
    )


def _validate_schema(conn: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(indices_daily)")
    }

    missing = REQUIRED_INDEX_COLUMNS - columns

    if missing:
        raise RuntimeError(
            "indices_daily is missing required columns: "
            + ", ".join(sorted(missing))
        )


def _load_nifty(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Load NIFTY50 history.

    The actual MarketBot schema uses index_name.
    """

    query = """
        SELECT
            trade_date,
            index_name,
            open,
            high,
            low,
            close,
            change_pct
        FROM indices_daily
        WHERE UPPER(TRIM(index_name)) IN (
            'NIFTY50',
            'NIFTY 50',
            'NIFTY'
        )
        ORDER BY trade_date
    """

    df = pd.read_sql_query(query, conn)

    if df.empty:
        raise RuntimeError(
            "No NIFTY observations found in indices_daily."
        )

    df["trade_date"] = pd.to_datetime(
        df["trade_date"],
        errors="coerce",
    )

    for column in (
        "open",
        "high",
        "low",
        "close",
        "change_pct",
    ):
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df = (
        df.dropna(
            subset=[
                "trade_date",
                "open",
                "high",
                "low",
                "close",
            ]
        )
        .drop_duplicates("trade_date")
        .sort_values("trade_date")
        .reset_index(drop=True)
    )

    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build leakage-safe daily market-state features.

    All features use information available on the same historical day.
    """

    x = df.copy(deep=True)

    x["daily_return"] = x["close"].pct_change()

    x["trend"] = (
        x["close"].pct_change(5)
    )

    x["volatility"] = (
        x["daily_return"]
        .rolling(20, min_periods=20)
        .std()
    )

    x["range_pct"] = (
        (x["high"] - x["low"])
        / x["close"].replace(0, np.nan)
    )

    return x


def build_scenarios(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert daily features into scenario observations.
    """

    x = build_features(df)

    records = []

    for _, row in x.iterrows():
        scenario = classify_scenario(
            trend=row["trend"],
            volatility=row["volatility"],
            daily_return=row["daily_return"],
            range_pct=row["range_pct"],
        )

        trend_bucket = _bucket(
            row["trend"],
            (-0.006, 0.006),
        )

        volatility_bucket = _bucket(
            row["volatility"],
            (0.010, 0.018),
        )

        return_bucket = _bucket(
            abs(row["daily_return"]),
            (0.002, 0.010),
        )

        range_bucket = _bucket(
            row["range_pct"],
            (0.006, 0.015),
        )

        fingerprint = make_fingerprint(
            scenario,
            trend_bucket,
            volatility_bucket,
            return_bucket,
            range_bucket,
        )

        records.append(
            {
                "trade_date": row["trade_date"],
                "index_name": "NIFTY50",
                "primary_scenario": scenario,
                "fingerprint": fingerprint,
                "trend": row["trend"],
                "volatility": row["volatility"],
                "daily_return": row["daily_return"],
                "range_pct": row["range_pct"],
            }
        )

    return pd.DataFrame(records)


def _existing_scenario_ids(
    conn: sqlite3.Connection,
) -> dict[str, str]:
    rows = conn.execute(
        f"""
        SELECT fingerprint, scenario_id
        FROM {TABLE_NAME}
        GROUP BY fingerprint, scenario_id
        """
    ).fetchall()

    return {
        fingerprint: scenario_id
        for fingerprint, scenario_id in rows
    }


def _next_unexplored_id(
    used_ids: set[str],
) -> str:
    number = 1

    while f"UNEXPLORED_{number}" in used_ids:
        number += 1

    return f"UNEXPLORED_{number}"


def assign_scenario_ids(
    conn: sqlite3.Connection,
    scenarios: pd.DataFrame,
) -> pd.DataFrame:
    """
    Persistently assign IDs.

    Same fingerprint:
        same scenario_id

    New fingerprint:
        next UNEXPLORED_N
    """

    x = scenarios.copy(deep=True)

    fingerprint_to_id = _existing_scenario_ids(conn)
    used_ids = set(fingerprint_to_id.values())

    assigned = []

    for fingerprint in x["fingerprint"]:
        if fingerprint in fingerprint_to_id:
            scenario_id = fingerprint_to_id[fingerprint]
        else:
            scenario_id = _next_unexplored_id(used_ids)

            fingerprint_to_id[fingerprint] = scenario_id
            used_ids.add(scenario_id)

        assigned.append(scenario_id)

    x["scenario_id"] = assigned

    return x


def write_scenarios(
    conn: sqlite3.Connection,
    scenarios: pd.DataFrame,
) -> int:
    """
    Insert scenario observations idempotently.

    Existing historical rows are never deleted or rewritten.
    """

    if scenarios.empty:
        return 0

    inserted = 0

    for _, row in scenarios.iterrows():
        cursor = conn.execute(
            f"""
            INSERT OR IGNORE INTO {TABLE_NAME} (
                trade_date,
                index_name,
                primary_scenario,
                scenario_id,
                fingerprint,
                trend,
                volatility,
                daily_return,
                range_pct
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["trade_date"].strftime("%Y-%m-%d"),
                row["index_name"],
                row["primary_scenario"],
                row["scenario_id"],
                row["fingerprint"],
                None if pd.isna(row["trend"]) else float(row["trend"]),
                None
                if pd.isna(row["volatility"])
                else float(row["volatility"]),
                None
                if pd.isna(row["daily_return"])
                else float(row["daily_return"]),
                None
                if pd.isna(row["range_pct"])
                else float(row["range_pct"]),
            ),
        )

        inserted += cursor.rowcount

    conn.commit()

    return inserted


def run(db_path: str | Path = DEFAULT_DB) -> dict:
    db_path = Path(db_path).resolve()

    conn = sqlite3.connect(str(db_path))

    try:
        _validate_schema(conn)
        _ensure_table(conn)

        raw = _load_nifty(conn)
        scenarios = build_scenarios(raw)

        scenarios = assign_scenario_ids(
            conn,
            scenarios,
        )

        inserted = write_scenarios(
            conn,
            scenarios,
        )

        return {
            "source_rows": int(len(raw)),
            "scenario_rows_generated": int(len(scenarios)),
            "rows_inserted": int(inserted),
            "date_min": (
                scenarios["trade_date"].min().strftime("%Y-%m-%d")
                if not scenarios.empty
                else None
            ),
            "date_max": (
                scenarios["trade_date"].max().strftime("%Y-%m-%d")
                if not scenarios.empty
                else None
            ),
            "scenario_distribution": (
                scenarios["primary_scenario"]
                .value_counts()
                .sort_index()
                .to_dict()
                if not scenarios.empty
                else {}
            ),
        }

    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
    )

    args = parser.parse_args()

    result = run(args.db)

    print("\n" + "=" * 70)
    print("MARKETBOT - MARKET SCENARIO REGISTRY")
    print("=" * 70)

    print(
        f"Source rows            : {result['source_rows']}"
    )
    print(
        f"Scenario rows generated: {result['scenario_rows_generated']}"
    )
    print(
        f"Rows inserted           : {result['rows_inserted']}"
    )
    print(
        f"Date range              : "
        f"{result['date_min']} -> {result['date_max']}"
    )

    print("\nSCENARIO DISTRIBUTION")

    for scenario, count in result[
        "scenario_distribution"
    ].items():
        print(f"{scenario:<15} {count}")

    print(
        "\nProduction scoring, weights, Track B, Track C "
        "and live trading were NOT changed."
    )


if __name__ == "__main__":
    main()