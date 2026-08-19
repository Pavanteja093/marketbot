from __future__ import annotations

import argparse
import csv
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = PROJECT_ROOT / "market_intelligence.db"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "research" / "artifacts" / "marketbot_health_report.csv"
)


@dataclass(frozen=True)
class TableSpec:
    name: str
    date_column: str | None
    critical_columns: tuple[str, ...]
    duplicate_key: tuple[str, ...] | None
    required: bool = True


TABLE_SPECS = (
    TableSpec(
        "indices_daily",
        "trade_date",
        ("trade_date", "index_name", "close"),
        ("trade_date", "index_name"),
    ),
    TableSpec(
        "stocks_daily",
        "trade_date",
        ("trade_date", "symbol", "close"),
        ("trade_date", "symbol"),
    ),
    TableSpec(
        "fii_dii_daily",
        "trade_date",
        ("trade_date", "fii_net", "dii_net"),
        ("trade_date",),
    ),
    TableSpec(
        "factor_history",
        "trade_date",
        ("trade_date", "index_name", "intelligence_score"),
        ("trade_date", "index_name", "sector"),
    ),
    TableSpec(
        "signal_history",
        "trade_date",
        ("trade_date", "index_name", "score"),
        ("trade_date", "index_name", "sector"),
    ),
    TableSpec(
        "signal_history_v2",
        "trade_date",
        ("trade_date", "index_name", "intelligence_score"),
        ("trade_date", "index_name", "sector"),
    ),
    TableSpec(
        "market_regime",
        "trade_date",
        ("trade_date", "market_regime", "regime_score"),
        ("trade_date",),
    ),
    TableSpec(
        "market_scenario_history",
        "trade_date",
        (
            "trade_date",
            "index_name",
            "primary_scenario",
            "scenario_id",
            "fingerprint",
        ),
        ("trade_date", "index_name"),
    ),
    TableSpec(
        "options_summary",
        "trade_date",
        ("trade_date", "index_name", "spot_price"),
        ("trade_date", "index_name"),
    ),
    TableSpec(
        "indices_intraday",
        "timestamp",
        ("timestamp", "index_name", "close"),
        None,
        required=False,
    ),
    TableSpec(
        "option_chain_history",
        "trade_time",
        ("trade_time", "symbol", "expiry", "strike"),
        None,
        required=False,
    ),
)


@dataclass
class TableHealth:
    table_name: str
    required: bool
    exists: bool
    row_count: int
    latest_value: str | None
    null_issues: int
    duplicate_groups: int
    status: str
    reason: str


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def connect_read_only(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def get_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(
        f"PRAGMA table_info({quote_identifier(table_name)})"
    ).fetchall()
    return {row[1] for row in rows}


def count_rows(conn: sqlite3.Connection, table_name: str) -> int:
    return int(
        conn.execute(
            f"SELECT COUNT(*) FROM {quote_identifier(table_name)}"
        ).fetchone()[0]
    )


def latest_value(
    conn: sqlite3.Connection,
    table_name: str,
    date_column: str | None,
) -> str | None:
    if not date_column:
        return None

    row = conn.execute(
        f"""
        SELECT MAX({quote_identifier(date_column)})
        FROM {quote_identifier(table_name)}
        """
    ).fetchone()

    return None if row is None or row[0] is None else str(row[0])


def count_null_issues(
    conn: sqlite3.Connection,
    table_name: str,
    columns: Iterable[str],
) -> int:
    columns = list(columns)

    if not columns:
        return 0

    expressions = [
        f"SUM(CASE WHEN {quote_identifier(column)} IS NULL THEN 1 ELSE 0 END)"
        for column in columns
    ]

    row = conn.execute(
        f"""
        SELECT {", ".join(expressions)}
        FROM {quote_identifier(table_name)}
        """
    ).fetchone()

    return int(sum(value or 0 for value in row))


def count_duplicate_groups(
    conn: sqlite3.Connection,
    table_name: str,
    key_columns: tuple[str, ...] | None,
) -> int:
    if not key_columns:
        return 0

    quoted = ", ".join(quote_identifier(column) for column in key_columns)

    row = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM (
            SELECT {quoted}
            FROM {quote_identifier(table_name)}
            GROUP BY {quoted}
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()

    return int(row[0])


def assess_status(
    *,
    required: bool,
    exists: bool,
    row_count: int,
    null_issues: int,
    duplicate_groups: int,
) -> tuple[str, str]:
    if not exists:
        if required:
            return "CRITICAL", "Required table is missing."
        return "WARNING", "Optional table is missing."

    if row_count == 0:
        if required:
            return "CRITICAL", "Required table is empty."
        return "WARNING", "Optional table is empty."

    if duplicate_groups > 0:
        return "WARNING", f"{duplicate_groups} duplicate key group(s) detected."

    if null_issues > 0:
        return "WARNING", f"{null_issues} NULL value(s) in critical columns."

    return "HEALTHY", "No configured integrity issues detected."


def inspect_table(
    conn: sqlite3.Connection,
    spec: TableSpec,
) -> TableHealth:
    if not table_exists(conn, spec.name):
        status, reason = assess_status(
            required=spec.required,
            exists=False,
            row_count=0,
            null_issues=0,
            duplicate_groups=0,
        )
        return TableHealth(
            spec.name,
            spec.required,
            False,
            0,
            None,
            0,
            0,
            status,
            reason,
        )

    actual_columns = get_columns(conn, spec.name)

    missing_columns = [
        column
        for column in spec.critical_columns
        if column not in actual_columns
    ]

    if spec.date_column and spec.date_column not in actual_columns:
        missing_columns.append(spec.date_column)

    if spec.duplicate_key:
        missing_columns.extend(
            column
            for column in spec.duplicate_key
            if column not in actual_columns
        )

    missing_columns = sorted(set(missing_columns))

    if missing_columns:
        return TableHealth(
            spec.name,
            spec.required,
            True,
            count_rows(conn, spec.name),
            None,
            0,
            0,
            "CRITICAL" if spec.required else "WARNING",
            "Schema mismatch; missing columns: "
            + ", ".join(missing_columns),
        )

    rows = count_rows(conn, spec.name)
    latest = latest_value(conn, spec.name, spec.date_column)
    nulls = count_null_issues(conn, spec.name, spec.critical_columns)
    duplicates = count_duplicate_groups(
        conn,
        spec.name,
        spec.duplicate_key,
    )

    status, reason = assess_status(
        required=spec.required,
        exists=True,
        row_count=rows,
        null_issues=nulls,
        duplicate_groups=duplicates,
    )

    return TableHealth(
        spec.name,
        spec.required,
        True,
        rows,
        latest,
        nulls,
        duplicates,
        status,
        reason,
    )


def latest_market_date(
    conn: sqlite3.Connection,
) -> str | None:
    if not table_exists(conn, "indices_daily"):
        return None

    row = conn.execute(
        """
        SELECT MAX(trade_date)
        FROM indices_daily
        """
    ).fetchone()

    return None if row is None or row[0] is None else str(row[0])


def assess_freshness(
    health_rows: list[TableHealth],
    reference_date: str | None,
) -> list[TableHealth]:
    if reference_date is None:
        return health_rows

    result = []

    freshness_tables = {
        "stocks_daily",
        "fii_dii_daily",
        "factor_history",
        "signal_history",
        "signal_history_v2",
        "market_regime",
        "market_scenario_history",
        "options_summary",
    }

    for row in health_rows:
        if row.table_name not in freshness_tables:
            result.append(row)
            continue

        if not row.exists or row.latest_value is None:
            result.append(row)
            continue

        if row.latest_value[:10] != reference_date[:10]:
            if row.status == "HEALTHY":
                row = TableHealth(
                    row.table_name,
                    row.required,
                    row.exists,
                    row.row_count,
                    row.latest_value,
                    row.null_issues,
                    row.duplicate_groups,
                    "WARNING",
                    (
                        f"Latest date {row.latest_value[:10]} "
                        f"does not match reference market date "
                        f"{reference_date[:10]}."
                    ),
                )

        result.append(row)

    return result


def overall_status(rows: list[TableHealth]) -> str:
    statuses = {row.status for row in rows}

    if "CRITICAL" in statuses:
        return "CRITICAL"

    if "WARNING" in statuses:
        return "WARNING"

    return "HEALTHY"


def build_report(
    conn: sqlite3.Connection,
) -> tuple[list[TableHealth], str | None, str]:
    rows = [
        inspect_table(conn, spec)
        for spec in TABLE_SPECS
    ]

    reference = latest_market_date(conn)
    rows = assess_freshness(rows, reference)

    return rows, reference, overall_status(rows)


def write_report(
    rows: list[TableHealth],
    reference_date: str | None,
    overall: str,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "table_name",
        "required",
        "exists",
        "row_count",
        "latest_value",
        "reference_market_date",
        "null_issues",
        "duplicate_groups",
        "status",
        "reason",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    "table_name": row.table_name,
                    "required": row.required,
                    "exists": row.exists,
                    "row_count": row.row_count,
                    "latest_value": row.latest_value or "",
                    "reference_market_date": reference_date or "",
                    "null_issues": row.null_issues,
                    "duplicate_groups": row.duplicate_groups,
                    "status": row.status,
                    "reason": row.reason,
                }
            )


def print_report(
    rows: list[TableHealth],
    reference_date: str | None,
    overall: str,
    output_path: Path,
) -> None:
    healthy = sum(row.status == "HEALTHY" for row in rows)
    warnings = sum(row.status == "WARNING" for row in rows)
    critical = sum(row.status == "CRITICAL" for row in rows)

    print("=" * 80)
    print("MARKETBOT - SYSTEM HEALTH MONITOR")
    print("=" * 80)

    print(f"Database status       : READ-ONLY")
    print(f"Reference market date : {reference_date or 'UNAVAILABLE'}")
    print()

    print("TABLE HEALTH")
    print("-" * 80)

    for row in rows:
        print(
            f"{row.table_name:<28} "
            f"{row.status:<9} "
            f"rows={row.row_count:<8} "
            f"latest={row.latest_value or '-'}"
        )

    print()
    print("HEALTH SUMMARY")
    print("-" * 80)
    print(f"Tables checked        : {len(rows)}")
    print(f"Healthy               : {healthy}")
    print(f"Warnings              : {warnings}")
    print(f"Critical              : {critical}")
    print(f"OVERALL STATUS        : {overall}")
    print()
    print(f"Saved: {output_path}")
    print()
    print(
        "READ-ONLY: no SQLite INSERT, UPDATE, DELETE, ALTER, or DROP "
        "operations were performed."
    )


def run(
    db_path: Path = DEFAULT_DB,
    output_path: Path = DEFAULT_OUTPUT,
) -> dict:
    if not db_path.exists():
        raise FileNotFoundError(
            f"MarketBot database not found: {db_path}"
        )

    conn = connect_read_only(db_path)

    try:
        rows, reference, overall = build_report(conn)
    finally:
        conn.close()

    write_report(rows, reference, overall, output_path)

    print_report(rows, reference, overall, output_path)

    return {
        "rows": rows,
        "reference_market_date": reference,
        "overall_status": overall,
        "output_path": output_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only MarketBot database health monitor."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    args = parser.parse_args()

    run(
        db_path=args.db,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()