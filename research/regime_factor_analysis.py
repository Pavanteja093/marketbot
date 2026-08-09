from __future__ import annotations

import numpy as np
import pandas as pd

from research.research_data import FACTORS, daily_ic, load_research_data, merge_regime


MIN_DAYS = 10


def analyze() -> None:
    print("\n" + "=" * 79)
    print("MARKETBOT TRACK A - REGIME CONDITIONED FACTOR ANALYSIS")
    print("=" * 79)

    df = merge_regime(load_research_data())

    print(f"\nObservations : {len(df):,}")
    print(f"Trading dates : {df['prediction_date'].nunique():,}")
    print(f"Regimes      : {df['regime'].nunique(dropna=True):,}")

    print("\n===== REGIME DISTRIBUTION =====")
    regime_counts = (
        df.groupby("regime")["prediction_date"]
        .nunique()
        .sort_values(ascending=False)
    )
    print(regime_counts.to_string())

    rows = []

    for regime, regime_df in df.dropna(subset=["regime"]).groupby("regime"):
        for factor in FACTORS:
            ics = daily_ic(regime_df, factor)
            if len(ics) < MIN_DAYS:
                rows.append(
                    {
                        "regime": regime,
                        "factor": factor,
                        "days": len(ics),
                        "mean_ic": np.nan,
                        "median_ic": np.nan,
                        "icir": np.nan,
                        "positive_pct": np.nan,
                        "spread": np.nan,
                    }
                )
                continue

            mean_ic = float(ics.mean())
            std_ic = float(ics.std(ddof=1))
            icir = (
                mean_ic / std_ic * np.sqrt(len(ics))
                if std_ic > 0
                else np.nan
            )

            # Spread is averaged across regime-days, not pooled across all stocks.
            spread_values = []
            for _, day in regime_df.groupby("prediction_date"):
                x = pd.to_numeric(day[factor], errors="coerce")
                y = pd.to_numeric(day["return_5d"], errors="coerce")
                valid = x.notna() & y.notna()
                if valid.sum() < 10:
                    continue
                w = pd.DataFrame({"x": x[valid], "y": y[valid]})
                w["q"] = pd.qcut(
                    w["x"].rank(method="first"),
                    5,
                    labels=False,
                )
                if w["q"].nunique() == 5:
                    spread_values.append(
                        float(
                            w.loc[w["q"] == 4, "y"].mean()
                            - w.loc[w["q"] == 0, "y"].mean()
                        )
                    )

            rows.append(
                {
                    "regime": regime,
                    "factor": factor,
                    "days": len(ics),
                    "mean_ic": mean_ic,
                    "median_ic": float(ics.median()),
                    "icir": icir,
                    "positive_pct": float((ics > 0).mean() * 100),
                    "spread": (
                        float(np.mean(spread_values))
                        if spread_values
                        else np.nan
                    ),
                }
            )

    result = pd.DataFrame(rows)

    print("\n===== REGIME FACTOR IC =====")
    if result.empty:
        print("No regime-conditioned observations.")
        return

    print(
        result.sort_values(
            ["regime", "mean_ic"],
            ascending=[True, False],
        ).round(4).to_string(index=False)
    )

    print("\n===== REGIME FACTOR DIRECTIONS =====")
    for regime in result["regime"].dropna().unique():
        subset = result[result["regime"] == regime].copy()
        subset = subset.dropna(subset=["mean_ic"])
        print(f"\n{regime}")
        for _, row in subset.sort_values("mean_ic", ascending=False).iterrows():
            direction = "POSITIVE" if row["mean_ic"] > 0 else "NEGATIVE"
            print(
                f"{row['factor']:<22}"
                f" {direction:<9}"
                f" MeanIC={row['mean_ic']:+.5f}"
                f" ICIR={row['icir']:+.3f}"
                f" PosDays={row['positive_pct']:.1f}%"
                f" Spread={row['spread']:+.4f}%"
            )

    print("\n===== TRACK A VERDICT =====")
    stable = []
    for factor in FACTORS:
        subset = result[result["factor"] == factor].dropna(subset=["mean_ic"])
        if subset.empty:
            continue
        positive_regimes = int((subset["mean_ic"] > 0).sum())
        negative_regimes = int((subset["mean_ic"] < 0).sum())
        stable.append((factor, positive_regimes, negative_regimes))

    for factor, pos, neg in stable:
        if pos > neg:
            verdict = "MORE OFTEN POSITIVE"
        elif neg > pos:
            verdict = "MORE OFTEN NEGATIVE"
        else:
            verdict = "MIXED"
        print(f"{factor:<22} {verdict} ({pos} positive regimes / {neg} negative regimes)")

    print(
        "\nResearch only. No production weights or scoring logic were changed."
    )


if __name__ == "__main__":
    analyze()
