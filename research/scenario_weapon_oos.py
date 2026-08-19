from __future__ import annotations

"""
MarketBot - Scenario × Weapon Chronological Holdout Validation

Research-only module.

Purpose
-------
Take the existing genuine date-level OOS observations produced by the
Track-B candidate modules, attach the MarketBot scenario registry to those
dates, and perform a chronological holdout evaluation for eligible
scenario × weapon combinations.

Important
---------
This module does NOT:
- modify candidate modules
- modify production scoring
- modify factor weights
- modify Track B
- modify Track C
- write to the database
- promote a weapon
- create trading signals

The existing candidate modules already perform their own walk-forward
research. This module performs a SECOND, scenario-conditioned chronological
holdout on their resulting OOS observations.

Evidence hierarchy
------------------
N < 20
    OOS_NOT_READY

N >= 20
    chronological split is possible

The first portion is the discovery/train portion.
The final portion is the untouched chronological holdout.

A holdout is never randomly shuffled.
"""

import argparse
import importlib
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = BASE_DIR / "market_intelligence.db"

VALIDATION_ARTIFACT = (
    BASE_DIR
    / "research"
    / "artifacts"
    / "scenario_weapon_validation.csv"
)

OUTPUT_ARTIFACT = (
    BASE_DIR
    / "research"
    / "artifacts"
    / "scenario_weapon_oos.csv"
)

EVIDENCE_ARTIFACT = (
    BASE_DIR
    / "research"
    / "artifacts"
    / "scenario_weapon_evidence.csv"
)

MIN_TOTAL_OBSERVATIONS = 20
MIN_HOLDOUT_OBSERVATIONS = 5
HOLDOUT_FRACTION = 0.30

ELIGIBLE_STATUS = "ELIGIBLE"

TRACK_B_CANDIDATES = {
    "TRACK_B_BASELINE_FAILURE": {
        "module": "research.baseline_failure_decomposition",
        "kind": "baseline",
    },
    "TRACK_B_CONDITIONAL_SCORE": {
        "module": "research.conditional_score_candidate",
        "kind": "conditional",
    },
    "TRACK_B_FACTOR_AGREEMENT": {
        "module": "research.factor_agreement_candidate",
        "kind": "agreement",
    },
}


def _require_columns(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise RuntimeError(
            f"{name} is missing required columns: {', '.join(missing)}"
        )


def load_eligible_candidates(
    validation_path: Path = VALIDATION_ARTIFACT,
) -> pd.DataFrame:
    """
    Load only ELIGIBLE scenario × weapon rows from the existing validation
    artifact.

    The validation artifact is treated as a research input.
    It is never modified.
    """
    if not validation_path.exists():
        raise FileNotFoundError(
            f"Scenario weapon validation artifact not found: {validation_path}"
        )

    frame = pd.read_csv(validation_path)

    _require_columns(
        frame,
        [
            "candidate",
            "scenario_id",
            "primary_scenario",
            "observations",
            "evidence_status",
        ],
        "scenario_weapon_validation.csv",
    )

    eligible = frame.loc[
        frame["evidence_status"].astype(str).str.upper()
        == ELIGIBLE_STATUS
    ].copy()

    return eligible.reset_index(drop=True)


def load_scenario_history(
    db_path: Path = DEFAULT_DB,
) -> pd.DataFrame:
    """
    Load scenario history without writing to the database.
    """
    conn = sqlite3.connect(str(db_path))

    try:
        table_exists = conn.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type='table'
              AND name='market_scenario_history'
            """
        ).fetchone()

        if table_exists is None:
            raise RuntimeError(
                "market_scenario_history does not exist."
            )

        frame = pd.read_sql_query(
            """
            SELECT
                DATE(trade_date) AS trade_date,
                index_name,
                primary_scenario,
                scenario_id,
                fingerprint,
                trend,
                volatility,
                daily_return,
                range_pct
            FROM market_scenario_history
            ORDER BY DATE(trade_date)
            """,
            conn,
        )
    finally:
        conn.close()

    frame["trade_date"] = pd.to_datetime(
        frame["trade_date"],
        errors="coerce",
    )

    return frame.dropna(
        subset=["trade_date", "scenario_id"]
    ).reset_index(drop=True)


def load_baseline_results(db_path: Path) -> pd.DataFrame:
    """
    Reuse the existing Baseline Failure candidate implementation.

    analyze() returns the genuine evaluated OOS dataframe.
    """
    module = importlib.import_module(
        TRACK_B_CANDIDATES[
            "TRACK_B_BASELINE_FAILURE"
        ]["module"]
    )

    result = module.analyze(db_path)

    evaluated = result.get("evaluated")

    if evaluated is None or evaluated.empty:
        return pd.DataFrame()

    frame = evaluated.copy()

    date_column = (
        "trade_date"
        if "trade_date" in frame.columns
        else "date"
    )

    _require_columns(
        frame,
        [date_column, "spread"],
        "Baseline candidate output",
    )

    frame["trade_date"] = pd.to_datetime(
        frame[date_column],
        errors="coerce",
    )

    frame["candidate"] = "TRACK_B_BASELINE_FAILURE"

    return frame[
        ["trade_date", "candidate", "spread"]
    ].dropna(
        subset=["trade_date", "spread"]
    )


def load_conditional_results(db_path: Path) -> pd.DataFrame:
    """
    Reuse the existing Conditional Score candidate.
    """
    module = importlib.import_module(
        TRACK_B_CANDIDATES[
            "TRACK_B_CONDITIONAL_SCORE"
        ]["module"]
    )

    result = module.run(db_path)

    if result is None or result.empty:
        return pd.DataFrame()

    frame = result.copy()

    _require_columns(
        frame,
        ["test_date", "spread"],
        "Conditional Score candidate output",
    )

    frame["trade_date"] = pd.to_datetime(
        frame["test_date"],
        errors="coerce",
    )

    frame["candidate"] = "TRACK_B_CONDITIONAL_SCORE"

    return frame[
        ["trade_date", "candidate", "spread"]
    ].dropna(
        subset=["trade_date", "spread"]
    )


def load_agreement_results(db_path: Path = DEFAULT_DB) -> pd.DataFrame:
    """
    Reuse the existing Factor Agreement candidate.
    """
    module = importlib.import_module(
        TRACK_B_CANDIDATES[
            "TRACK_B_FACTOR_AGREEMENT"
        ]["module"]
    )

    source = module.load_data(db_path)

    if source is None or source.empty:
        return pd.DataFrame()

    results = module.run_walk_forward(source)

    if results is None or results.empty:
        return pd.DataFrame()

    frame = results.copy()

    _require_columns(
        frame,
        ["test_date", "spread"],
        "Factor Agreement candidate output",
    )

    frame["trade_date"] = pd.to_datetime(
        frame["test_date"],
        errors="coerce",
    )

    frame["candidate"] = "TRACK_B_FACTOR_AGREEMENT"

    return frame[
        ["trade_date", "candidate", "spread"]
    ].dropna(
        subset=["trade_date", "spread"]
    )


def load_candidate_evidence(db_path: Path = DEFAULT_DB) -> pd.DataFrame:
    """
    Collect genuine date-level OOS observations from all three existing
    Track-B candidates.

    No candidate module is changed.
    """
    frames = [
        load_baseline_results(db_path),
        load_conditional_results(db_path),
        load_agreement_results(db_path),
    ]

    frames = [
        frame
        for frame in frames
        if not frame.empty
    ]

    if not frames:
        return pd.DataFrame(
            columns=["trade_date", "candidate", "spread"]
        )

    combined = pd.concat(
        frames,
        ignore_index=True,
    )

    combined["trade_date"] = pd.to_datetime(
        combined["trade_date"],
        errors="coerce",
    )

    combined["spread"] = pd.to_numeric(
        combined["spread"],
        errors="coerce",
    )

    combined = combined.dropna(
        subset=["trade_date", "candidate", "spread"]
    )

    return (
        combined
        .drop_duplicates(
            subset=["candidate", "trade_date"],
            keep="last",
        )
        .sort_values(
            ["candidate", "trade_date"]
        )
        .reset_index(drop=True)
    )


def attach_scenarios(
    evidence: pd.DataFrame,
    scenarios: pd.DataFrame,
) -> pd.DataFrame:
    """
    Attach scenario identity to each candidate OOS day.

    Scenario matching is date-based and intentionally conservative.

    If multiple scenario rows exist for a date, prefer NIFTY50/NIFTY
    when available; otherwise the first deterministic row is used.
    """
    if evidence.empty:
        return pd.DataFrame()

    scenario = scenarios.copy()

    scenario["trade_date"] = pd.to_datetime(
        scenario["trade_date"],
        errors="coerce",
    )

    scenario = scenario.dropna(
        subset=["trade_date", "scenario_id"]
    )

    scenario["_priority"] = np.where(
        scenario["index_name"]
        .astype(str)
        .str.upper()
        .isin({"NIFTY", "NIFTY50", "NIFTY 50"}),
        0,
        1,
    )

    scenario = (
        scenario
        .sort_values(
            ["trade_date", "_priority", "index_name"]
        )
        .drop_duplicates(
            subset=["trade_date"],
            keep="first",
        )
        .drop(columns=["_priority"])
    )

    merged = evidence.merge(
        scenario[
            [
                "trade_date",
                "index_name",
                "primary_scenario",
                "scenario_id",
                "fingerprint",
            ]
        ],
        on="trade_date",
        how="left",
        validate="many_to_one",
    )

    return merged.sort_values(
        ["candidate", "trade_date"]
    ).reset_index(drop=True)


def _split_index(
    n: int,
    holdout_fraction: float = HOLDOUT_FRACTION,
) -> tuple[int, int]:
    """
    Return train and holdout sizes.

    The holdout is always the newest chronological observations.
    """
    if n < MIN_TOTAL_OBSERVATIONS:
        return n, 0

    holdout = max(
        MIN_HOLDOUT_OBSERVATIONS,
        int(np.ceil(n * holdout_fraction)),
    )

    train = n - holdout

    if train < MIN_HOLDOUT_OBSERVATIONS:
        return n, 0

    return train, holdout


def _metrics(spreads: pd.Series) -> dict:
    values = pd.to_numeric(
        spreads,
        errors="coerce",
    ).dropna()

    if values.empty:
        return {
            "observations": 0,
            "average_spread": None,
            "median_spread": None,
            "positive_day_pct": None,
            "worst_day": None,
            "best_day": None,
        }

    return {
        "observations": int(len(values)),
        "average_spread": float(values.mean()),
        "median_spread": float(values.median()),
        "positive_day_pct": float(
            (values > 0).mean() * 100
        ),
        "worst_day": float(values.min()),
        "best_day": float(values.max()),
    }


def evaluate_holdout(
    frame: pd.DataFrame,
    min_total: int = MIN_TOTAL_OBSERVATIONS,
) -> dict:
    """
    Evaluate one chronological scenario × weapon sequence.

    This function never shuffles observations.
    """
    work = frame.copy()

    work["trade_date"] = pd.to_datetime(
        work["trade_date"],
        errors="coerce",
    )

    work["spread"] = pd.to_numeric(
        work["spread"],
        errors="coerce",
    )

    work = (
        work
        .dropna(subset=["trade_date", "spread"])
        .sort_values("trade_date")
        .drop_duplicates("trade_date")
        .reset_index(drop=True)
    )

    n = len(work)

    if n < min_total:
        metrics = _metrics(work["spread"])

        return {
            "evidence_status": "OOS_NOT_READY",
            "research_status": "INSUFFICIENT_HOLDOUT_HISTORY",
            "train_observations": n,
            "holdout_observations": 0,
            "train_start": (
                work["trade_date"].min()
                if n else None
            ),
            "train_end": (
                work["trade_date"].max()
                if n else None
            ),
            "holdout_start": None,
            "holdout_end": None,
            "train_average_spread": metrics["average_spread"],
            "train_median_spread": metrics["median_spread"],
            "train_positive_day_pct": metrics["positive_day_pct"],
            "oos_average_spread": None,
            "oos_median_spread": None,
            "oos_positive_day_pct": None,
            "oos_worst_day": None,
            "oos_best_day": None,
            "oos_result": "NOT_READY",
        }

    train_n, holdout_n = _split_index(n)

    if holdout_n == 0:
        return {
            "evidence_status": "OOS_NOT_READY",
            "research_status": "INVALID_SPLIT",
            "train_observations": n,
            "holdout_observations": 0,
            "train_start": work["trade_date"].min(),
            "train_end": work["trade_date"].max(),
            "holdout_start": None,
            "holdout_end": None,
            "train_average_spread": None,
            "train_median_spread": None,
            "train_positive_day_pct": None,
            "oos_average_spread": None,
            "oos_median_spread": None,
            "oos_positive_day_pct": None,
            "oos_worst_day": None,
            "oos_best_day": None,
            "oos_result": "NOT_READY",
        }

    train = work.iloc[:train_n].copy()
    holdout = work.iloc[train_n:].copy()

    train_metrics = _metrics(train["spread"])
    oos_metrics = _metrics(holdout["spread"])

    train_positive = train_metrics["average_spread"] > 0
    oos_positive = oos_metrics["average_spread"] > 0

    oos_hit_rate = oos_metrics["positive_day_pct"]

    persistent_positive = (
        train_positive
        and oos_positive
        and oos_hit_rate >= 60.0
        and oos_metrics["median_spread"] > 0
    )

    if persistent_positive:
        research_status = "PROMISING"
        oos_result = "POSITIVE_OOS"
    elif oos_metrics["average_spread"] is not None:
        research_status = "VALIDATION_READY"
        oos_result = "OOS_RESULT_AVAILABLE"
    else:
        research_status = "OOS_NOT_READY"
        oos_result = "NOT_READY"

    return {
        "evidence_status": "OOS_EVALUATED",
        "research_status": research_status,
        "train_observations": train_n,
        "holdout_observations": holdout_n,
        "train_start": train["trade_date"].min(),
        "train_end": train["trade_date"].max(),
        "holdout_start": holdout["trade_date"].min(),
        "holdout_end": holdout["trade_date"].max(),
        "train_average_spread": train_metrics["average_spread"],
        "train_median_spread": train_metrics["median_spread"],
        "train_positive_day_pct": train_metrics["positive_day_pct"],
        "oos_average_spread": oos_metrics["average_spread"],
        "oos_median_spread": oos_metrics["median_spread"],
        "oos_positive_day_pct": oos_metrics["positive_day_pct"],
        "oos_worst_day": oos_metrics["worst_day"],
        "oos_best_day": oos_metrics["best_day"],
        "oos_result": oos_result,
    }


def build_oos_report(
    eligible: pd.DataFrame,
    evidence: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build:
      1. one row per eligible scenario × weapon candidate
      2. one date-level evidence ledger

    The evidence ledger is deliberately retained because it becomes the
    foundation for future fingerprint learning and evidence accumulation.
    """
    if eligible.empty:
        return pd.DataFrame(), evidence.copy()

    rows = []

    for _, candidate in eligible.iterrows():
        name = str(candidate["candidate"])
        scenario_id = str(candidate["scenario_id"])

        subset = evidence.loc[
            (evidence["candidate"] == name)
            & (evidence["scenario_id"].astype(str) == scenario_id)
        ].copy()

        result = evaluate_holdout(subset)

        rows.append(
            {
                "candidate": name,
                "scenario_id": scenario_id,
                "primary_scenario": candidate[
                    "primary_scenario"
                ],
                "historical_observations": int(
                    len(subset)
                ),
                **result,
            }
        )

    report = pd.DataFrame(rows)

    if not report.empty:
        report = report.sort_values(
            [
                "research_status",
                "primary_scenario",
                "candidate",
                "scenario_id",
            ],
            kind="stable",
        ).reset_index(drop=True)

    return report, evidence.copy()


def build_evidence_ledger(
    evidence: pd.DataFrame,
) -> pd.DataFrame:
    """
    Produce a stable date-level evidence artifact.

    This is intentionally separate from the summary report.

    Future modules can use this artifact to learn:
        fingerprint -> weapon -> repeated outcomes
    """
    if evidence.empty:
        return evidence.copy()

    columns = [
        "trade_date",
        "candidate",
        "scenario_id",
        "primary_scenario",
        "fingerprint",
        "spread",
    ]

    available = [
        column
        for column in columns
        if column in evidence.columns
    ]

    return (
        evidence[available]
        .sort_values(
            ["trade_date", "candidate"]
        )
        .reset_index(drop=True)
    )


def run(
    db_path: Path = DEFAULT_DB,
    validation_path: Path = VALIDATION_ARTIFACT,
) -> dict:
    """
    Execute the complete read-only OOS research pipeline.
    """
    eligible = load_eligible_candidates(
        validation_path
    )

    scenarios = load_scenario_history(
        db_path
    )

    candidate_evidence = load_candidate_evidence(
        db_path
    )

    mapped = attach_scenarios(
        candidate_evidence,
        scenarios,
    )

    report, full_evidence = build_oos_report(
        eligible,
        mapped,
    )

    ledger = build_evidence_ledger(
        full_evidence
    )

    OUTPUT_ARTIFACT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report.to_csv(
        OUTPUT_ARTIFACT,
        index=False,
    )

    ledger.to_csv(
        EVIDENCE_ARTIFACT,
        index=False,
    )

    return {
        "eligible": eligible,
        "candidate_evidence": candidate_evidence,
        "mapped_evidence": mapped,
        "report": report,
        "ledger": ledger,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "MarketBot scenario × weapon chronological "
            "holdout validation."
        )
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
    )

    parser.add_argument(
        "--validation",
        type=Path,
        default=VALIDATION_ARTIFACT,
    )

    args = parser.parse_args()

    result = run(
        db_path=args.db,
        validation_path=args.validation,
    )

    eligible = result["eligible"]
    candidate_evidence = result["candidate_evidence"]
    mapped = result["mapped_evidence"]
    report = result["report"]

    print("\n" + "=" * 98)
    print(
        "MARKETBOT - SCENARIO × WEAPON CHRONOLOGICAL OOS VALIDATION"
    )
    print("=" * 98)

    print(
        f"\nEligible candidates        : {len(eligible):,}"
    )

    print(
        f"Candidate OOS observations : "
        f"{len(candidate_evidence):,}"
    )

    print(
        f"Scenario-mapped evidence   : "
        f"{len(mapped):,}"
    )

    if report.empty:
        print("\nNo eligible scenario × weapon candidates.")
    else:
        print("\nOOS VALIDATION RESULTS")

        display_columns = [
            "candidate",
            "scenario_id",
            "primary_scenario",
            "historical_observations",
            "train_observations",
            "holdout_observations",
            "train_average_spread",
            "oos_average_spread",
            "oos_median_spread",
            "oos_positive_day_pct",
            "research_status",
            "oos_result",
        ]

        available = [
            column
            for column in display_columns
            if column in report.columns
        ]

        print(
            report[available]
            .round(4)
            .to_string(index=False)
        )

    print(
        "\nSaved:"
        f"\n  {OUTPUT_ARTIFACT}"
        f"\n  {EVIDENCE_ARTIFACT}"
    )

    print(
        "\nREAD-ONLY:"
        " no database writes, production changes, "
        "candidate changes, factor-weight changes, "
        "or weapon promotion occurred."
    )


if __name__ == "__main__":
    main()