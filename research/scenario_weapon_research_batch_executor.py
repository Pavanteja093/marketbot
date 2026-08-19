from __future__ import annotations

"""
MarketBot - Scenario Ã— Weapon Research Batch Executor

Research-only execution boundary.

This module consumes the already-planned
research/artifacts/scenario_weapon_research_batches.csv artifact and executes
ONLY relationships explicitly authorized by that artifact and supported by
the existing scenario_weapon_oos research path.

It does NOT:
- regenerate eligibility, queue, or batches
- call the decision gate or unified report
- modify Track B or Track C modules
- write to SQLite
- modify existing research artifacts
- promote candidates
- create production signals
- alter OOS methodology

The existing scenario_weapon_oos module is treated as the OOS execution
adapter. This executor deliberately calls only its candidate-specific loader
functions; it never calls scenario_weapon_oos.run(), because that would
execute all supported Track-B candidates rather than only the authorized
candidate relationships.
"""

import argparse
import importlib
from pathlib import Path
from typing import Any

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_BATCH_ARTIFACT = (
    BASE_DIR / "research" / "artifacts" / "scenario_weapon_research_batches.csv"
)
DEFAULT_DB = BASE_DIR / "market_intelligence.db"
DEFAULT_OUTPUT_ARTIFACT = (
    BASE_DIR / "research" / "artifacts" / "scenario_weapon_research_batch_execution.csv"
)

REQUIRED_COLUMNS = {
    "batch_id",
    "batch_priority",
    "queue_priority",
    "research_priority",
    "scenario_id",
    "primary_scenario",
    "fingerprint",
    "candidate",
    "scenario_observations",
    "oos_windows",
    "target_oos_windows",
    "oos_gap_to_target",
    "eligibility_status",
    "queue_action",
    "batch_action",
    "batch_reason",
    "batch_rank",
}

EXECUTABLE_BATCH_ACTIONS = {
    "START_OOS_BATCH",
    "CONTINUE_OOS_BATCH",
}

WAIT_BATCH_ACTION = "WAIT_FOR_SCENARIO_HISTORY"

# Existing Track-B OOS paths. These are intentionally unchanged.
SUPPORTED_CANDIDATES = {
    "TRACK_B_BASELINE_FAILURE": "load_baseline_results",
    "TRACK_B_CONDITIONAL_SCORE": "load_conditional_results",
    "TRACK_B_FACTOR_AGREEMENT": "load_agreement_results",
}

# Track-C is executed only through the independently validated,
# candidate-specific OOS adapter. No Track-C methodology is implemented here.
TRACK_C_CANDIDATES = {
    "TRACK_C_FACTOR_INTERACTION",
    "TRACK_C_REGIME_AWARE",
    "TRACK_C_SCENARIO_WEAPON",
}

OUTPUT_COLUMNS = [
    "batch_id",
    "batch_priority",
    "queue_priority",
    "research_priority",
    "scenario_id",
    "primary_scenario",
    "fingerprint",
    "candidate",
    "scenario_observations",
    "planned_oos_windows",
    "target_oos_windows",
    "oos_gap_to_target",
    "eligibility_status",
    "queue_action",
    "batch_action",
    "batch_reason",
    "batch_rank",
    "execution_status",
    "execution_reason",
    "candidate_evidence_observations",
    "scenario_matched_observations",
    "historical_observations",
    "train_observations",
    "holdout_observations",
    "train_start",
    "train_end",
    "holdout_start",
    "holdout_end",
    "train_average_spread",
    "train_median_spread",
    "train_positive_day_pct",
    "oos_average_spread",
    "oos_median_spread",
    "oos_positive_day_pct",
    "oos_worst_day",
    "oos_best_day",
    "research_status",
    "oos_result",
]


def _require_columns(frame: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = sorted(columns - set(frame.columns))
    if missing:
        raise ValueError(
            f"{name} is missing required columns: {', '.join(missing)}"
        )


def load_batches(path: Path = DEFAULT_BATCH_ARTIFACT) -> pd.DataFrame:
    """Read and validate the stable batch artifact without modifying it."""
    if not path.exists():
        raise FileNotFoundError(f"Research batch artifact not found: {path}")

    frame = pd.read_csv(path)
    _require_columns(frame, REQUIRED_COLUMNS, "scenario_weapon_research_batches.csv")

    work = frame.copy(deep=True)

    for column in (
        "batch_id",
        "batch_priority",
        "queue_priority",
        "research_priority",
        "scenario_id",
        "primary_scenario",
        "fingerprint",
        "candidate",
        "eligibility_status",
        "queue_action",
        "batch_action",
        "batch_reason",
    ):
        work[column] = work[column].fillna("").astype(str).str.strip()

    for column in (
        "scenario_observations",
        "oos_windows",
        "target_oos_windows",
        "oos_gap_to_target",
        "batch_rank",
    ):
        work[column] = pd.to_numeric(work[column], errors="coerce")

    if work[["batch_id", "scenario_id", "candidate"]].eq("").any().any():
        raise ValueError(
            "Batch artifact contains blank batch_id, scenario_id, or candidate."
        )

    if work["batch_action"].isin(EXECUTABLE_BATCH_ACTIONS | {WAIT_BATCH_ACTION}).eq(False).any():
        invalid = sorted(
            set(work.loc[
                ~work["batch_action"].isin(
                    EXECUTABLE_BATCH_ACTIONS | {WAIT_BATCH_ACTION}
                ),
                "batch_action",
            ])
        )
        raise ValueError(
            "Batch artifact contains unsupported batch_action values: "
            + ", ".join(invalid)
        )

    duplicate_keys = work.duplicated(
        subset=["batch_id", "scenario_id", "candidate"],
        keep=False,
    )
    if duplicate_keys.any():
        raise ValueError(
            "Batch artifact contains duplicate batch_id/scenario_id/candidate "
            "relationships."
        )

    return work


def select_authorized_relationships(
    batches: pd.DataFrame,
    batch_id: str | None = None,
) -> pd.DataFrame:
    """
    Return only relationships explicitly authorized for OOS execution.

    WAIT_FOR_SCENARIO_HISTORY rows are never executable. They remain in the
    source artifact and are not rewritten.
    """
    _require_columns(batches, REQUIRED_COLUMNS, "batch dataframe")

    work = batches.loc[
        batches["batch_action"].isin(EXECUTABLE_BATCH_ACTIONS)
    ].copy()

    if batch_id is not None:
        work = work.loc[work["batch_id"] == str(batch_id)].copy()

    return work.sort_values(
        ["batch_priority", "batch_rank", "candidate", "scenario_id"],
        kind="stable",
    ).reset_index(drop=True)


def _load_oos_adapter() -> Any:
    """Load the existing Track-B OOS module."""
    return importlib.import_module("research.scenario_weapon_oos")


def _execute_track_c_relationship(
    scenario_id: str,
    fingerprint: str,
    candidate: str,
    db_path: Path,
) -> dict:
    """Delegate exactly one Track-C relationship to the safe OOS adapter."""
    if candidate not in TRACK_C_CANDIDATES:
        raise ValueError(f"Unsupported Track-C candidate: {candidate}")

    adapter = importlib.import_module("research.scenario_weapon_track_c_oos_adapter")
    executor = getattr(adapter, "execute_track_c_relationship", None)
    if executor is None:
        return {
            "candidate": candidate,
            "scenario_id": scenario_id,
            "fingerprint": fingerprint,
            "research_status": "UNSUPPORTED_OOS_PATH",
            "oos_result": "NOT_READY",
            "holdout_observations": 0,
            "scenario_matched_observations": 0,
            "execution_reason": (
                "Track-C adapter does not expose execute_track_c_relationship."
            ),
        }

    return executor(scenario_id, fingerprint, candidate, db_path)


def _track_c_execution_status(result: dict) -> str:
    """Map adapter research status to the executor's execution status."""
    status = str(result.get("research_status") or "").strip()
    if status in {
        "EXECUTED",
        "INSUFFICIENT_HOLDOUT_HISTORY",
        "NOT_READY",
        "UNSUPPORTED_OOS_PATH",
    }:
        return status
    return "UNSUPPORTED_OOS_PATH"


def _candidate_evidence(
    adapter: Any,
    candidate: str,
    db_path: Path,
) -> pd.DataFrame:
    loader_name = SUPPORTED_CANDIDATES[candidate]
    loader = getattr(adapter, loader_name)
    result = loader(db_path)

    if result is None:
        return pd.DataFrame(
            columns=["trade_date", "candidate", "spread"]
        )

    frame = result.copy()
    required = {"trade_date", "candidate", "spread"}
    _require_columns(frame, required, f"{candidate} OOS output")

    frame["trade_date"] = pd.to_datetime(
        frame["trade_date"], errors="coerce"
    )
    frame["spread"] = pd.to_numeric(frame["spread"], errors="coerce")
    frame["candidate"] = frame["candidate"].astype(str)

    return (
        frame.dropna(subset=["trade_date", "candidate", "spread"])
        .drop_duplicates(["candidate", "trade_date"], keep="last")
        .sort_values(["candidate", "trade_date"], kind="stable")
        .reset_index(drop=True)
    )


def _attach_scenarios(
    adapter: Any,
    evidence: pd.DataFrame,
    scenarios: pd.DataFrame,
) -> pd.DataFrame:
    if evidence.empty:
        return pd.DataFrame()

    return adapter.attach_scenarios(
        evidence.copy(deep=True),
        scenarios.copy(deep=True),
    )


def _safe_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    return value


def _result_row(
    relationship: pd.Series,
    *,
    execution_status: str,
    execution_reason: str,
    candidate_evidence_observations: int = 0,
    scenario_matched_observations: int = 0,
    holdout_result: dict | None = None,
) -> dict:
    result = holdout_result or {}

    return {
        "batch_id": relationship["batch_id"],
        "batch_priority": relationship["batch_priority"],
        "queue_priority": relationship["queue_priority"],
        "research_priority": relationship["research_priority"],
        "scenario_id": relationship["scenario_id"],
        "primary_scenario": relationship["primary_scenario"],
        "fingerprint": relationship["fingerprint"],
        "candidate": relationship["candidate"],
        "scenario_observations": _safe_value(
            relationship["scenario_observations"]
        ),
        "planned_oos_windows": _safe_value(relationship["oos_windows"]),
        "target_oos_windows": _safe_value(
            relationship["target_oos_windows"]
        ),
        "oos_gap_to_target": _safe_value(
            relationship["oos_gap_to_target"]
        ),
        "eligibility_status": relationship["eligibility_status"],
        "queue_action": relationship["queue_action"],
        "batch_action": relationship["batch_action"],
        "batch_reason": relationship["batch_reason"],
        "batch_rank": _safe_value(relationship["batch_rank"]),
        "execution_status": execution_status,
        "execution_reason": execution_reason,
        "candidate_evidence_observations": candidate_evidence_observations,
        "scenario_matched_observations": scenario_matched_observations,
        "historical_observations": result.get("train_observations", 0)
        + result.get("holdout_observations", 0),
        "train_observations": result.get("train_observations"),
        "holdout_observations": result.get("holdout_observations"),
        "train_start": result.get("train_start"),
        "train_end": result.get("train_end"),
        "holdout_start": result.get("holdout_start"),
        "holdout_end": result.get("holdout_end"),
        "train_average_spread": result.get("train_average_spread"),
        "train_median_spread": result.get("train_median_spread"),
        "train_positive_day_pct": result.get("train_positive_day_pct"),
        "oos_average_spread": result.get("oos_average_spread"),
        "oos_median_spread": result.get("oos_median_spread"),
        "oos_positive_day_pct": result.get("oos_positive_day_pct"),
        "oos_worst_day": result.get("oos_worst_day"),
        "oos_best_day": result.get("oos_best_day"),
        "research_status": result.get("research_status"),
        "oos_result": result.get("oos_result"),
    }


def execute(
    db_path: Path = DEFAULT_DB,
    batch_path: Path = DEFAULT_BATCH_ARTIFACT,
    output_path: Path = DEFAULT_OUTPUT_ARTIFACT,
    batch_id: str | None = None,
) -> pd.DataFrame:
    """
    Execute only authorized, currently supported relationships.

    Candidate OOS loaders are called at most once per candidate, then their
    genuine date-level OOS observations are restricted to the exact authorized
    scenario_id/fingerprint relationship from the batch artifact.

    No SQLite write is performed by this module.
    """
    batches = load_batches(batch_path)
    authorized = select_authorized_relationships(batches, batch_id=batch_id)

    if authorized.empty:
        report = pd.DataFrame(columns=OUTPUT_COLUMNS)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report.to_csv(output_path, index=False)
        return report

    adapter = _load_oos_adapter()
    scenarios = adapter.load_scenario_history(db_path)

    evidence_by_candidate: dict[str, pd.DataFrame] = {}
    mapped_by_candidate: dict[str, pd.DataFrame] = {}

    rows: list[dict] = []

    # Preserve one row for every requested relationship, including unsupported
    # candidates. Unsupported does not mean failed research; it means this
    # executor refuses to cross an unimplemented OOS boundary.
    for _, relationship in authorized.iterrows():
        candidate = str(relationship["candidate"])

        if candidate in TRACK_C_CANDIDATES:
            result = _execute_track_c_relationship(
                str(relationship["scenario_id"]),
                str(relationship["fingerprint"]),
                candidate,
                db_path,
            )
            rows.append(
                _result_row(
                    relationship,
                    execution_status=_track_c_execution_status(result),
                    execution_reason=str(
                        result.get(
                            "execution_reason",
                            "Track-C relationship delegated to the safe candidate-specific OOS adapter.",
                        )
                    ),
                    candidate_evidence_observations=int(
                        result.get("candidate_evidence_observations", 0) or 0
                    ),
                    scenario_matched_observations=int(
                        result.get("scenario_matched_observations", 0) or 0
                    ),
                    holdout_result=result,
                )
            )
            continue

        if candidate not in SUPPORTED_CANDIDATES:
            rows.append(
                _result_row(
                    relationship,
                    execution_status="UNSUPPORTED_OOS_PATH",
                    execution_reason=(
                        f"{candidate} is authorized by the batch artifact but "
                        "is not exposed by the existing scenario_weapon_oos "
                        "execution path. No candidate code was executed."
                    ),
                )
            )
            continue

        if candidate not in evidence_by_candidate:
            evidence_by_candidate[candidate] = _candidate_evidence(
                adapter, candidate, db_path
            )
            mapped_by_candidate[candidate] = _attach_scenarios(
                adapter,
                evidence_by_candidate[candidate],
                scenarios,
            )

        candidate_evidence = evidence_by_candidate[candidate]
        mapped = mapped_by_candidate[candidate]

        scenario_id = str(relationship["scenario_id"])
        fingerprint = str(relationship["fingerprint"])

        subset = mapped.loc[
            (mapped["candidate"].astype(str) == candidate)
            & (mapped["scenario_id"].astype(str) == scenario_id)
            & (mapped["fingerprint"].astype(str) == fingerprint)
        ].copy()

        candidate_count = int(
            candidate_evidence.loc[
                candidate_evidence["candidate"].astype(str) == candidate
            ].shape[0]
        )

        scenario_count = int(len(subset))

        result = adapter.evaluate_holdout(subset)

        status = "EXECUTED"
        reason = (
            "Authorized batch relationship executed through the existing "
            "candidate-specific OOS path; scenario/fingerprint restriction "
            "was applied before chronological holdout evaluation."
        )

        if scenario_count == 0:
            reason = (
                "Authorized relationship reached the existing OOS path, but "
                "no genuine OOS observations matched the exact scenario_id "
                "and fingerprint. No synthetic evidence was created."
            )

        rows.append(
            _result_row(
                relationship,
                execution_status=status,
                execution_reason=reason,
                candidate_evidence_observations=candidate_count,
                scenario_matched_observations=scenario_count,
                holdout_result=result,
            )
        )

    report = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)

    if not report.empty:
        report = report.sort_values(
            ["batch_priority", "batch_rank", "candidate", "scenario_id"],
            kind="stable",
        ).reset_index(drop=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(output_path, index=False)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Execute authorized Scenario Ã— Weapon research batches."
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--batch", type=str, default=None)
    parser.add_argument("--batches", type=Path, default=DEFAULT_BATCH_ARTIFACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_ARTIFACT)
    args = parser.parse_args()

    report = execute(
        db_path=args.db,
        batch_path=args.batches,
        output_path=args.output,
        batch_id=args.batch,
    )

    print("\n" + "=" * 98)
    print("MARKETBOT - SCENARIO Ã— WEAPON RESEARCH BATCH EXECUTOR")
    print("=" * 98)
    print(f"\nRequested relationships : {len(report):,}")
    if not report.empty:
        print(
            "\nExecution status:\n"
            + report["execution_status"].value_counts().to_string()
        )
        print(
            "\nResearch status:\n"
            + report["research_status"].fillna("NONE").value_counts().to_string()
        )

    print(f"\nSaved:\n  {args.output}")
    print(
        "\nREAD-ONLY:"
        " no SQLite writes, production changes, candidate promotion, "
        "decision-gate execution, or existing-artifact modification occurred."
    )


if __name__ == "__main__":
    main()
