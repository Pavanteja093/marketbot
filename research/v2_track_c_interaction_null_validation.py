"""Research-only null validation for the six Track C interaction candidates.

This module does not rediscover candidates. It uses the existing interaction
search artifact for the candidate definitions and observed statistics, then
permutes realized outcome labels within each scenario while preserving each
candidate's observed sample size.  It never writes to SQLite or production
state.
"""
from __future__ import annotations

from pathlib import Path
import logging
import numpy as np
import pandas as pd

DEFAULT_DATASET = Path("research/artifacts/historical_probability_dataset.csv")
DEFAULT_SEARCH = Path("research/artifacts/track_c_scenario_factor_interactions.csv")
DEFAULT_OUTPUT = Path("research/artifacts/track_c_interaction_null_validation.csv")
DEFAULT_LOG = Path("research/artifacts/track_c_interaction_null_validation_run.log")
DEFAULT_PERMUTATIONS = 1000
DEFAULT_SEED = 20260813
ALPHA = 0.05
REQUIRED_DATA = {"scenario", "label", "return_5d"}
REQUIRED_SEARCH = {
    "scenario", "factor_a", "factor_b", "state_a", "state_b",
    "observations", "down_pct", "flat_pct", "up_pct",
    "mean_return_5d", "median_return_5d",
}

CANDIDATES = (
    ("TREND_UP", "change_pct", "HIGH", "trend_score", "HIGH"),
    ("TREND_UP", "intelligence_score", "HIGH", "trend_score", "HIGH"),
    ("TREND_UP", "relative_strength", "HIGH", "trend_score", "HIGH"),
    ("TREND_UP", "trend_score", "HIGH", "momentum_score", "HIGH"),
    ("TREND_UP", "trend_score", "HIGH", "volatility_score", "HIGH"),
    ("TREND_UP", "trend_score", "HIGH", "volatility_score", "LOW"),
)


class Candidate:
    def __init__(self, scenario, factor_a, state_a, factor_b, state_b):
        self.scenario = scenario
        self.factor_a = factor_a
        self.state_a = state_a
        self.factor_b = factor_b
        self.state_b = state_b

    @property
    def key(self) -> str:
        return f"{self.scenario}|{self.factor_a}={self.state_a}|{self.factor_b}={self.state_b}"


def _require_columns(df: pd.DataFrame, required: set[str], name: str) -> None:
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{name} missing required columns: {', '.join(missing)}")


def _candidate_frame(search: pd.DataFrame) -> pd.DataFrame:
    _require_columns(search, REQUIRED_SEARCH, "interaction search artifact")
    rows = []
    for spec in CANDIDATES:
        c = Candidate(*spec)
        m = (
            (search["scenario"].astype(str) == c.scenario)
            & (search["factor_a"].astype(str) == c.factor_a)
            & (search["state_a"].astype(str) == c.state_a)
            & (search["factor_b"].astype(str) == c.factor_b)
            & (search["state_b"].astype(str) == c.state_b)
        )
        hit = search.loc[m]
        if len(hit) > 1:
            raise ValueError(f"Duplicate candidate definition: {c.key}")
        if len(hit) == 0:
            rows.append({
                "candidate": c.key, "scenario": c.scenario,
                "factor_a": c.factor_a, "state_a": c.state_a,
                "factor_b": c.factor_b, "state_b": c.state_b,
                "observations": 0, "down_pct": np.nan, "flat_pct": np.nan,
                "up_pct": np.nan, "mean_return_5d": np.nan,
                "median_return_5d": np.nan,
            })
        else:
            rows.append(hit.iloc[0].to_dict() | {"candidate": c.key})
    return pd.DataFrame(rows)


def _primary_stat(row: pd.Series) -> float:
    vals = [row["down_pct"], row["flat_pct"], row["up_pct"]]
    vals = [float(v) for v in vals if pd.notna(v)]
    return max(vals) if vals else np.nan


def _null_stats(labels: np.ndarray, sample_size: int, permutations: int, rng: np.random.Generator) -> np.ndarray:
    if sample_size <= 0:
        return np.array([], dtype=float)
    if sample_size > len(labels):
        raise ValueError("Candidate sample size exceeds scenario population.")
    # A fixed candidate mask under a random within-scenario label permutation
    # is exchangeable with drawing the same number of labels from the scenario.
    out = np.empty(permutations, dtype=float)
    n = len(labels)
    for i in range(permutations):
        idx = rng.choice(n, size=sample_size, replace=False)
        chosen = labels[idx]
        counts = np.bincount(chosen, minlength=3)
        out[i] = counts.max() / sample_size * 100.0
    return out


def _empirical_p(null_stats: np.ndarray, observed: float) -> float:
    if not len(null_stats) or not np.isfinite(observed):
        return np.nan
    return (1.0 + float(np.sum(null_stats >= observed))) / (1.0 + len(null_stats))


def _classify(raw_p: float, adjusted_p: float, observations: int) -> tuple[str, str]:
    if observations == 0:
        return "NO_HISTORICAL_EVIDENCE", "RETAIN_FOR_FUTURE_DATA_COLLECTION"
    if not np.isfinite(raw_p):
        return "NULL_NOT_SIGNIFICANT", "INSUFFICIENT_NULL_EVIDENCE"
    if adjusted_p < ALPHA:
        return "NULL_SIGNAL_SURVIVES_MULTIPLE_TESTING", "CONTINUE_INDEPENDENT_OOS_VALIDATION"
    if raw_p < ALPHA:
        return "NULL_SIGNAL_PRESENT_BUT_INSUFFICIENT", "DO_NOT_PROMOTE"
    return "NULL_NOT_SIGNIFICANT", "DO_NOT_PROMOTE"


def validate(
    dataset: pd.DataFrame,
    search: pd.DataFrame,
    *,
    permutations: int = DEFAULT_PERMUTATIONS,
    seed: int = DEFAULT_SEED,
) -> pd.DataFrame:
    if permutations < 100:
        raise ValueError("Use at least 100 permutations for this research layer.")
    _require_columns(dataset, REQUIRED_DATA, "historical dataset")
    data = dataset.copy(deep=True)
    search_copy = search.copy(deep=True)
    data["scenario"] = data["scenario"].astype(str)
    data["label"] = data["label"].astype(str).str.upper()
    data["return_5d"] = pd.to_numeric(data["return_5d"], errors="coerce")
    data = data.dropna(subset=["scenario", "label", "return_5d"])
    data = data[data["label"].isin(["DOWN", "FLAT", "UP"])].copy()

    candidates = _candidate_frame(search_copy)
    scenario_labels = {
        s: g["label"].map({"DOWN": 0, "FLAT": 1, "UP": 2}).to_numpy(dtype=int)
        for s, g in data.groupby("scenario", sort=True)
    }
    rng = np.random.default_rng(seed)
    search_space = len(search_copy.drop_duplicates([
        "scenario", "factor_a", "factor_b", "state_a", "state_b"
    ]))
    rows = []
    for _, r in candidates.iterrows():
        obs = int(pd.to_numeric(r["observations"], errors="coerce") or 0)
        scenario = str(r["scenario"])
        labels = scenario_labels.get(scenario, np.array([], dtype=int))
        observed = _primary_stat(r)
        null = _null_stats(labels, obs, permutations, rng) if obs else np.array([], dtype=float)
        raw_p = _empirical_p(null, observed)
        adjusted = min(1.0, raw_p * search_space) if np.isfinite(raw_p) else np.nan
        result, action = _classify(raw_p, adjusted, obs)
        rows.append({
            "candidate": r["candidate"], "scenario": scenario,
            "factor_a": r["factor_a"], "state_a": r["state_a"],
            "factor_b": r["factor_b"], "state_b": r["state_b"],
            "observations": obs,
            "observed_up_pct": r["up_pct"], "observed_down_pct": r["down_pct"],
            "observed_flat_pct": r["flat_pct"],
            "observed_mean_return_5d": r["mean_return_5d"],
            "observed_median_return_5d": r["median_return_5d"],
            "primary_observed_statistic": observed,
            "null_mean": float(np.mean(null)) if len(null) else np.nan,
            "null_std": float(np.std(null, ddof=1)) if len(null) > 1 else np.nan,
            "null_median": float(np.median(null)) if len(null) else np.nan,
            "null_95th_percentile": float(np.percentile(null, 95)) if len(null) else np.nan,
            "null_99th_percentile": float(np.percentile(null, 99)) if len(null) else np.nan,
            "raw_p_value": raw_p,
            "adjusted_p_value": adjusted,
            "adjustment_method": f"BONFERRONI_{search_space}_SEARCH_TERMS" if search_space else "MULTIPLE_TESTING_NOT_FULLY_ADJUSTED",
            "permutations": permutations if obs else 0,
            "null_seed": seed,
            "null_result": result,
            "research_action": action,
        })
    return pd.DataFrame(rows)


def run(dataset_path=DEFAULT_DATASET, search_path=DEFAULT_SEARCH, output_path=DEFAULT_OUTPUT, log_path=DEFAULT_LOG):
    dataset = pd.read_csv(dataset_path)
    search = pd.read_csv(search_path)
    result = validate(dataset, search)
    output_path = Path(output_path); log_path = Path(log_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    lines = [
        "MARKETBOT - TRACK C INTERACTION NULL VALIDATION",
        "READ-ONLY",
        "SQLite writes: NONE",
        "Production changes: NONE",
        "Weight changes: NONE",
        "Weapon promotion: NONE",
        f"Input observations: {len(dataset)}",
        f"Scenario population rows used: {int((dataset.scenario == 'TREND_UP').sum())}",
        f"Candidates tested: {len(result)}",
        f"Permutations: {DEFAULT_PERMUTATIONS}",
        f"Random seed: {DEFAULT_SEED}",
        f"Search-space terms: {len(search.drop_duplicates(['scenario','factor_a','factor_b','state_a','state_b']))}",
        "",
        result[["candidate","observations","primary_observed_statistic","null_mean","null_95th_percentile","raw_p_value","adjusted_p_value","null_result","research_action"]].to_string(index=False),
        "",
        f"Saved: {output_path.resolve()}",
        "READ-ONLY: no SQLite or production state was modified.",
    ]
    text = "\n".join(lines)
    print(text)
    log_path.write_text(text + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    run()
