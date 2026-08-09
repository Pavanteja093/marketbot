from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "market_intelligence.db"

REQUIRED_STOCK_TABLES = ("prediction_history", "prediction_outcomes")

DATE_ALIASES = {
    "prediction_history": ("trade_date", "prediction_date", "date"),
    "prediction_outcomes": ("prediction_date", "trade_date", "date"),
}
ENTITY_ALIASES = ("index_name", "symbol", "ticker")
RANK_ALIASES = ("rank", "prediction_rank")


class ContractError(RuntimeError):
    """A database/schema contract failure that makes Track-A validation invalid."""


@dataclass
class Report:
    database: str
    prediction_history_rows: int = 0
    prediction_outcomes_rows: int = 0
    matched_outcome_rows: int = 0
    unmatched_prediction_rows: int = 0
    latest_prediction_date: Optional[str] = None
    latest_outcome_date: Optional[str] = None
    learning_history_rows: int = 0
    learning_history_reason: str = ""
    critical_errors: list[str] | None = None
    warnings: list[str] | None = None

    def __post_init__(self) -> None:
        self.critical_errors = [] if self.critical_errors is None else self.critical_errors
        self.warnings = [] if self.warnings is None else self.warnings

    @property
    def ok(self) -> bool:
        return not self.critical_errors


def connect(db: Path) -> sqlite3.Connection:
    db = Path(db)
    if not db.exists():
        raise ContractError(f"Database does not exist: {db}")
    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA schema_version").fetchone()
        return conn
    except sqlite3.DatabaseError as exc:
        raise ContractError(
            f"Unsupported or invalid SQLite database: {db} ({exc})"
        ) from exc


def tables(conn: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    }


def columns(conn: sqlite3.Connection, table: str) -> list[str]:
    if table not in tables(conn):
        raise ContractError(f"Required table is missing: {table}")
    return [row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')]


def resolve_column(
    conn: sqlite3.Connection,
    table: str,
    aliases: tuple[str, ...],
    label: str,
) -> str:
    actual = set(columns(conn, table))
    for name in aliases:
        if name in actual:
            return name
    raise ContractError(
        f"{table} has no recognizable {label} column; "
        f"expected one of: {', '.join(aliases)}"
    )


def require_stock_contract(conn: sqlite3.Connection) -> dict[str, str]:
    for table in REQUIRED_STOCK_TABLES:
        if table not in tables(conn):
            raise ContractError(f"Required table is missing: {table}")

    p_date = resolve_column(
        conn, "prediction_history", DATE_ALIASES["prediction_history"], "date"
    )
    o_date = resolve_column(
        conn, "prediction_outcomes", DATE_ALIASES["prediction_outcomes"], "date"
    )
    p_entity = resolve_column(
        conn, "prediction_history", ENTITY_ALIASES, "entity (index_name/symbol/ticker)"
    )
    o_entity = resolve_column(
        conn, "prediction_outcomes", ENTITY_ALIASES, "entity (index_name/symbol/ticker)"
    )
    p_rank = resolve_column(
        conn, "prediction_history", RANK_ALIASES, "rank"
    )
    o_rank = resolve_column(
        conn, "prediction_outcomes", RANK_ALIASES, "rank"
    )

    if "return_5d" not in columns(conn, "prediction_outcomes"):
        raise ContractError(
            "prediction_outcomes is missing required column: return_5d"
        )

    return {
        "p_date": p_date,
        "o_date": o_date,
        "p_entity": p_entity,
        "o_entity": o_entity,
        "p_rank": p_rank,
        "o_rank": o_rank,
    }


def stock_outcome_match(
    conn: sqlite3.Connection,
) -> tuple[int, int, int, int, Optional[str], Optional[str], int]:
    c = require_stock_contract(conn)

    total = conn.execute("SELECT COUNT(*) FROM prediction_history").fetchone()[0]
    outcomes = conn.execute("SELECT COUNT(*) FROM prediction_outcomes").fetchone()[0]

    p_date = f'p."{c["p_date"]}"'
    o_date = f'o."{c["o_date"]}"'
    p_entity = f'p."{c["p_entity"]}"'
    o_entity = f'o."{c["o_entity"]}"'
    p_rank = f'p."{c["p_rank"]}"'
    o_rank = f'o."{c["o_rank"]}"'

    matched = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM prediction_history p
        INNER JOIN prediction_outcomes o
          ON {p_date} = {o_date}
         AND {p_entity} = {o_entity}
         AND {p_rank} = {o_rank}
        """
    ).fetchone()[0]

    unmatched = total - matched
    latest_prediction = conn.execute(
        f'SELECT MAX("{c["p_date"]}") FROM prediction_history'
    ).fetchone()[0]
    latest_outcome = conn.execute(
        f'SELECT MAX("{c["o_date"]}") FROM prediction_outcomes'
    ).fetchone()[0]

    duplicates = conn.execute(
        f"""
        SELECT COUNT(*) FROM (
            SELECT "{c["o_date"]}", "{c["o_entity"]}", "{c["o_rank"]}"
            FROM prediction_outcomes
            GROUP BY "{c["o_date"]}", "{c["o_entity"]}", "{c["o_rank"]}"
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]

    return (
        total,
        outcomes,
        matched,
        unmatched,
        latest_prediction,
        latest_outcome,
        duplicates,
    )


def _safe_count(conn: sqlite3.Connection, table: str) -> int:
    if table not in tables(conn):
        return 0
    return conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]


def learning_status(conn: sqlite3.Connection) -> tuple[int, str]:
    if "learning_history" not in tables(conn):
        return 0, "learning_history table is absent; no market-direction learning rows can be recorded."

    count = _safe_count(conn, "learning_history")
    if count:
        return count, "learning_history contains market-direction learning records."

    reasons: list[str] = []

    for table, label in (
        ("direction_predictions", "direction_predictions"),
        ("market_prediction_history", "market_prediction_history"),
    ):
        if table not in tables(conn):
            reasons.append(f"{label} table is absent")
        elif _safe_count(conn, table) == 0:
            reasons.append(f"{label} has 0 rows")

    if "prediction" in columns(conn, "prediction_history"):
        nonnull = conn.execute(
            'SELECT COUNT(*) FROM prediction_history WHERE "prediction" IS NOT NULL'
        ).fetchone()[0]
        if nonnull == 0:
            reasons.append("prediction_history.prediction is NULL for all rows")
    else:
        reasons.append("prediction_history has no prediction column")

    return 0, (
        "learning_history is empty; no valid market-direction learning source "
        "records are currently available ("
        + "; ".join(reasons)
        + "). prediction_outcomes is stock-ranking data and is intentionally not "
          "copied into learning_history."
    )


def validate(db: Path) -> Report:
    report = Report(database=str(Path(db).resolve()))
    conn: sqlite3.Connection | None = None
    try:
        conn = connect(db)
        missing = sorted(set(REQUIRED_STOCK_TABLES) - tables(conn))
        if missing:
            report.critical_errors.append(
                "Missing required table(s): " + ", ".join(missing)
            )
            return report

        (
            report.prediction_history_rows,
            report.prediction_outcomes_rows,
            report.matched_outcome_rows,
            report.unmatched_prediction_rows,
            report.latest_prediction_date,
            report.latest_outcome_date,
            duplicate_outcomes,
        ) = stock_outcome_match(conn)

        if duplicate_outcomes:
            report.critical_errors.append(
                f"prediction_outcomes contains {duplicate_outcomes} duplicate "
                "(date, entity, rank) key group(s)."
            )

        report.learning_history_rows, report.learning_history_reason = learning_status(conn)

        if report.unmatched_prediction_rows:
            report.warnings.append(
                f"{report.unmatched_prediction_rows} prediction row(s) have no "
                "historical 5-day outcome yet. They are unresolved, not false outcomes."
            )

        if report.latest_prediction_date and report.latest_outcome_date:
            if report.latest_prediction_date > report.latest_outcome_date:
                report.warnings.append(
                    "Latest prediction date is newer than latest outcome date; "
                    "recent rows are expected to remain unresolved until 5-day outcomes exist."
                )
    except (sqlite3.DatabaseError, ContractError) as exc:
        report.critical_errors.append(str(exc))
    finally:
        if conn is not None:
            conn.close()
    return report


def print_report(r: Report) -> None:
    print("MARKETBOT TRACK-A VALIDATION")
    print("=" * 32)
    print(f"Database: {r.database}")
    print(f"prediction_history rows:  {r.prediction_history_rows}")
    print(f"prediction_outcomes rows: {r.prediction_outcomes_rows}")
    print(f"Matched outcome rows:     {r.matched_outcome_rows}")
    print(f"Unmatched predictions:     {r.unmatched_prediction_rows}")
    print(f"Latest prediction date:   {r.latest_prediction_date}")
    print(f"Latest outcome date:      {r.latest_outcome_date}")
    print(f"learning_history rows:    {r.learning_history_rows}")
    print(f"Learning-history status:  {r.learning_history_reason}")
    if r.warnings:
        print("\nWARNINGS:")
        for item in r.warnings:
            print(f"- {item}")
    if r.critical_errors:
        print("\nCRITICAL ERRORS:")
        for item in r.critical_errors:
            print(f"- {item}")
    else:
        print("\nSTATUS: PASS")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="MarketBot Track-A validator")
    parser.add_argument("command", choices=("validate", "schema"))
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.command == "schema":
            conn = connect(args.db)
            try:
                payload = {table: columns(conn, table) for table in sorted(tables(conn))}
            finally:
                conn.close()
            print(json.dumps(payload, indent=2))
            return 0

        report = validate(args.db)
        if args.json:
            print(json.dumps(asdict(report), indent=2))
        else:
            print_report(report)
        return 0 if report.ok else 2
    except ContractError as exc:
        print(f"CRITICAL ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
