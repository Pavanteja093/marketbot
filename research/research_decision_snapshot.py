from __future__ import annotations

"""Read-only adapter for the six MarketBot Track-B/Track-C research candidates.

It consumes already-produced/persisted candidate evidence. It never executes
candidate research and never writes to the MarketBot database.
"""

from pathlib import Path
from typing import Any, Mapping
import importlib
import json
import sqlite3

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = BASE_DIR / "research" / "artifacts"
DEFAULT_INPUT = ARTIFACT_DIR / "unified_candidate_gate.csv"

CANDIDATES = (
    {
        "track": "B",
        "candidate": "TRACK_B_BASELINE_FAILURE",
        "source_module": "research.baseline_failure_decomposition",
        "aliases": ("Baseline Failure Decomposition",),
    },
    {
        "track": "B",
        "candidate": "TRACK_B_CONDITIONAL_SCORE",
        "source_module": "research.conditional_score_candidate",
        "aliases": ("Conditional Score",),
    },
    {
        "track": "B",
        "candidate": "TRACK_B_FACTOR_AGREEMENT",
        "source_module": "research.factor_agreement_candidate",
        "aliases": ("Factor Agreement",),
    },
    {
        "track": "C",
        "candidate": "TRACK_C_FACTOR_INTERACTION",
        "source_module": "research.factor_interaction_walk_forward",
        "aliases": ("C3.3 Factor Interaction", "Factor Interaction"),
    },
    {
        "track": "C",
        "candidate": "TRACK_C_REGIME_AWARE",
        "source_module": "research.regime_aware_walk_forward",
        "aliases": ("C2.2 Regime-Aware", "C2.1 Regime-Aware", "Regime-Aware"),
    },
    {
        "track": "C",
        "candidate": "TRACK_C_SCENARIO_WEAPON",
        "source_module": "research.scenario_weapon_candidate",
        "aliases": ("Scenario Weapon", "C3.4 Scenario Weapon"),
    },
)

OUTPUT_COLUMNS = [
    "track",
    "candidate",
    "source_module",
    "decision",
    "windows_or_days",
    "average_spread",
    "median_spread",
    "positive_window_pct",
    "worst_window",
    "evidence_status",
    "reason",
]


def _readonly_connection(db_path: str | Path) -> sqlite3.Connection:
    """Open SQLite in read-only URI mode."""
    path = Path(db_path).resolve()
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def _load_existing_artifact(path: str | Path = DEFAULT_INPUT) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _find_row(frame: pd.DataFrame, aliases: tuple[str, ...]) -> pd.Series | None:
    if frame.empty or "candidate" not in frame.columns:
        return None
    for alias in aliases:
        rows = frame.loc[frame["candidate"].astype(str).str.strip() == alias]
        if not rows.empty:
            return rows.iloc[0]
    return None


def _value(row: pd.Series, *names: str) -> Any:
    for name in names:
        if name not in row.index:
            continue
        value = row[name]
        if isinstance(value, (list, tuple)):
            return value
        try:
            if pd.notna(value):
                return value
        except (TypeError, ValueError):
            return value
    return None


def _as_float(value: Any) -> float | None:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if pd.notna(value) else None


def _as_int(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _gate_module():
    return importlib.import_module("research.candidate_gate")


def _apply_existing_gate(spreads: list[float]) -> Mapping[str, Any]:
    """Delegate acceptance to the authoritative existing candidate gate."""
    gate = _gate_module()
    evaluate = getattr(gate, "evaluate", None)
    if evaluate is None:
        raise RuntimeError("research.candidate_gate.evaluate is unavailable")

    frame = pd.DataFrame({"spread": pd.to_numeric(spreads, errors="coerce")}).dropna()
    if frame.empty:
        raise ValueError("No usable spread observations")

    result = evaluate(frame)
    if not isinstance(result, Mapping):
        raise TypeError("candidate_gate.evaluate did not return a mapping")
    return result


def _row_from_persisted_result(spec: Mapping[str, Any], row: pd.Series) -> dict[str, Any]:
    decision = str(_value(row, "decision") or "").upper()
    status = str(_value(row, "status") or "").upper()

    windows = _as_int(_value(row, "observations", "windows", "days"))
    average = _as_float(_value(row, "average", "average_spread"))
    median = _as_float(_value(row, "median", "median_spread"))
    positive = _as_float(
        _value(row, "positive_pct", "positive_window_pct", "positive_day_pct")
    )
    worst = _as_float(_value(row, "worst", "worst_window", "worst_day"))

    if windows is not None and windows <= 0:
        decision = "NO_RESULT"
        evidence_status = "INSUFFICIENT_DATA"
    elif status in {"ERROR", "UNAVAILABLE"}:
        decision = "NO_RESULT"
        evidence_status = "UNAVAILABLE"
    elif decision in {"PASS", "REVIEW", "FAIL"}:
        evidence_status = "SUFFICIENT"
    else:
        decision = "NO_RESULT"
        evidence_status = "INSUFFICIENT_DATA"

    reason = _value(row, "error", "reason")
    if reason is None:
        reason = "Consumed persisted candidate result; no new research was executed."

    return {
        "track": spec["track"],
        "candidate": spec["candidate"],
        "source_module": spec["source_module"],
        "decision": decision,
        "windows_or_days": windows,
        "average_spread": average,
        "median_spread": median,
        "positive_window_pct": positive,
        "worst_window": worst,
        "evidence_status": evidence_status,
        "reason": str(reason),
    }


def _normalise_input(result: Any) -> pd.DataFrame:
    if result is None:
        return pd.DataFrame()

    if isinstance(result, pd.DataFrame):
        return result.copy(deep=True)

    if isinstance(result, Mapping):
        rows = []
        for key, value in result.items():
            if isinstance(value, Mapping):
                row = dict(value)
                row.setdefault("candidate", key)
                rows.append(row)
        return pd.DataFrame(rows)

    raise TypeError("candidate_results must be a DataFrame or mapping")


def build_snapshot(
    candidate_results: pd.DataFrame | Mapping[str, Mapping[str, Any]] | None = None,
    *,
    artifact_path: str | Path = DEFAULT_INPUT,
) -> pd.DataFrame:
    """Build the six-candidate read-only decision snapshot.

    No candidate module is executed. If raw persisted OOS spreads are supplied,
    they are passed directly to research.candidate_gate.evaluate. If only a
    persisted summary is available, its existing PASS/REVIEW/FAIL decision is
    preserved rather than reconstructing a competing gate.
    """
    source = (
        _normalise_input(candidate_results)
        if candidate_results is not None
        else _load_existing_artifact(artifact_path)
    )

    rows: list[dict[str, Any]] = []

    for spec in CANDIDATES:
        row = _find_row(source, spec["aliases"])

        if row is None:
            rows.append(
                {
                    "track": spec["track"],
                    "candidate": spec["candidate"],
                    "source_module": spec["source_module"],
                    "decision": "NO_RESULT",
                    "windows_or_days": None,
                    "average_spread": None,
                    "median_spread": None,
                    "positive_window_pct": None,
                    "worst_window": None,
                    "evidence_status": "UNAVAILABLE",
                    "reason": "No persisted result is available for this candidate.",
                }
            )
            continue

        raw_spreads = _value(row, "spreads", "raw_spreads")

        if isinstance(raw_spreads, str):
            try:
                raw_spreads = json.loads(raw_spreads)
            except json.JSONDecodeError:
                raw_spreads = None

        if isinstance(raw_spreads, (list, tuple)):
            values = [_as_float(v) for v in raw_spreads]
            values = [v for v in values if v is not None]

            if not values:
                rows.append(
                    {
                        "track": spec["track"],
                        "candidate": spec["candidate"],
                        "source_module": spec["source_module"],
                        "decision": "NO_RESULT",
                        "windows_or_days": 0,
                        "average_spread": None,
                        "median_spread": None,
                        "positive_window_pct": None,
                        "worst_window": None,
                        "evidence_status": "INSUFFICIENT_DATA",
                        "reason": "Candidate supplied no usable OOS spread observations.",
                    }
                )
                continue

            gate_result = _apply_existing_gate(values)
            metrics = gate_result.get("metrics", {})

            rows.append(
                {
                    "track": spec["track"],
                    "candidate": spec["candidate"],
                    "source_module": spec["source_module"],
                    "decision": str(
                        gate_result.get("decision", "NO_RESULT")
                    ).upper(),
                    "windows_or_days": _as_int(metrics.get("windows")),
                    "average_spread": _as_float(metrics.get("average_spread")),
                    "median_spread": _as_float(metrics.get("median_spread")),
                    "positive_window_pct": _as_float(
                        metrics.get("positive_window_pct")
                    ),
                    "worst_window": _as_float(metrics.get("worst_window")),
                    "evidence_status": "SUFFICIENT",
                    "reason": "Gate applied to already-produced OOS spread observations.",
                }
            )
            continue

        rows.append(_row_from_persisted_result(spec, row))

    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def main() -> None:
    snapshot = build_snapshot()

    print("\n" + "=" * 100)
    print("MARKETBOT - RESEARCH DECISION SNAPSHOT")
    print("=" * 100)

    display = snapshot[
        [
            "track",
            "candidate",
            "decision",
            "windows_or_days",
            "average_spread",
            "median_spread",
            "positive_window_pct",
            "evidence_status",
        ]
    ].copy()

    print(display.round(4).to_string(index=False))
    print(
        "\nREAD-ONLY: no candidate module was executed and "
        "no database write was performed."
    )


if __name__ == "__main__":
    main()
