from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ARTIFACT_DIR = BASE_DIR / "research" / "artifacts"
DEFAULT_COVERAGE = DEFAULT_ARTIFACT_DIR / "track_c_episode_coverage_diagnostic.csv"
DEFAULT_QUALIFICATION = DEFAULT_ARTIFACT_DIR / "track_c_episode_qualification.csv"
DEFAULT_STABILITY = DEFAULT_ARTIFACT_DIR / "track_c_interaction_episode_stability.csv"
DEFAULT_STABILITY_EPISODES = DEFAULT_ARTIFACT_DIR / "track_c_interaction_episode_stability_episodes.csv"
DEFAULT_OOS = DEFAULT_ARTIFACT_DIR / "track_c_interaction_oos_validation.csv"
DEFAULT_OUTPUT = DEFAULT_ARTIFACT_DIR / "track_c_interaction_evidence_synthesis.csv"
DEFAULT_LOG = DEFAULT_ARTIFACT_DIR / "track_c_interaction_evidence_synthesis_run.log"

KEYS = ["scenario", "factor_a", "state_a", "factor_b", "state_b"]
REQUIRED_COVERAGE = KEYS + [
    "total_candidate_observations", "total_scenario_episodes", "episodes_with_candidate",
    "episode_coverage_pct", "qualifying_episodes_ge_20", "max_episode_observations",
    "mean_observations_per_occupied_episode", "median_observations_per_occupied_episode",
    "max_episode_concentration_pct",
]
REQUIRED_OOS = KEYS + ["observations", "up_pct", "mean_return_5d", "oos_folds", "oos_stability"]
REQUIRED_QUALIFICATION = KEYS


def _read(path: Path, required: bool = True) -> pd.DataFrame:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Required artifact not found: {path}")
        return pd.DataFrame()
    return pd.read_csv(path)


def _validate(df: pd.DataFrame, required: Iterable[str], name: str) -> None:
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError(f"{name} missing required columns: {', '.join(missing)}")


def _norm_keys(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in KEYS:
        out[c] = out[c].astype(str).str.strip()
    return out


def _candidate_key(row: pd.Series) -> tuple[str, ...]:
    return tuple(str(row[c]) for c in KEYS)


def _num(row: pd.Series, col: str, default=0.0):
    value = row.get(col, default)
    if pd.isna(value):
        return default
    return value


def _coverage_classification(row: pd.Series | None) -> str:
    if row is None:
        return "NO_HISTORICAL_EVIDENCE"
    total = int(_num(row, "total_candidate_observations", 0))
    if total <= 0:
        return "NO_HISTORICAL_EVIDENCE"
    qualifying = int(_num(row, "qualifying_episodes_ge_20", 0))
    if qualifying > 0:
        return "RECURRENT_WITH_QUALIFYING_EPISODES"
    return "RECURRENT_BUT_SPARSE"


def synthesize(
    coverage: pd.DataFrame,
    qualification: pd.DataFrame,
    oos: pd.DataFrame,
) -> pd.DataFrame:
    coverage = _norm_keys(coverage)
    qualification = _norm_keys(qualification) if not qualification.empty else qualification
    oos = _norm_keys(oos) if not oos.empty else oos

    _validate(coverage, REQUIRED_COVERAGE, "coverage")
    if not qualification.empty:
        _validate(qualification, REQUIRED_QUALIFICATION, "qualification")
    _validate(oos, REQUIRED_OOS, "oos")

    # Candidates are defined by the qualification/coverage layer, not invented here.
    candidates = coverage[KEYS].drop_duplicates().copy()
    if not qualification.empty:
        candidates = pd.concat([candidates, qualification[KEYS]], ignore_index=True).drop_duplicates()
    candidates = candidates.sort_values(KEYS).reset_index(drop=True)

    coverage_map = { _candidate_key(r): r for _, r in coverage.iterrows() }
    oos_map = { _candidate_key(r): r for _, r in oos.iterrows() }
    qual_map = { _candidate_key(r): r for _, r in qualification.iterrows() } if not qualification.empty else {}

    rows = []
    for _, c in candidates.iterrows():
        key = _candidate_key(c)
        cv = coverage_map.get(key)
        ov = oos_map.get(key)
        qv = qual_map.get(key)

        total_obs = int(_num(cv, "total_candidate_observations", 0)) if cv is not None else 0
        scenario_eps = int(_num(cv, "total_scenario_episodes", 0)) if cv is not None else 0
        occupied = int(_num(cv, "episodes_with_candidate", 0)) if cv is not None else 0
        qualifying = int(_num(cv, "qualifying_episodes_ge_20", 0)) if cv is not None else 0
        coverage_class = _coverage_classification(cv)

        oos_exists = ov is not None
        oos_obs = int(_num(ov, "observations", 0)) if oos_exists else 0
        oos_up = float(_num(ov, "up_pct", 0.0)) if oos_exists else None
        oos_ret = float(_num(ov, "mean_return_5d", 0.0)) if oos_exists else None
        oos_folds = int(_num(ov, "oos_folds", 0)) if oos_exists else 0
        oos_stability = str(ov.get("oos_stability", "NO_OOS_EVIDENCE")) if oos_exists else "NO_OOS_EVIDENCE"

        if total_obs == 0:
            evidence = "NO_HISTORICAL_EVIDENCE"
            action = "No historical evidence; retain candidate only for future data collection."
        elif not oos_exists or oos_obs == 0:
            evidence = "NO_OOS_EVIDENCE"
            action = "Recurring historical pattern lacks matching OOS evidence; do not promote."
        elif qualifying == 0:
            evidence = "RECURRENT_BUT_SPARSE"
            action = "Continue collecting independent episodes; insufficient within-episode evidence for stability."
        elif oos_stability == "STABLE" and oos_folds >= 3 and qualifying >= 2:
            evidence = "MULTI_SOURCE_REPEATABLE_EVIDENCE"
            action = "Advance to stricter independent-episode and economic validation; still research-only."
        elif oos_stability in {"SINGLE_FOLD", "INSUFFICIENT_EPISODES"} or oos_folds < 3:
            evidence = "RECURRENT_BUT_SPARSE"
            action = "OOS evidence is too concentrated or sparse; continue episode accumulation."
        else:
            evidence = "RECURRENT_BUT_SPARSE"
            action = "Evidence is incomplete or mixed; continue research conservatively."

        rows.append({
            **{k: c[k] for k in KEYS},
            "total_candidate_observations": total_obs,
            "total_scenario_episodes": scenario_eps,
            "episodes_with_candidate": occupied,
            "episode_coverage_pct": float(_num(cv, "episode_coverage_pct", 0.0)) if cv is not None else 0.0,
            "qualifying_episodes_ge_20": qualifying,
            "max_episode_observations": int(_num(cv, "max_episode_observations", 0)) if cv is not None else 0,
            "mean_observations_per_occupied_episode": float(_num(cv, "mean_observations_per_occupied_episode", 0.0)) if cv is not None else 0.0,
            "median_observations_per_occupied_episode": float(_num(cv, "median_observations_per_occupied_episode", 0.0)) if cv is not None else 0.0,
            "max_episode_concentration_pct": float(_num(cv, "max_episode_concentration_pct", 0.0)) if cv is not None else 0.0,
            "coverage_classification": coverage_class,
            "episode_stability_classification": str(qv.get("classification", qv.get("episode_stability_classification", "UNKNOWN"))) if qv is not None else "UNKNOWN",
            "oos_observations": oos_obs,
            "oos_up_pct": oos_up,
            "oos_mean_return_5d": oos_ret,
            "oos_oos_folds": oos_folds,
            "oos_stability": oos_stability,
            "evidence_classification": evidence,
            "research_action": action,
        })

    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage", default=str(DEFAULT_COVERAGE))
    parser.add_argument("--qualification", default=str(DEFAULT_QUALIFICATION))
    parser.add_argument("--oos", default=str(DEFAULT_OOS))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--log", default=str(DEFAULT_LOG))
    args = parser.parse_args()

    lines = []
    def log(s=""):
        print(s)
        lines.append(s)

    log("MARKETBOT TRACK C - INTERACTION EVIDENCE SYNTHESIS")
    log("READ-ONLY: No SQLite access. No production changes. No candidate promotion.")
    log("")

    coverage = _read(Path(args.coverage))
    qualification = _read(Path(args.qualification), required=False)
    oos = _read(Path(args.oos))
    result = synthesize(coverage, qualification, oos)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out, index=False)

    log(f"Candidates synthesized : {len(result)}")
    log("")
    for _, r in result.iterrows():
        log(f"{r['scenario']} | {r['factor_a']}={r['state_a']} | {r['factor_b']}={r['state_b']} | {r['evidence_classification']}")
        log(f"  action: {r['research_action']}")
    log("")
    log(f"Saved: {out}")
    log("RESEARCH ONLY")
    log("SQLite writes      : NONE")
    log("Production changes : NONE")
    log("Candidate promotion: NONE")
    log("STATUS             : SUCCESS")

    Path(args.log).parent.mkdir(parents=True, exist_ok=True)
    Path(args.log).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
