from pathlib import Path
import pandas as pd

from research.v2_interaction_episode_stability_multi import (
    load_dataset,
    load_oos,
    load_candidates,
    build_scenario_episodes,
    _candidate_mask,
)

OUTPUT = Path(
    "research/artifacts/track_c_episode_coverage_diagnostic.csv"
)

dataset = load_dataset()
oos = load_oos()
candidates = load_candidates(oos)

episodes = build_scenario_episodes(
    dataset,
    max_gap_days=3,
    min_episode_days=1,
    min_episode_observations=1,
)

rows = []

for candidate in candidates:
    scenario, factor_a, state_a, factor_b, state_b = candidate

    key = (
        f"{scenario}|"
        f"{factor_a}={state_a}|"
        f"{factor_b}={state_b}"
    )

    candidate_rows = dataset.loc[
        _candidate_mask(dataset, candidate)
    ].copy()

    scenario_episodes = episodes[
        episodes["scenario"].eq(scenario)
    ].copy()

    episode_counts = []

    for _, ep in scenario_episodes.iterrows():
        frame = candidate_rows[
            candidate_rows["trade_date"].between(
                ep["start_date"],
                ep["end_date"],
            )
        ]

        n = len(frame)

        if n > 0:
            episode_counts.append(n)

    total_candidate_obs = len(candidate_rows)
    episodes_with_candidate = len(episode_counts)
    total_scenario_episodes = len(scenario_episodes)

    qualifying_episodes = sum(
        n >= 20 for n in episode_counts
    )

    max_episode_observations = (
        max(episode_counts)
        if episode_counts
        else 0
    )

    mean_observations_per_occupied_episode = (
        sum(episode_counts) / len(episode_counts)
        if episode_counts
        else 0.0
    )

    median_observations_per_occupied_episode = (
        float(pd.Series(episode_counts).median())
        if episode_counts
        else 0.0
    )

    episode_coverage_pct = (
        episodes_with_candidate
        / total_scenario_episodes
        * 100.0
        if total_scenario_episodes
        else 0.0
    )

    observation_concentration_pct = (
        max_episode_observations
        / total_candidate_obs
        * 100.0
        if total_candidate_obs
        else 0.0
    )

    rows.append({
        "candidate": key,
        "scenario": scenario,
        "factor_a": factor_a,
        "state_a": state_a,
        "factor_b": factor_b,
        "state_b": state_b,
        "total_candidate_observations": total_candidate_obs,
        "total_scenario_episodes": total_scenario_episodes,
        "episodes_with_candidate": episodes_with_candidate,
        "episode_coverage_pct": episode_coverage_pct,
        "qualifying_episodes_ge_20": qualifying_episodes,
        "max_episode_observations": max_episode_observations,
        "mean_observations_per_occupied_episode": (
            mean_observations_per_occupied_episode
        ),
        "median_observations_per_occupied_episode": (
            median_observations_per_occupied_episode
        ),
        "max_episode_concentration_pct": (
            observation_concentration_pct
        ),
        "episode_observation_distribution": ",".join(
            str(x) for x in sorted(episode_counts)
        ),
    })

result = pd.DataFrame(rows)

result.to_csv(
    OUTPUT,
    index=False,
)

print("=" * 80)
print("TRACK-C EPISODE COVERAGE DIAGNOSTIC")
print("=" * 80)
print()
print(result.to_string(index=False))
print()
print(f"Saved: {OUTPUT.resolve()}")
print()
print("READ-ONLY:")
print("No SQLite access.")
print("No production changes.")
print("No candidate promotion.")
