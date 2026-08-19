from __future__ import annotations

"""
MarketBot Track C - Final Evidence Adjudication

Research-only final adjudication layer.

Combines:
1. interaction evidence synthesis,
2. cross-episode temporal robustness,
3. interaction null-validation evidence.

This layer does NOT promote candidates, change weights, write SQLite, or alter
production state. It applies deterministic and conservative rules to the
already-generated research artifacts.
"""

from pathlib import Path
import argparse
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = BASE_DIR / "research" / "artifacts"

DEFAULT_EVIDENCE = ARTIFACT_DIR / "track_c_interaction_evidence_synthesis.csv"
DEFAULT_TEMPORAL = ARTIFACT_DIR / "track_c_cross_episode_temporal_robustness.csv"
DEFAULT_NULL = ARTIFACT_DIR / "track_c_interaction_null_validation.csv"
DEFAULT_OUTPUT = ARTIFACT_DIR / "track_c_final_evidence_adjudication.csv"
DEFAULT_LOG = ARTIFACT_DIR / "track_c_final_evidence_adjudication_run.log"

KEYS = ["scenario", "factor_a", "state_a", "factor_b", "state_b"]

REQUIRED_EVIDENCE = set(KEYS) | {
    "total_candidate_observations",
    "qualifying_episodes_ge_20",
    "oos_observations",
    "oos_oos_folds",
    "oos_stability",
    "evidence_classification",
}

REQUIRED_TEMPORAL = set(KEYS) | {
    "episode_count",
    "qualifying_episode_count_ge_20",
    "total_observations",
    "temporal_robustness_classification",
}

REQUIRED_NULL = set(KEYS) | {
    "observations",
    "raw_p_value",
    "adjusted_p_value",
    "null_result",
}


def _validate(df: pd.DataFrame, required: set[str], name: str) -> None:
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(
            f"{name} missing required columns: {', '.join(missing)}"
        )


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy(deep=True)
    for col in KEYS:
        out[col] = out[col].astype(str).str.strip()
    return out


def _key(row: pd.Series) -> tuple[str, ...]:
    return tuple(str(row[c]).strip() for c in KEYS)


def _numeric(row: pd.Series, col: str, default=0.0) -> float:
    value = row.get(col, default)
    if pd.isna(value):
        return default
    return float(value)


def adjudicate(
    evidence: pd.DataFrame,
    temporal: pd.DataFrame,
    null_validation: pd.DataFrame,
) -> pd.DataFrame:
    _validate(evidence, REQUIRED_EVIDENCE, "evidence synthesis")
    _validate(temporal, REQUIRED_TEMPORAL, "temporal robustness")
    _validate(null_validation, REQUIRED_NULL, "null validation")

    ev = _normalise(evidence)
    tr = _normalise(temporal)
    nv = _normalise(null_validation)

    ev_map = {_key(r): r for _, r in ev.iterrows()}
    tr_map = {_key(r): r for _, r in tr.iterrows()}
    nv_map = {_key(r): r for _, r in nv.iterrows()}

    # The evidence-synthesis artifact defines the six current candidates.
    candidates = ev[KEYS].drop_duplicates().sort_values(KEYS).reset_index(drop=True)

    rows = []
    for _, c in candidates.iterrows():
        key = _key(c)
        e = ev_map.get(key)
        t = tr_map.get(key)
        n = nv_map.get(key)

        # Each artifact answers a different research question.  Do not let a
        # zero in the evidence-synthesis artifact erase positive evidence in
        # the independent temporal/null layers.
        evidence_obs = int(_numeric(e, "total_candidate_observations", 0))
        evidence_qualifying = int(_numeric(e, "qualifying_episodes_ge_20", 0))
        temporal_obs = int(_numeric(t, "total_observations", 0)) if t is not None else 0
        temporal_qualifying = (
            int(_numeric(t, "qualifying_episode_count_ge_20", 0))
            if t is not None else 0
        )

        oos_obs = int(_numeric(e, "oos_observations", 0))
        oos_folds = int(_numeric(e, "oos_oos_folds", 0))
        oos_stability = str(e.get("oos_stability", "NO_OOS_EVIDENCE"))

        temporal_class = (
            str(t.get("temporal_robustness_classification", "NO_TEMPORAL_EVIDENCE"))
            if t is not None else "NO_TEMPORAL_EVIDENCE"
        )

        null_result = (
            str(n.get("null_result", "NO_NULL_EVIDENCE"))
            if n is not None else "NO_NULL_EVIDENCE"
        )
        raw_p = _numeric(n, "raw_p_value", float("nan")) if n is not None else float("nan")
        adjusted_p = _numeric(n, "adjusted_p_value", float("nan")) if n is not None else float("nan")
        null_obs = int(_numeric(n, "observations", 0)) if n is not None else 0

        # Historical evidence exists if any validated Track C research layer
        # contains observations for this exact candidate key.  A mismatch is
        # recorded explicitly rather than converted into NO_HISTORICAL_EVIDENCE.
        positive_sources = sum(x > 0 for x in (evidence_obs, temporal_obs, null_obs))
        historical_obs = max(evidence_obs, temporal_obs, null_obs)
        if positive_sources == 0:
            lineage_status = "NO_HISTORICAL_OBSERVATIONS"
        elif evidence_obs == 0 and (temporal_obs > 0 or null_obs > 0):
            lineage_status = "CROSS_ARTIFACT_OBSERVATION_MISMATCH"
        elif temporal_obs == 0 and (evidence_obs > 0 or null_obs > 0):
            lineage_status = "CROSS_ARTIFACT_OBSERVATION_MISMATCH"
        elif len({evidence_obs, temporal_obs, null_obs}) > 1:
            lineage_status = "DIFFERENT_SAMPLE_SCOPES"
        else:
            lineage_status = "CROSS_ARTIFACT_OBSERVATIONS_CONSISTENT"

        # The temporal layer is authoritative for independent episode
        # repeatability. Its strict >=20 episode gate must not be weakened by
        # the older evidence-synthesis coverage artifact.
        qualifying = temporal_qualifying if t is not None else evidence_qualifying

        # Conservative adjudication.
        if positive_sources == 0:
            final_class = "NO_HISTORICAL_EVIDENCE"
            action = (
                "No validated Track C artifact contains historical observations "
                "for this candidate; retain only for future data collection."
            )
        elif t is None:
            final_class = "INSUFFICIENT_TEMPORAL_EVIDENCE"
            action = (
                "Temporal robustness artifact is missing; do not adjudicate "
                "repeatability or promote."
            )
        elif temporal_obs == 0:
            final_class = "NO_REPEATABLE_EVIDENCE"
            action = (
                "No observations are available in the independent temporal "
                "episode layer; do not promote."
            )
        elif temporal_class != "MULTI_EPISODE_STABLE":
            final_class = "NO_REPEATABLE_EVIDENCE"
            action = (
                "Historical recurrence does not demonstrate repeated stable "
                "episode behavior; do not promote."
            )
        elif qualifying < 2:
            final_class = "NO_REPEATABLE_EVIDENCE"
            action = (
                "Fewer than two independently qualifying episodes exist; the "
                "strict >=20-observation episode threshold is not satisfied."
            )
        elif oos_obs == 0 or oos_folds < 3 or oos_stability not in {"STABLE", "REPEATED"}:
            final_class = "INSUFFICIENT_OOS_EVIDENCE"
            action = (
                "Independent OOS evidence is insufficient for combined "
                "repeatability; continue research without promotion."
            )
        elif n is None or null_obs == 0:
            final_class = "INSUFFICIENT_NULL_EVIDENCE"
            action = (
                "Null-validation evidence is missing; retain research-only "
                "status and do not promote."
            )
        elif pd.notna(adjusted_p) and adjusted_p < 0.05:
            final_class = "MULTI_SOURCE_SUPPORT"
            action = (
                "Multiple independent research layers support the candidate; "
                "advance only to stricter economic and independent validation."
            )
        else:
            # A candidate must survive the null layer as well. A raw p-value
            # below 0.05 is not enough when multiple-testing adjustment fails.
            final_class = "NO_REPEATABLE_EVIDENCE"
            action = (
                "Temporal/OOS evidence is not sufficiently supported after "
                "multiple-testing-aware null validation; do not promote."
            )

        rows.append({
            **{k: c[k] for k in KEYS},
            "historical_observations": historical_obs,
            "evidence_synthesis_observations": evidence_obs,
            "temporal_observations": temporal_obs,
            "null_observations": null_obs,
            "evidence_lineage_status": lineage_status,
            "qualifying_episodes_ge_20": qualifying,
            "oos_observations": oos_obs,
            "oos_folds": oos_folds,
            "oos_stability": oos_stability,
            "temporal_robustness_classification": temporal_class,
            "null_result": null_result,
            "raw_p_value": raw_p,
            "adjusted_p_value": adjusted_p,
            "evidence_synthesis_classification": str(
                e.get("evidence_classification", "UNKNOWN")
            ),
            "final_evidence_classification": final_class,
            "final_research_action": action,
        })

    return (
        pd.DataFrame(rows)
        .sort_values(KEYS, kind="mergesort")
        .reset_index(drop=True)
    )


def run(
    evidence_path: Path = DEFAULT_EVIDENCE,
    temporal_path: Path = DEFAULT_TEMPORAL,
    null_path: Path = DEFAULT_NULL,
    output_path: Path = DEFAULT_OUTPUT,
    log_path: Path = DEFAULT_LOG,
) -> pd.DataFrame:
    evidence = pd.read_csv(evidence_path)
    temporal = pd.read_csv(temporal_path)
    null_validation = pd.read_csv(null_path)

    result = adjudicate(evidence, temporal, null_validation)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)

    lines = [
        "MARKETBOT TRACK C - FINAL EVIDENCE ADJUDICATION",
        "READ-ONLY: No SQLite access. No production changes. No candidate promotion.",
        f"Candidates adjudicated: {len(result)}",
        "",
        result[
            KEYS
            + [
                "final_evidence_classification",
                "final_research_action",
            ]
        ].to_string(index=False),
        "",
        f"Saved: {output_path.resolve()}",
        "RESEARCH ONLY",
        "SQLite writes      : NONE",
        "Production changes : NONE",
        "Candidate promotion: NONE",
        "STATUS             : SUCCESS",
    ]
    text = "\n".join(lines) + "\n"
    print(text)
    log_path.write_text(text, encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", default=str(DEFAULT_EVIDENCE))
    parser.add_argument("--temporal", default=str(DEFAULT_TEMPORAL))
    parser.add_argument("--null", dest="null_path", default=str(DEFAULT_NULL))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--log", default=str(DEFAULT_LOG))
    args = parser.parse_args()

    run(
        Path(args.evidence),
        Path(args.temporal),
        Path(args.null_path),
        Path(args.output),
        Path(args.log),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
