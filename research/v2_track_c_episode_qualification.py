from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

try:
    from research.v2_interaction_episode_stability_multi import (
        CANDIDATES,
        build_scenario_episodes,
        load_dataset,
    )
    from research import v2_interaction_episode_stability_multi as _stability_module
except ModuleNotFoundError:
    from v2_interaction_episode_stability_multi import (
        CANDIDATES,
        build_scenario_episodes,
        load_dataset,
    )
    import v2_interaction_episode_stability_multi as _stability_module

_add_factor_states = getattr(_stability_module, "_add_factor_states", None)

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = BASE_DIR / "research" / "artifacts" / "historical_probability_dataset.csv"
DEFAULT_OUTPUT = BASE_DIR / "research" / "artifacts" / "track_c_episode_qualification.csv"

# These are deliberately conservative and configurable. They do NOT replace the
# strict >=20 observation episode rule; they describe recurrence separately.
DEFAULT_MIN_COVERAGE_PCT = 50.0
DEFAULT_MIN_OCCUPIED_EPISODES = 3
DEFAULT_STRICT_MIN_EPISODES = 2
DEFAULT_MAX_CONCENTRATION_PCT = 50.0



def ensure_factor_states(dataset: pd.DataFrame) -> pd.DataFrame:
    if all(f"{factor}__state" in dataset.columns for factor in (
        "change_pct", "intelligence_score", "relative_strength",
        "trend_score", "momentum_score", "volatility_score", "liquidity_score",
    )):
        return dataset.copy(deep=True)
    if _add_factor_states is not None:
        return _add_factor_states(dataset)
    work = dataset.copy(deep=True)
    for factor in (
        "change_pct", "intelligence_score", "relative_strength",
        "trend_score", "momentum_score", "volatility_score", "liquidity_score",
    ):
        values = pd.to_numeric(work[factor], errors="coerce")
        work[f"{factor}__state"] = pd.cut(
            values,
            bins=[-float("inf"), 40, 60, 80, float("inf")],
            labels=["LOW", "MEDIUM", "HIGH", "VERY_HIGH"],
            right=False,
        ).astype("object")
        work.loc[values.isna(), f"{factor}__state"] = "UNKNOWN"
    return work

def candidate_key(candidate: tuple[str, str, str, str, str]) -> str:
    scenario, factor_a, state_a, factor_b, state_b = candidate
    return (
        f"{scenario}|{factor_a}={state_a}|"
        f"{factor_b}={state_b}"
    )


def _candidate_mask(
    dataset: pd.DataFrame,
    candidate: tuple[str, str, str, str, str],
) -> pd.Series:
    scenario, factor_a, state_a, factor_b, state_b = candidate
    return (
        dataset["scenario"].eq(scenario)
        & dataset[f"{factor_a}__state"].eq(state_a)
        & dataset[f"{factor_b}__state"].eq(state_b)
    )


def _distribution(values: list[int]) -> str:
    return ",".join(str(v) for v in sorted(values))


def classify_candidate(
    *,
    total_observations: int,
    total_scenario_episodes: int,
    occupied_episodes: int,
    coverage_pct: float,
    qualifying_episodes_ge_20: int,
    max_concentration_pct: float,
    min_coverage_pct: float = DEFAULT_MIN_COVERAGE_PCT,
    min_occupied_episodes: int = DEFAULT_MIN_OCCUPIED_EPISODES,
    strict_min_episodes: int = DEFAULT_STRICT_MIN_EPISODES,
    max_concentration_limit_pct: float = DEFAULT_MAX_CONCENTRATION_PCT,
) -> str:
    """Return a research-only evidence class.

    The class is intentionally not a production promotion decision.
    """
    if total_observations == 0:
        return "NO_HISTORICAL_EVIDENCE"

    if occupied_episodes == 0:
        return "SPARSE_NO_EPISODE_COVERAGE"

    if max_concentration_pct > max_concentration_limit_pct:
        return "CONCENTRATED_EVIDENCE"

    if qualifying_episodes_ge_20 >= strict_min_episodes:
        if occupied_episodes >= min_occupied_episodes and coverage_pct >= min_coverage_pct:
            return "EPISODE_STABLE_CANDIDATE"
        return "EPISODE_QUALIFIED_LOW_COVERAGE"

    if occupied_episodes >= min_occupied_episodes and coverage_pct >= min_coverage_pct:
        return "RECURRENT_BUT_SPARSE"

    return "SPARSE_EVIDENCE"


def build_qualification_report(
    dataset: pd.DataFrame,
    episodes: pd.DataFrame,
    *,
    min_episode_observations: int = 20,
    min_coverage_pct: float = DEFAULT_MIN_COVERAGE_PCT,
    min_occupied_episodes: int = DEFAULT_MIN_OCCUPIED_EPISODES,
    strict_min_episodes: int = DEFAULT_STRICT_MIN_EPISODES,
    max_concentration_limit_pct: float = DEFAULT_MAX_CONCENTRATION_PCT,
) -> pd.DataFrame:
    dataset = ensure_factor_states(dataset)
    rows: list[dict] = []

    for candidate in CANDIDATES:
        scenario, factor_a, state_a, factor_b, state_b = candidate
        key = candidate_key(candidate)
        candidate_rows = dataset.loc[_candidate_mask(dataset, candidate)].copy()

        scenario_episodes = episodes[episodes["scenario"].eq(scenario)].copy()
        total_scenario_episodes = len(scenario_episodes)

        per_episode: list[int] = []
        for _, episode in scenario_episodes.sort_values("episode_id").iterrows():
            frame = candidate_rows[
                candidate_rows["trade_date"].between(
                    episode["start_date"], episode["end_date"]
                )
            ]
            n = int(len(frame))
            if n > 0:
                per_episode.append(n)

        occupied = len(per_episode)
        coverage = (
            occupied / total_scenario_episodes * 100.0
            if total_scenario_episodes
            else 0.0
        )
        qualifying = sum(n >= min_episode_observations for n in per_episode)
        max_obs = max(per_episode) if per_episode else 0
        mean_obs = sum(per_episode) / occupied if occupied else 0.0
        median_obs = float(pd.Series(per_episode).median()) if per_episode else 0.0
        concentration = (
            max_obs / len(candidate_rows) * 100.0
            if len(candidate_rows)
            else 0.0
        )

        status = classify_candidate(
            total_observations=len(candidate_rows),
            total_scenario_episodes=total_scenario_episodes,
            occupied_episodes=occupied,
            coverage_pct=coverage,
            qualifying_episodes_ge_20=qualifying,
            max_concentration_pct=concentration,
            min_coverage_pct=min_coverage_pct,
            min_occupied_episodes=min_occupied_episodes,
            strict_min_episodes=strict_min_episodes,
            max_concentration_limit_pct=max_concentration_limit_pct,
        )

        rows.append({
            "candidate": key,
            "scenario": scenario,
            "factor_a": factor_a,
            "state_a": state_a,
            "factor_b": factor_b,
            "state_b": state_b,
            "total_candidate_observations": len(candidate_rows),
            "total_scenario_episodes": total_scenario_episodes,
            "episodes_with_candidate": occupied,
            "episode_coverage_pct": coverage,
            "qualifying_episodes_ge_20": qualifying,
            "max_episode_observations": max_obs,
            "mean_observations_per_occupied_episode": mean_obs,
            "median_observations_per_occupied_episode": median_obs,
            "max_episode_concentration_pct": concentration,
            "episode_observation_distribution": _distribution(per_episode),
            "coverage_gate": (
                "PASS"
                if occupied >= min_occupied_episodes and coverage >= min_coverage_pct
                else "FAIL"
            ),
            "strict_episode_gate": (
                "PASS" if qualifying >= strict_min_episodes else "FAIL"
            ),
            "research_status": status,
        })

    return pd.DataFrame(rows)


def run(
    dataset_path: Path = DEFAULT_DATASET,
    output_path: Path = DEFAULT_OUTPUT,
    *,
    max_gap_days: int = 3,
    min_episode_observations: int = 20,
    min_coverage_pct: float = DEFAULT_MIN_COVERAGE_PCT,
    min_occupied_episodes: int = DEFAULT_MIN_OCCUPIED_EPISODES,
    strict_min_episodes: int = DEFAULT_STRICT_MIN_EPISODES,
    max_concentration_limit_pct: float = DEFAULT_MAX_CONCENTRATION_PCT,
) -> pd.DataFrame:
    if min_episode_observations < 1:
        raise ValueError("min_episode_observations must be positive")
    if not 0 <= min_coverage_pct <= 100:
        raise ValueError("min_coverage_pct must be between 0 and 100")
    if min_occupied_episodes < 1 or strict_min_episodes < 1:
        raise ValueError("episode thresholds must be positive")
    if not 0 <= max_concentration_limit_pct <= 100:
        raise ValueError("max_concentration_limit_pct must be between 0 and 100")

    dataset = ensure_factor_states(load_dataset(dataset_path))
    episodes = build_scenario_episodes(
        dataset,
        max_gap_days=max_gap_days,
        min_episode_days=1,
        min_episode_observations=1,
    )
    report = build_qualification_report(
        dataset,
        episodes,
        min_episode_observations=min_episode_observations,
        min_coverage_pct=min_coverage_pct,
        min_occupied_episodes=min_occupied_episodes,
        strict_min_episodes=strict_min_episodes,
        max_concentration_limit_pct=max_concentration_limit_pct,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(output_path, index=False, lineterminator="\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Track-C episode coverage/qualification diagnostic (research only)."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-gap-days", type=int, default=3)
    parser.add_argument("--min-episode-observations", type=int, default=20)
    parser.add_argument("--min-coverage-pct", type=float, default=DEFAULT_MIN_COVERAGE_PCT)
    parser.add_argument("--min-occupied-episodes", type=int, default=DEFAULT_MIN_OCCUPIED_EPISODES)
    parser.add_argument("--strict-min-episodes", type=int, default=DEFAULT_STRICT_MIN_EPISODES)
    parser.add_argument("--max-concentration-limit-pct", type=float, default=DEFAULT_MAX_CONCENTRATION_PCT)
    args = parser.parse_args()

    report = run(
        args.dataset,
        args.output,
        max_gap_days=args.max_gap_days,
        min_episode_observations=args.min_episode_observations,
        min_coverage_pct=args.min_coverage_pct,
        min_occupied_episodes=args.min_occupied_episodes,
        strict_min_episodes=args.strict_min_episodes,
        max_concentration_limit_pct=args.max_concentration_limit_pct,
    )

    print("=" * 80)
    print("TRACK-C EPISODE QUALIFICATION / COVERAGE")
    print("=" * 80)
    print("Research only: no SQLite access, no production changes, no promotion.")
    print("\nQUALIFICATION RULES")
    print(f"Strict episode evidence     : >= {args.min_episode_observations} observations per episode")
    print(f"Strict repeatability gate   : >= {args.strict_min_episodes} qualifying episodes")
    print(f"Coverage gate                : >= {args.min_occupied_episodes} occupied episodes AND >= {args.min_coverage_pct:.1f}% coverage")
    print(f"Concentration warning        : > {args.max_concentration_limit_pct:.1f}% in one episode")
    print("\nRESULTS")
    print(report[[
        "candidate", "total_candidate_observations", "total_scenario_episodes",
        "episodes_with_candidate", "episode_coverage_pct",
        "qualifying_episodes_ge_20", "max_episode_observations",
        "max_episode_concentration_pct", "coverage_gate",
        "strict_episode_gate", "research_status",
    ]].to_string(index=False))
    print(f"\nSaved: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
