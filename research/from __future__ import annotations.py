from __future__ import annotations

"""
MarketBot - Rebuild Market Scenario History

Purpose
-------
Rebuild the derived market_scenario_history table from the current
Scenario Registry logic.

Safety rules
------------
- indices_daily is read-only.
- Existing fingerprint -> scenario_id mappings are preserved.
- New fingerprints receive new UNEXPLORED_N IDs.
- The rebuild is transactional.
- On failure, the original scenario history remains intact.
- Production scoring, Track A, Track B, Track C and trading are untouched.
"""

import argparse
import re
import sqlite3
from pathlib import Path

import pandas as pd

from research.market_scenario_registry import (
    TABLE_NAME,
    _ensure_table,
    _load_nifty,
    _validate_schema,
    assign_scenario_ids,
    build_scenarios,
)


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = BASE_DIR / "market_intelligence.db"


def _existing_id_map(
    conn: sqlite3.Connection,
) -> tuple[dict[str, str], int]:
    """
    Capture existing fingerprint -> scenario_id mappings.

    Returns
    -------
    mapping:
        fingerprint -> existing scenario_id

    max_id:
        Highest numeric UNEXPLORED_N ID currently present.
    """

    rows = conn.execute(
        f"""
        SELECT fingerprint, scenario_id
        FROM {TABLE_NAME}
        WHERE fingerprint IS NOT NULL
          AND scenario_id IS NOT NULL
        """
    ).fetchall()

    mapping: dict[str, str] = {}
    max_id = 0

    for fingerprint, scenario_id in rows:
        mapping[str(fingerprint)] = str(scenario_id)

        match = re.fullmatch(r"UNEXPLORED_(\d+)", str(scenario_id))
        if match:
            max_id = max(max_id, int(match.group(1)))

    return mapping, max_id


def _assign_preserving_existing_ids(
    frame: pd.DataFrame,
    existing_map: dict[str, str],
    starting_id: int,
) -> pd.DataFrame:
    """
    Assign scenario IDs while preserving historical fingerprint mappings.

    A fingerprint that existed before keeps its original scenario ID.

    A genuinely new fingerprint receives the next available
    UNEXPLORED_N identifier.
    """

    result = frame.copy()

    used_ids = set(existing_map.values())
    next_id = starting_id + 1

    assigned: list[str] = []

    for fingerprint in result["fingerprint"].astype(str):
        if fingerprint in existing_map:
            assigned.append(existing_map[fingerprint])
            continue

        while f"UNEXPLORED_{next_id}" in used_ids:
            next_id += 1

        scenario_id = f"UNEXPLORED_{next_id}"

        used_ids.add(scenario_id)
        existing_map[fingerprint] = scenario_id

        assigned.append(scenario_id)
        next_id += 1

    result["scenario_id"] = assigned

    return result


def _insert_rows(
    conn: sqlite3.Connection,
    frame: pd.DataFrame,
) -> int:
    """
    Insert the rebuilt scenario history.
    """

    columns = [
        "trade_date",
        "index_name",
        "primary_scenario",
        "scenario_id",
        "fingerprint",
        "trend",
        "volatility",
        "daily_return",
        "range_pct",
    ]

    rows = [
        tuple(row[column] for column in columns)
        for _, row in frame.iterrows()
    ]

    conn.executemany(
        f"""
        INSERT INTO {TABLE_NAME}
        (
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
        rows,
    )

    return len(rows)


def rebuild(db_path: Path = DEFAULT_DB) -> dict:
    """
    Transactionally rebuild market_scenario_history.

    The existing fingerprint -> scenario_id mapping is preserved.
    """

    db_path = Path(db_path)

    conn = sqlite3.connect(str(db_path))

    try:
        _ensure_table(conn)
        _validate_schema(conn)

        existing_map, max_existing_id = _existing_id_map(conn)

        source = _load_nifty(conn)

        if source.empty:
            raise RuntimeError(
                "No NIFTY50 rows found in indices_daily."
            )

        scenarios = build_scenarios(source)

        if scenarios.empty:
            raise RuntimeError(
                "Scenario Registry produced no observations."
            )

        rebuilt = _assign_preserving_existing_ids(
            scenarios,
            existing_map,
            max_existing_id,
        )

        expected_rows = len(rebuilt)

        # Everything below is one transaction.
        conn.execute("BEGIN")

        conn.execute(f"DELETE FROM {TABLE_NAME}")

        inserted_rows = _insert_rows(
            conn,
            rebuilt,
        )

        if inserted_rows != expected_rows:
            raise RuntimeError(
                f"Row-count mismatch during rebuild: "
                f"expected {expected_rows}, inserted {inserted_rows}"
            )

        conn.commit()

        distribution = (
            rebuilt["primary_scenario"]
            .value_counts()
            .sort_index()
            .to_dict()
        )

        unique_fingerprints = int(
            rebuilt["fingerprint"].nunique()
        )

        unique_ids = int(
            rebuilt["scenario_id"].nunique()
        )

        return {
            "source_rows": int(len(source)),
            "scenario_rows": int(len(rebuilt)),
            "rows_inserted": int(inserted_rows),
            "unique_fingerprints": unique_fingerprints,
            "unique_scenario_ids": unique_ids,
            "distribution": {
                str(k): int(v)
                for k, v in distribution.items()
            },
            "date_min": str(
                pd.to_datetime(
                    rebuilt["trade_date"]
                ).min().date()
            ),
            "date_max": str(
                pd.to_datetime(
                    rebuilt["trade_date"]
                ).max().date()
            ),
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild MarketBot market scenario history."
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help="Path to market_intelligence.db",
    )

    args = parser.parse_args()

    result = rebuild(args.db)

    print("=" * 72)
    print("MARKETBOT - MARKET SCENARIO HISTORY REBUILD")
    print("=" * 72)

    print(f"Source rows            : {result['source_rows']}")
    print(f"Scenario rows generated: {result['scenario_rows']}")
    print(f"Rows inserted           : {result['rows_inserted']}")
    print(f"Unique fingerprints     : {result['unique_fingerprints']}")
    print(f"Unique scenario IDs     : {result['unique_scenario_ids']}")
    print(
        f"Date range              : "
        f"{result['date_min']} -> {result['date_max']}"
    )

    print()
    print("SCENARIO DISTRIBUTION")

    for scenario, count in result["distribution"].items():
        print(f"{scenario:<16}{count}")

    print()
    print(
        "Existing fingerprint -> scenario_id mappings were preserved."
    )
    print(
        "Production scoring, weights, Track A, Track B, Track C "
        "and live trading were NOT changed."
    )


if __name__ == "__main__":
    main()