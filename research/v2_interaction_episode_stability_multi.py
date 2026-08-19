from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = BASE_DIR / "research" / "artifacts" / "historical_probability_dataset.csv"
DEFAULT_OOS = BASE_DIR / "research" / "artifacts" / "track_c_interaction_oos_validation.csv"
DEFAULT_OUTPUT = BASE_DIR / "research" / "artifacts" / "track_c_multi_candidate_episode_stability.csv"


FACTOR_COLUMNS = (
    "change_pct",
    "intelligence_score",
    "relative_strength",
    "trend_score",
    "momentum_score",
    "volatility_score",
    "liquidity_score",
)


REQUIRED_DATASET_COLUMNS = {
    "trade_date",
    "index_name",
    "scenario",
    "return_5d",
    "change_pct",
    "intelligence_score",
    "relative_strength",
    "trend_score",
    "momentum_score",
    "volatility_score",
    "liquidity_score",
}


REQUIRED_OOS_COLUMNS = {
    "scenario",
    "factor_a",
    "factor_b",
    "state_a",
    "state_b",
    "observations",
    "up_pct",
    "mean_return_5d",
    "oos_folds",
    "oos_stability",
}

CANDIDATES = (
    (
        "TREND_UP",
        "trend_score",
        "HIGH",
        "momentum_score",
        "HIGH",
    ),
    (
        "TREND_UP",
        "relative_strength",
        "HIGH",
        "trend_score",
        "HIGH",
    ),
    (
        "TREND_UP",
        "change_pct",
        "HIGH",
        "trend_score",
        "HIGH",
    ),
    (
        "TREND_UP",
        "trend_score",
        "HIGH",
        "volatility_score",
        "HIGH",
    ),
    (
        "TREND_UP",
        "trend_score",
        "HIGH",
        "volatility_score",
        "LOW",
    ),
    (
        "TREND_UP",
        "intelligence_score",
        "HIGH",
        "trend_score",
        "HIGH",
    ),
)


def _require_columns(
    df: pd.DataFrame,
    required: set[str],
    name: str,
) -> None:
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(
            f"{name} missing required columns: {', '.join(missing)}"
        )


def _factor_state(value: float) -> str:
    if pd.isna(value):
        return "UNKNOWN"
    if value < 40:
        return "LOW"
    if value < 60:
        return "MEDIUM"
    if value < 80:
        return "HIGH"
    return "VERY_HIGH"


def _add_factor_states(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy(deep=True)

    for factor in FACTOR_COLUMNS:
        work[f"{factor}__state"] = work[factor].apply(_factor_state)

    return work


def load_candidates(
    oos: pd.DataFrame,
) -> tuple[tuple[str, str, str, str, str], ...]:
    available = {
        (
            str(row["scenario"]),
            str(row["factor_a"]),
            str(row["state_a"]),
            str(row["factor_b"]),
            str(row["state_b"]),
        )
        for _, row in oos[
            [
                "scenario",
                "factor_a",
                "state_a",
                "factor_b",
                "state_b",
            ]
        ].drop_duplicates().iterrows()
    }

    missing = [candidate for candidate in CANDIDATES if candidate not in available]

    if missing:
        raise ValueError(
            "Required Track C candidates missing from OOS validation: "
            + "; ".join(map(str, missing))
        )

    return CANDIDATES


def _candidate_mask(
    df: pd.DataFrame,
    candidate: tuple[str, str, str, str, str],
) -> pd.Series:
    scenario, factor_a, state_a, factor_b, state_b = candidate

    return (
        df["scenario"].eq(scenario)
        & df[f"{factor_a}__state"].eq(state_a)
        & df[f"{factor_b}__state"].eq(state_b)
    )


def load_dataset(
    path: Path = DEFAULT_DATASET,
) -> pd.DataFrame:
    df = pd.read_csv(path)

    _require_columns(
        df,
        REQUIRED_DATASET_COLUMNS,
        "historical_probability_dataset",
    )

    work = df.copy(deep=True)

    work["trade_date"] = pd.to_datetime(
        work["trade_date"],
        errors="coerce",
    )

    if work["trade_date"].isna().any():
        raise ValueError(
            "historical_probability_dataset contains invalid trade_date values"
        )

    for factor in FACTOR_COLUMNS:
        work[factor] = pd.to_numeric(
            work[factor],
            errors="coerce",
        )

    work["return_5d"] = pd.to_numeric(
        work["return_5d"],
        errors="coerce",
    )

    work = work.dropna(
        subset=["return_5d"]
    ).copy()

    work = _add_factor_states(work)

    return (
        work.sort_values(
            ["trade_date", "index_name"],
            kind="mergesort",
        )
        .reset_index(drop=True)
    )


def load_oos(
    path: Path = DEFAULT_OOS,
) -> pd.DataFrame:
    df = pd.read_csv(path)

    _require_columns(
        df,
        REQUIRED_OOS_COLUMNS,
        "track_c_interaction_oos_validation",
    )

    return df.copy(deep=True)


def build_scenario_episodes(
    dataset: pd.DataFrame,
    *,
    max_gap_days: int = 3,
    min_episode_days: int = 1,
    min_episode_observations: int = 1,
) -> pd.DataFrame:

    if (
        max_gap_days < 1
        or min_episode_days < 1
        or min_episode_observations < 1
    ):
        raise ValueError(
            "episode thresholds must be positive"
        )

    dates = (
        dataset.loc[:, ["trade_date", "scenario"]]
        .drop_duplicates()
        .sort_values(
            ["scenario", "trade_date"],
            kind="mergesort",
        )
    )

    rows = []

    for scenario, group in dates.groupby(
        "scenario",
        sort=True,
    ):
        g = (
            group.sort_values("trade_date")
            .reset_index(drop=True)
        )

        if g.empty:
            continue

        episode = 1
        start = 0

        for i in range(1, len(g)):
            gap = (
                g.loc[i, "trade_date"]
                - g.loc[i - 1, "trade_date"]
            ).days

            if gap > max_gap_days:
                part = g.iloc[start:i]

                obs = int(
                    dataset[
                        (dataset["scenario"] == scenario)
                        & (
                            dataset["trade_date"].isin(
                                part["trade_date"]
                            )
                        )
                    ].shape[0]
                )

                if (
                    len(part) >= min_episode_days
                    and obs >= min_episode_observations
                ):
                    rows.append(
                        {
                            "scenario": scenario,
                            "episode_id": episode,
                            "start_date": part["trade_date"].min(),
                            "end_date": part["trade_date"].max(),
                            "trading_days": len(part),
                            "observations": obs,
                        }
                    )
                    episode += 1

                start = i

        part = g.iloc[start:]

        obs = int(
            dataset[
                (dataset["scenario"] == scenario)
                & (
                    dataset["trade_date"].isin(
                        part["trade_date"]
                    )
                )
            ].shape[0]
        )

        if (
            len(part) >= min_episode_days
            and obs >= min_episode_observations
        ):
            rows.append(
                {
                    "scenario": scenario,
                    "episode_id": episode,
                    "start_date": part["trade_date"].min(),
                    "end_date": part["trade_date"].max(),
                    "trading_days": len(part),
                    "observations": obs,
                }
            )

    return pd.DataFrame(rows)


def _label_counts(
    frame: pd.DataFrame,
) -> tuple[int, int, int]:

    up = int(
        (frame["return_5d"] > 0.5).sum()
    )

    down = int(
        (frame["return_5d"] < -0.5).sum()
    )

    flat = int(
        (
            (frame["return_5d"] >= -0.5)
            & (frame["return_5d"] <= 0.5)
        ).sum()
    )

    return down, flat, up


def _dominant(
    frame: pd.DataFrame,
) -> tuple[str, float]:

    down, flat, up = _label_counts(frame)

    counts = {
        "DOWN": down,
        "FLAT": flat,
        "UP": up,
    }

    outcome = max(
        counts,
        key=lambda k: (
            counts[k],
            {
                "DOWN": 0,
                "FLAT": 1,
                "UP": 2,
            }[k],
        ),
    )

    return (
        outcome,
        counts[outcome] / len(frame) * 100.0,
    )


def _candidate_key(
    candidate: tuple[str, str, str, str, str],
) -> str:
    scenario, factor_a, state_a, factor_b, state_b = candidate

    return (
        f"{scenario}|"
        f"{factor_a}={state_a}|"
        f"{factor_b}={state_b}"
    )


def evaluate_candidates(
    dataset: pd.DataFrame,
    oos: pd.DataFrame,
    episodes: pd.DataFrame,
    candidates: tuple[
        tuple[str, str, str, str, str],
        ...
    ],
    *,
    min_episode_observations: int = 20,
    min_dominant_probability: float = 60.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    episode_rows = []
    summary_rows = []

    for candidate in candidates:

        scenario, factor_a, state_a, factor_b, state_b = candidate

        key = _candidate_key(candidate)

        candidate_rows = dataset.loc[
            _candidate_mask(dataset, candidate)
        ].copy()

        oos_match = oos[
            oos["scenario"].eq(scenario)
            & oos["factor_a"].eq(factor_a)
            & oos["state_a"].eq(state_a)
            & oos["factor_b"].eq(factor_b)
            & oos["state_b"].eq(state_b)
        ].copy()

        if oos_match.empty:
            overall_direction = None
        else:
            overall_direction = str(
                oos_match.iloc[0].get(
                    "dominant_outcome",
                    "",
                )
                or ""
            )

            if overall_direction not in {
                "UP",
                "DOWN",
                "FLAT",
            }:
                up_pct = float(
                    oos_match.iloc[0]["up_pct"]
                )

                mean_ret = float(
                    oos_match.iloc[0]["mean_return_5d"]
                )

                overall_direction = (
                    "UP"
                    if up_pct >= 50
                    else (
                        "DOWN"
                        if mean_ret < 0
                        else "FLAT"
                    )
                )

        applicable = episodes[
            episodes["scenario"].eq(scenario)
        ].copy()

        applicable = applicable.sort_values(
            "episode_id"
        )

        candidate_episode_rows = []

        for _, ep in applicable.iterrows():

            frame = candidate_rows[
                candidate_rows["trade_date"].between(
                    ep["start_date"],
                    ep["end_date"],
                )
            ].copy()

            if len(frame) < min_episode_observations:
                continue

            dominant, prob = _dominant(frame)

            success = (
                overall_direction is not None
                and dominant == overall_direction
                and prob >= min_dominant_probability
            )

            down, flat, up = _label_counts(frame)

            row = {
                "candidate": key,
                "scenario": scenario,
                "factor_a": factor_a,
                "factor_b": factor_b,
                "state_a": state_a,
                "state_b": state_b,
                "episode_id": int(ep["episode_id"]),
                "start_date": ep["start_date"].date().isoformat(),
                "end_date": ep["end_date"].date().isoformat(),
                "trading_days": int(ep["trading_days"]),
                "observations": len(frame),
                "down_count": down,
                "flat_count": flat,
                "up_count": up,
                "down_pct": down / len(frame) * 100,
                "flat_pct": flat / len(frame) * 100,
                "up_pct": up / len(frame) * 100,
                "mean_return_5d": float(
                    frame["return_5d"].mean()
                ),
                "median_return_5d": float(
                    frame["return_5d"].median()
                ),
                "dominant_outcome": dominant,
                "dominant_probability": prob,
                "overall_oos_direction": overall_direction,
                "success": bool(success),
            }

            episode_rows.append(row)
            candidate_episode_rows.append(row)

        epf = pd.DataFrame(candidate_episode_rows)

        scenario_frame = dataset[
            dataset["scenario"].eq(scenario)
        ]

        if epf.empty:

            summary_rows.append(
                {
                    "candidate": key,
                    "scenario": scenario,
                    "factor_a": factor_a,
                    "factor_b": factor_b,
                    "state_a": state_a,
                    "state_b": state_b,
                    "episode_count": 0,
                    "successful_episode_count": 0,
                    "failure_episode_count": 0,
                    "success_rate": None,
                    "observations": len(candidate_rows),
                    "dominant_outcome": overall_direction,
                    "dominant_probability": None,
                    "mean_return_5d": (
                        float(
                            candidate_rows[
                                "return_5d"
                            ].mean()
                        )
                        if len(candidate_rows)
                        else None
                    ),
                    "median_return_5d": (
                        float(
                            candidate_rows[
                                "return_5d"
                            ].median()
                        )
                        if len(candidate_rows)
                        else None
                    ),
                    "baseline_probability": (
                        float(
                            (
                                scenario_frame[
                                    "return_5d"
                                ]
                                > 0.5
                            ).mean()
                            * 100
                        )
                        if len(scenario_frame)
                        else None
                    ),
                    "uplift_vs_baseline": None,
                    "return_uplift_vs_baseline": None,
                    "stability": "INSUFFICIENT_EPISODES",
                    "episode_details": "",
                }
            )

            continue

        successes = int(
            epf["success"].sum()
        )

        count = len(epf)

        baseline_prob = float(
            (
                scenario_frame["return_5d"] > 0.5
            ).mean()
            * 100
        )

        candidate_up = float(
            (
                candidate_rows["return_5d"] > 0.5
            ).mean()
            * 100
        ) if len(candidate_rows) else None

        baseline_mean = float(
            scenario_frame["return_5d"].mean()
        )

        candidate_mean = float(
            candidate_rows["return_5d"].mean()
        )

        if count == 1:
            stability = "SINGLE_EPISODE"
        elif successes == 0:
            stability = "INSUFFICIENT_EPISODES"
        elif successes / count < 0.67:
            stability = "WEAK_REPEATABILITY"
        elif successes / count < 0.80:
            stability = "MODERATE_REPEATABILITY"
        else:
            stability = "STRONG_REPEATABILITY"

        details = ";".join(
            (
                f"E{int(row.episode_id)}:"
                f"{row.start_date}->{row.end_date};"
                f"n={row.observations};"
                f"{row.dominant_outcome}="
                f"{row.dominant_probability:.2f}%;"
                f"success={str(row.success)}"
            )
            for row in epf.itertuples()
        )

        summary_rows.append(
            {
                "candidate": key,
                "scenario": scenario,
                "factor_a": factor_a,
                "factor_b": factor_b,
                "state_a": state_a,
                "state_b": state_b,
                "episode_count": count,
                "successful_episode_count": successes,
                "failure_episode_count": count - successes,
                "success_rate": successes / count * 100,
                "observations": len(candidate_rows),
                "dominant_outcome": overall_direction,
                "dominant_probability": candidate_up,
                "mean_return_5d": candidate_mean,
                "median_return_5d": float(
                    candidate_rows[
                        "return_5d"
                    ].median()
                ),
                "baseline_probability": baseline_prob,
                "uplift_vs_baseline": (
                    candidate_up - baseline_prob
                    if candidate_up is not None
                    else None
                ),
                "return_uplift_vs_baseline": (
                    candidate_mean - baseline_mean
                ),
                "stability": stability,
                "episode_details": details,
            }
        )

    return (
        pd.DataFrame(summary_rows),
        pd.DataFrame(episode_rows),
    )


def run(
    dataset_path: Path = DEFAULT_DATASET,
    oos_path: Path = DEFAULT_OOS,
    output_path: Path = DEFAULT_OUTPUT,
    *,
    max_gap_days: int = 3,
    min_episode_days: int = 1,
    min_episode_observations: int = 20,
    min_dominant_probability: float = 60.0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:

    dataset = load_dataset(dataset_path)
    oos = load_oos(oos_path)

    candidates = load_candidates(oos)

    episodes = build_scenario_episodes(
        dataset,
        max_gap_days=max_gap_days,
        min_episode_days=min_episode_days,
        min_episode_observations=1,
    )

    summary, episode_detail = evaluate_candidates(
        dataset,
        oos,
        episodes,
        candidates,
        min_episode_observations=min_episode_observations,
        min_dominant_probability=min_dominant_probability,
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary.to_csv(
        output_path,
        index=False,
        lineterminator="\n",
    )

    return (
        episodes,
        summary,
        episode_detail,
    )


def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Track-C multi-candidate interaction "
            "episode stability (research only)."
        )
    )

    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
    )

    parser.add_argument(
        "--oos",
        type=Path,
        default=DEFAULT_OOS,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--max-gap-days",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--min-episode-days",
        type=int,
        default=1,
    )

    parser.add_argument(
        "--min-episode-observations",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--min-dominant-probability",
        type=float,
        default=60.0,
    )

    args = parser.parse_args()

    episodes, summary, _ = run(
        args.dataset,
        args.oos,
        args.output,
        max_gap_days=args.max_gap_days,
        min_episode_days=args.min_episode_days,
        min_episode_observations=args.min_episode_observations,
        min_dominant_probability=args.min_dominant_probability,
    )

    dataset = load_dataset(args.dataset)
    oos = load_oos(args.oos)
    candidates = load_candidates(oos)

    print("=" * 80)
    print(
        "MARKETBOT TRACK C - "
        "MULTI-CANDIDATE INTERACTION EPISODE STABILITY"
    )
    print("=" * 80)

    print(
        f"Dataset observations : {len(dataset)}"
    )

    print(
        f"Trading dates        : "
        f"{dataset['trade_date'].nunique()}"
    )

    print(
        f"Candidates tested    : {len(candidates)}"
    )

    print("\nSCENARIO EPISODES")

    print(
        episodes.to_string(index=False)
        if not episodes.empty
        else "NONE"
    )

    print("\nCANDIDATE RESULTS")

    display_columns = [
        "candidate",
        "episode_count",
        "successful_episode_count",
        "failure_episode_count",
        "success_rate",
        "observations",
        "dominant_outcome",
        "dominant_probability",
        "mean_return_5d",
        "baseline_probability",
        "uplift_vs_baseline",
        "stability",
    ]

    print(
        summary[display_columns].to_string(
            index=False
        )
    )

    print(
        f"\nSaved: {args.output.resolve()}"
    )

    print(
        "READ-ONLY: no SQLite access, "
        "no production changes, "
        "no candidate promotion."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
