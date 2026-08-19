from __future__ import annotations

"""
MarketBot Track C - Cross-Episode Temporal Robustness

Research-only layer.

Purpose:
    Measure whether the six current Track C interaction candidates are
    directionally repeatable across independent OOS scenario episodes.

Important:
    This module deliberately consumes the already-generated
    track_c_interaction_episode_stability_episodes.csv artifact.

    That artifact contains states assigned using the existing chronological
    OOS methodology. We therefore do NOT recompute states from the full
    historical dataset, which would leak future information and would not
    reproduce the established Track C candidate definitions.

No SQLite access.
No production changes.
No candidate promotion.
"""

from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT = BASE_DIR / "research" / "artifacts" / "track_c_interaction_episode_stability_episodes.csv"
OOS_INPUT = BASE_DIR / "research" / "artifacts" / "track_c_interaction_oos_validation.csv"
OUTPUT = BASE_DIR / "research" / "artifacts" / "track_c_cross_episode_temporal_robustness.csv"
LOG = BASE_DIR / "research" / "artifacts" / "track_c_cross_episode_temporal_robustness_run.log"

MIN_EPISODE_OBSERVATIONS = 20

CANDIDATES = [
    ("TREND_UP", "trend_score", "HIGH", "momentum_score", "HIGH"),
    ("TREND_UP", "relative_strength", "HIGH", "trend_score", "HIGH"),
    ("TREND_UP", "change_pct", "HIGH", "trend_score", "HIGH"),
    ("TREND_UP", "trend_score", "HIGH", "volatility_score", "HIGH"),
    ("TREND_UP", "trend_score", "HIGH", "volatility_score", "LOW"),
    ("TREND_UP", "intelligence_score", "HIGH", "trend_score", "HIGH"),
]

KEYS = ["scenario", "factor_a", "state_a", "factor_b", "state_b"]

REQUIRED_EPISODE_COLUMNS = set(KEYS) | {
    "episode_id",
    "test_start",
    "test_end",
    "observations",
    "dominant_outcome",
    "dominant_probability_pct",
    "mean_return_5d",
    "median_return_5d",
    "down_pct",
    "flat_pct",
    "up_pct",
}

REQUIRED_OOS_COLUMNS = set(KEYS) | {
    "observations",
    "up_pct",
    "mean_return_5d",
    "oos_folds",
    "oos_stability",
}


def candidate_name(candidate: tuple[str, str, str, str, str]) -> str:
    scenario, factor_a, state_a, factor_b, state_b = candidate
    return f"{scenario}|{factor_a}={state_a}|{factor_b}={state_b}"


def _validate(df: pd.DataFrame, required: set[str], name: str) -> None:
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{name} missing required columns: {', '.join(missing)}")


def _normalise_keys(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy(deep=True)
    for col in KEYS:
        work[col] = work[col].astype(str).str.strip()
    return work


def _oos_lookup(oos: pd.DataFrame) -> dict[tuple[str, ...], pd.Series]:
    if oos.empty:
        return {}
    work = _normalise_keys(oos)
    return {tuple(row[k] for k in KEYS): row for _, row in work.iterrows()}


def _classify(
    total_observations: int,
    occupied_episodes: int,
    qualifying_episodes: pd.DataFrame,
    concentration_pct: float,
) -> tuple[str, str]:
    if total_observations == 0:
        return (
            "NO_HISTORICAL_EVIDENCE",
            "No historical episode observations for this candidate.",
        )

    if occupied_episodes == 1:
        return (
            "SINGLE_EPISODE",
            "Evidence occurs in only one independent OOS episode.",
        )

    if len(qualifying_episodes) < 2:
        return (
            "RECURRENT_BUT_SPARSE",
            "Candidate recurs, but fewer than two episodes meet the strict >=20 observation threshold.",
        )

    dominant = set(qualifying_episodes["dominant_outcome"].astype(str))
    signs = set(np.sign(pd.to_numeric(
        qualifying_episodes["mean_return_5d"], errors="coerce"
    ).dropna()))

    if (
        len(dominant) == 1
        and signs == {1.0}
        and concentration_pct <= 50.0
    ):
        return (
            "MULTI_EPISODE_STABLE",
            "At least two qualifying independent episodes share the same dominant outcome and positive return sign without excessive concentration.",
        )

    if (
        len(dominant) == 1
        and signs == {-1.0}
        and concentration_pct <= 50.0
    ):
        return (
            "MULTI_EPISODE_STABLE",
            "At least two qualifying independent episodes share the same dominant outcome and negative return sign without excessive concentration.",
        )

    return (
        "MULTI_EPISODE_INCONSISTENT",
        "Multiple qualifying episodes exist, but outcome direction, return sign, or concentration is not sufficiently consistent.",
    )


def analyze(
    episode_data: pd.DataFrame,
    oos: pd.DataFrame,
) -> pd.DataFrame:
    _validate(episode_data, REQUIRED_EPISODE_COLUMNS, "episode_data")
    _validate(oos, REQUIRED_OOS_COLUMNS, "oos")

    episodes = _normalise_keys(episode_data)
    oos_lookup = _oos_lookup(oos)

    results = []

    for candidate in CANDIDATES:
        scenario, factor_a, state_a, factor_b, state_b = candidate
        name = candidate_name(candidate)

        subset = episodes.loc[
            (episodes["scenario"] == scenario)
            & (episodes["factor_a"] == factor_a)
            & (episodes["state_a"] == state_a)
            & (episodes["factor_b"] == factor_b)
            & (episodes["state_b"] == state_b)
        ].copy()

        if not subset.empty:
            subset["observations"] = pd.to_numeric(
                subset["observations"], errors="coerce"
            ).fillna(0).astype(int)
            subset["mean_return_5d"] = pd.to_numeric(
                subset["mean_return_5d"], errors="coerce"
            )
            subset["median_return_5d"] = pd.to_numeric(
                subset["median_return_5d"], errors="coerce"
            )

        total = int(subset["observations"].sum()) if not subset.empty else 0
        occupied = int(len(subset))
        qualifying = subset.loc[
            subset["observations"] >= MIN_EPISODE_OBSERVATIONS
        ].copy()

        if total > 0:
            concentration = (
                float(subset["observations"].max()) / total * 100.0
            )
            means = qualifying["mean_return_5d"].dropna()
            positive_pct = (
                float((means > 0).mean() * 100.0) if len(means) else 0.0
            )
            negative_pct = (
                float((means < 0).mean() * 100.0) if len(means) else 0.0
            )
            mean_episode_return = (
                float(qualifying["mean_return_5d"].mean())
                if len(qualifying) else np.nan
            )
            median_episode_return = (
                float(qualifying["mean_return_5d"].median())
                if len(qualifying) else np.nan
            )
            std_episode_return = (
                float(qualifying["mean_return_5d"].std(ddof=0))
                if len(qualifying) else np.nan
            )
            min_episode_return = (
                float(qualifying["mean_return_5d"].min())
                if len(qualifying) else np.nan
            )
            max_episode_return = (
                float(qualifying["mean_return_5d"].max())
                if len(qualifying) else np.nan
            )
            up_consistency = (
                float((qualifying["dominant_outcome"] == "UP").mean() * 100.0)
                if len(qualifying) else 0.0
            )
            down_consistency = (
                float((qualifying["dominant_outcome"] == "DOWN").mean() * 100.0)
                if len(qualifying) else 0.0
            )
            flat_consistency = (
                float((qualifying["dominant_outcome"] == "FLAT").mean() * 100.0)
                if len(qualifying) else 0.0
            )
            min_obs = int(subset["observations"].min())
            max_obs = int(subset["observations"].max())
            mean_obs = float(subset["observations"].mean())
            median_obs = float(subset["observations"].median())
        else:
            concentration = 0.0
            positive_pct = negative_pct = 0.0
            mean_episode_return = median_episode_return = np.nan
            std_episode_return = min_episode_return = max_episode_return = np.nan
            up_consistency = down_consistency = flat_consistency = 0.0
            min_obs = max_obs = 0
            mean_obs = median_obs = 0.0

        classification, action = _classify(
            total,
            occupied,
            qualifying,
            concentration,
        )

        key = (scenario, factor_a, state_a, factor_b, state_b)
        ov = oos_lookup.get(key)

        if ov is None:
            oos_observations = 0
            oos_up_pct = np.nan
            oos_mean = np.nan
            oos_folds = 0
            oos_stability = "NO_OOS_EVIDENCE"
        else:
            oos_observations = int(float(ov.get("observations", 0) or 0))
            oos_up_pct = float(ov["up_pct"]) if pd.notna(ov.get("up_pct")) else np.nan
            oos_mean = (
                float(ov["mean_return_5d"])
                if pd.notna(ov.get("mean_return_5d"))
                else np.nan
            )
            oos_folds = int(float(ov.get("oos_folds", 0) or 0))
            oos_stability = str(ov.get("oos_stability", "UNKNOWN"))

        results.append({
            "candidate": name,
            "scenario": scenario,
            "factor_a": factor_a,
            "state_a": state_a,
            "factor_b": factor_b,
            "state_b": state_b,
            "episode_count": occupied,
            "occupied_episode_count": occupied,
            "qualifying_episode_count_ge_20": len(qualifying),
            "total_observations": total,
            "min_episode_observations": min_obs,
            "max_episode_observations": max_obs,
            "mean_episode_observations": mean_obs,
            "median_episode_observations": median_obs,
            "episode_up_consistency_pct": up_consistency,
            "episode_down_consistency_pct": down_consistency,
            "episode_flat_consistency_pct": flat_consistency,
            "mean_episode_return_5d": mean_episode_return,
            "median_episode_return_5d": median_episode_return,
            "positive_mean_return_episode_pct": positive_pct,
            "negative_mean_return_episode_pct": negative_pct,
            "mean_return_std": std_episode_return,
            "mean_return_min": min_episode_return,
            "mean_return_max": max_episode_return,
            "max_episode_concentration_pct": concentration,
            "oos_observations": oos_observations,
            "oos_up_pct": oos_up_pct,
            "oos_mean_return_5d": oos_mean,
            "oos_folds": oos_folds,
            "oos_stability": oos_stability,
            "temporal_robustness_classification": classification,
            "research_action": action,
        })

    return (
        pd.DataFrame(results)
        .sort_values(KEYS, kind="mergesort")
        .reset_index(drop=True)
    )


def run(
    input_path: Path = INPUT,
    oos_path: Path = OOS_INPUT,
    output_path: Path = OUTPUT,
) -> pd.DataFrame:
    episode_data = pd.read_csv(input_path)
    oos = pd.read_csv(oos_path)
    result = analyze(episode_data, oos)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)

    lines = [
        "MARKETBOT TRACK C - CROSS-EPISODE TEMPORAL ROBUSTNESS",
        "READ-ONLY: No SQLite access. No production changes. No candidate promotion.",
        f"Candidates analyzed: {len(result)}",
        "",
    ]

    for _, row in result.iterrows():
        lines.append(
            f"{row['candidate']} | "
            f"{row['temporal_robustness_classification']} | "
            f"episodes={row['episode_count']} "
            f"qualifying={row['qualifying_episode_count_ge_20']} "
            f"obs={row['total_observations']} "
            f"oos_folds={row['oos_folds']}"
        )
        lines.append(f"  action: {row['research_action']}")

    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print("MARKETBOT TRACK C - CROSS-EPISODE TEMPORAL ROBUSTNESS")
    print("READ-ONLY: No SQLite access. No production changes. No candidate promotion.")
    result = run()
    print(f"\nCandidates analyzed : {len(result)}")
    print(result[
        ["candidate", "temporal_robustness_classification", "research_action"]
    ].to_string(index=False))
    print(f"\nSaved: {OUTPUT}")
    print(f"Log:   {LOG}")
    print("RESEARCH ONLY")
    print("SQLite writes      : NONE")
    print("Production changes : NONE")
    print("Candidate promotion: NONE")
    print("STATUS             : SUCCESS")
