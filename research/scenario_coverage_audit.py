"""
MarketBot - Scenario Coverage Audit

Audits the scenario universe against the six configured research weapons.

Stable inputs:
    market_scenario_history
    scenario_weapon_matrix.csv

READ-ONLY:
    No database writes.
    No candidate changes.
    No production changes.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd


DEFAULT_DB = Path("market_intelligence.db")

DEFAULT_MATRIX = (
    Path(__file__).resolve().parent
    / "artifacts"
    / "scenario_weapon_matrix.csv"
)

DEFAULT_OUTPUT = (
    Path(__file__).resolve().parent
    / "artifacts"
    / "scenario_coverage_audit.csv"
)

WEAPONS = (
    "TRACK_B_BASELINE_FAILURE",
    "TRACK_B_CONDITIONAL_SCORE",
    "TRACK_B_FACTOR_AGREEMENT",
    "TRACK_C_FACTOR_INTERACTION",
    "TRACK_C_REGIME_AWARE",
    "TRACK_C_SCENARIO_WEAPON",
)

SCENARIO_COLUMNS = {
    "scenario_id",
    "primary_scenario",
    "fingerprint",
}

MATRIX_COLUMNS = {
    "scenario_id",
    "primary_scenario",
    "fingerprint",
    "candidate",
    "oos_windows",
    "evidence_status",
}


def load_scenarios(db_path: str | Path) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        frame = pd.read_sql_query(
            """
            SELECT
                scenario_id,
                primary_scenario,
                fingerprint,
                COUNT(*) AS scenario_observations,
                MIN(trade_date) AS first_observation,
                MAX(trade_date) AS last_observation
            FROM market_scenario_history
            GROUP BY
                scenario_id,
                primary_scenario,
                fingerprint
            ORDER BY scenario_id
            """,
            conn,
        )

    if frame.empty:
        raise ValueError(
            "market_scenario_history contains no scenario observations."
        )

    return frame


def load_matrix(matrix_path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(matrix_path)

    missing = sorted(MATRIX_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(
            "Scenario matrix is missing required columns: "
            + ", ".join(missing)
        )

    return frame.copy()


def build_audit(
    scenarios: pd.DataFrame,
    matrix: pd.DataFrame,
) -> pd.DataFrame:

    missing = sorted(SCENARIO_COLUMNS - set(scenarios.columns))
    if missing:
        raise ValueError(
            "Scenario history is missing required columns: "
            + ", ".join(missing)
        )

    scenario_frame = scenarios.copy()
    matrix_frame = matrix.copy()

    scenario_frame["scenario_observations"] = pd.to_numeric(
        scenario_frame["scenario_observations"],
        errors="coerce",
    ).fillna(0).astype(int)

    matrix_frame["oos_windows"] = pd.to_numeric(
        matrix_frame["oos_windows"],
        errors="coerce",
    ).fillna(0).astype(int)

    weapon_frame = pd.DataFrame(
        {"candidate": list(WEAPONS)}
    )

    scenario_frame["_key"] = 1
    weapon_frame["_key"] = 1

    result = scenario_frame.merge(
        weapon_frame,
        on="_key",
        how="inner",
    ).drop(columns="_key")

    matrix_columns = [
        "scenario_id",
        "fingerprint",
        "candidate",
        "oos_windows",
        "evidence_status",
    ]

    result = result.merge(
        matrix_frame[matrix_columns],
        on=["scenario_id", "fingerprint", "candidate"],
        how="left",
        suffixes=("", "_matrix"),
    )

    result["oos_windows"] = result["oos_windows"].fillna(0).astype(int)

    result["matrix_present"] = result["candidate"].isin(
        matrix_frame["candidate"]
    ) & result["oos_windows"].gt(0)

    def classify(row: pd.Series) -> str:
        if bool(row["matrix_present"]):
            return "EVIDENCE_PRESENT"

        return "NO_WEAPON_EVIDENCE"

    result["coverage_status"] = result.apply(
        classify,
        axis=1,
    )

    result["evidence_status"] = result["evidence_status"].fillna(
        "UNAVAILABLE"
    )

    result["oos_gap_to_10"] = (
        10 - result["oos_windows"]
    ).clip(lower=0)

    result["oos_gap_to_20"] = (
        20 - result["oos_windows"]
    ).clip(lower=0)

    columns = [
    "scenario_id",
    "primary_scenario",
    "fingerprint",
    "scenario_observations",
    "first_observation",
    "last_observation",
    "candidate",
    "oos_windows",
    "oos_gap_to_10",
    "oos_gap_to_20",
    "evidence_status",
    "coverage_status",
    "matrix_present",
]

    return (
        result[columns]
        .sort_values(
            [
                "scenario_id",
                "coverage_status",
                "candidate",
            ],
            ascending=[True, True, True],
            kind="mergesort",
        )
        .reset_index(drop=True)
    )


def run(
    db_path: str | Path = DEFAULT_DB,
    matrix_path: str | Path = DEFAULT_MATRIX,
    output_path: str | Path = DEFAULT_OUTPUT,
) -> pd.DataFrame:

    scenarios = load_scenarios(db_path)
    matrix = load_matrix(matrix_path)

    result = build_audit(scenarios, matrix)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result.to_csv(output_path, index=False)

    return result


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB),
    )

    parser.add_argument(
        "--matrix",
        default=str(DEFAULT_MATRIX),
    )

    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
    )

    args = parser.parse_args()

    result = run(
        args.db,
        args.matrix,
        args.output,
    )

    print("# MARKETBOT - SCENARIO COVERAGE AUDIT")
    print()

    print(
        "Distinct scenarios :",
        result["scenario_id"].nunique(),
    )

    print(
        "Configured weapons  :",
        result["candidate"].nunique(),
    )

    print(
        "Scenario × weapon relationships :",
        len(result),
    )

    print()
    print("COVERAGE COUNTS")
    print(
        result["coverage_status"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print()
    print("SCENARIO COVERAGE")

    summary = (
        result.groupby(
            [
                "scenario_id",
                "primary_scenario",
            ],
            as_index=False,
        )
        .agg(
            scenario_observations=(
                "scenario_observations",
                "first",
            ),
            weapons_with_evidence=(
                "matrix_present",
                "sum",
            ),
            total_configured_weapons=(
                "candidate",
                "count",
            ),
        )
    )

    print(summary.to_string(index=False))

    print()
    print("Saved:")
    print(Path(args.output).resolve())

    print()
    print(
        "READ-ONLY: no SQLite writes, candidate changes, production "
        "scoring changes, factor-weight changes, Track B/C changes, "
        "promotion, or live trading."
    )


if __name__ == "__main__":
    main()
