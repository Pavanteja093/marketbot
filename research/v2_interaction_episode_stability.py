from __future__ import annotations

from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT = BASE_DIR / "research" / "artifacts" / "historical_probability_dataset.csv"
OUTPUT = BASE_DIR / "research" / "artifacts" / "track_c_interaction_episode_stability.csv"
EPISODE_OUTPUT = BASE_DIR / "research" / "artifacts" / "track_c_interaction_episode_stability_episodes.csv"

FEATURES = [
    "change_pct", "intelligence_score", "relative_strength", "trend_score",
    "momentum_score", "volatility_score", "liquidity_score",
]
CLASSES = ["DOWN", "FLAT", "UP"]
MIN_TRAIN_DATES = 60
TEST_DATES = 20
STEP_DATES = 20
MIN_EPISODE_OBSERVATIONS = 20
MIN_REPEAT_EPISODES = 3


def load_dataset() -> pd.DataFrame:
    df = pd.read_csv(INPUT)
    required = {"trade_date", "scenario", "label", "return_5d", *FEATURES}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    for c in FEATURES + ["return_5d"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["label"] = df["label"].astype(str)
    df = df.dropna(subset=["trade_date", "scenario", "label", "return_5d", *FEATURES]).copy()
    return df.sort_values(["trade_date", "index_name"] if "index_name" in df.columns else ["trade_date"]).reset_index(drop=True)


def state_frame(train: pd.DataFrame, test: pd.DataFrame, a: str, b: str):
    threshold_a = train[a].median()
    threshold_b = train[b].median()
    train = train.copy(); test = test.copy()
    train["state_a"] = (train[a] >= threshold_a).map({True: "HIGH", False: "LOW"})
    train["state_b"] = (train[b] >= threshold_b).map({True: "HIGH", False: "LOW"})
    test["state_a"] = (test[a] >= threshold_a).map({True: "HIGH", False: "LOW"})
    test["state_b"] = (test[b] >= threshold_b).map({True: "HIGH", False: "LOW"})
    return train, test


def scenario_baseline(train: pd.DataFrame, scenario: str) -> pd.Series:
    g = train[train["scenario"] == scenario]
    counts = g["label"].value_counts().reindex(CLASSES, fill_value=0).astype(float)
    # Laplace smoothing for finite probabilities.
    return (counts + 1.0) / (counts.sum() + 3.0)


def main() -> int:
    print("\n" + "=" * 78)
    print("MARKETBOT TRACK C - INTERACTION EPISODE STABILITY")
    print("=" * 78)
    print("Question: does an interaction repeat across independent OOS episodes?")

    df = load_dataset()
    dates = sorted(df["trade_date"].dt.normalize().unique())
    print(f"Observations : {len(df):,}")
    print(f"Trading dates: {len(dates):,}")
    print(f"Scenarios    : {df['scenario'].nunique():,}")

    episode_rows = []
    start = MIN_TRAIN_DATES
    episode_id = 0
    while start < len(dates):
        test_end = min(start + TEST_DATES, len(dates))
        train_dates = dates[:start]
        test_dates = dates[start:test_end]
        train = df[df["trade_date"].dt.normalize().isin(train_dates)].copy()
        test = df[df["trade_date"].dt.normalize().isin(test_dates)].copy()
        if test.empty:
            break
        episode_id += 1
        print(f"\nEpisode {episode_id}: {test_dates[0].date()} -> {test_dates[-1].date()}")

        for a, b in combinations(FEATURES, 2):
            _, test_states = state_frame(train, test, a, b)
            for scenario in sorted(test_states["scenario"].unique()):
                s = test_states[test_states["scenario"] == scenario]
                base = scenario_baseline(train, scenario)
                for sa in ["LOW", "HIGH"]:
                    for sb in ["LOW", "HIGH"]:
                        sub = s[(s["state_a"] == sa) & (s["state_b"] == sb)]
                        if len(sub) < MIN_EPISODE_OBSERVATIONS:
                            continue
                        counts = sub["label"].value_counts().reindex(CLASSES, fill_value=0)
                        pct = counts / len(sub)
                        dominant = pct.idxmax()
                        dominant_pct = float(pct.max())
                        baseline_pct = float(base[dominant])
                        episode_rows.append({
                            "episode_id": episode_id,
                            "test_start": test_dates[0].date().isoformat(),
                            "test_end": test_dates[-1].date().isoformat(),
                            "scenario": scenario,
                            "factor_a": a,
                            "factor_b": b,
                            "state_a": sa,
                            "state_b": sb,
                            "observations": int(len(sub)),
                            "dominant_outcome": dominant,
                            "dominant_probability_pct": dominant_pct * 100,
                            "baseline_probability_pct": baseline_pct * 100,
                            "probability_uplift_pct": (dominant_pct - baseline_pct) * 100,
                            "mean_return_5d": float(sub["return_5d"].mean()),
                            "median_return_5d": float(sub["return_5d"].median()),
                            "down_pct": float(pct["DOWN"] * 100),
                            "flat_pct": float(pct["FLAT"] * 100),
                            "up_pct": float(pct["UP"] * 100),
                        })
        start += STEP_DATES

    ep = pd.DataFrame(episode_rows)
    if ep.empty:
        raise RuntimeError("No interaction met the minimum per-episode observation requirement.")

    key = ["scenario", "factor_a", "factor_b", "state_a", "state_b"]
    rows = []
    for k, g in ep.groupby(key):
        # A repeatable signal must preserve its dominant outcome across qualifying episodes.
        dominant_counts = g["dominant_outcome"].value_counts()
        dominant = dominant_counts.index[0]
        repeat = int(dominant_counts.iloc[0])
        episodes = int(len(g))
        dominant_consistency = repeat / episodes
        uplift_positive = int((g["probability_uplift_pct"] > 0).sum())
        return_positive = int((g["mean_return_5d"] > 0).sum())
        mean_uplift = float(g["probability_uplift_pct"].mean())
        mean_return = float(g["mean_return_5d"].mean())
        # Conservative stability classification.
        if episodes >= MIN_REPEAT_EPISODES and dominant_consistency >= 2/3 and uplift_positive >= 2 and return_positive >= 2:
            decision = "REPEATABLE_CANDIDATE"
        elif episodes >= MIN_REPEAT_EPISODES:
            decision = "NOT_REPEATABLE"
        else:
            decision = "INSUFFICIENT_EPISODES"
        rows.append({
            **dict(zip(key, k)),
            "qualifying_episodes": episodes,
            "total_observations": int(g["observations"].sum()),
            "dominant_outcome": dominant,
            "dominant_consistency_pct": dominant_consistency * 100,
            "episodes_with_positive_uplift": uplift_positive,
            "episodes_with_positive_mean_return": return_positive,
            "mean_probability_uplift_pct": mean_uplift,
            "median_probability_uplift_pct": float(g["probability_uplift_pct"].median()),
            "mean_return_5d": mean_return,
            "median_return_5d": float(g["median_return_5d"].median()),
            "min_episode_dominant_probability_pct": float(g["dominant_probability_pct"].min()),
            "max_episode_dominant_probability_pct": float(g["dominant_probability_pct"].max()),
            "decision": decision,
        })
    out = pd.DataFrame(rows)
    out["repeatability_score"] = (
        out["dominant_consistency_pct"] / 100
        * (out["qualifying_episodes"] / max(1, ep["episode_id"].nunique()))
        * (out["episodes_with_positive_uplift"] / out["qualifying_episodes"])
    )
    out = out.sort_values(["decision", "repeatability_score", "total_observations"], ascending=[True, False, False]).reset_index(drop=True)

    print("\n" + "-" * 78)
    print("EPISODE STABILITY RESULTS")
    print("-" * 78)
    print(out.head(40).to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print("\nDecision counts:")
    print(out["decision"].value_counts().to_string())

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False)
    ep.to_csv(EPISODE_OUTPUT, index=False)
    print(f"\nSaved: {OUTPUT}")
    print(f"Saved: {EPISODE_OUTPUT}")
    print("\nRESEARCH ONLY")
    print("SQLite writes      : NONE")
    print("Production changes : NONE")
    print("Weight changes     : NONE")
    print("Promotion         : NONE")
    print("STATUS             : SUCCESS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
