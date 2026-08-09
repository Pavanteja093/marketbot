from __future__ import annotations

import numpy as np
import pandas as pd

from research.research_data import FACTORS, daily_ic, load_research_data, quintile_spread


ROLLING_DAYS = 60


def analyze() -> None:
    print("\n" + "=" * 79)
    print("MARKETBOT TRACK B - FACTOR SIGNAL STRENGTH")
    print("=" * 79)

    df = load_research_data()

    print(f"\nObservations : {len(df):,}")
    print(f"Trading dates : {df['prediction_date'].nunique():,}")
    print(f"Symbols       : {df['index_name'].nunique():,}")

    rows = []

    for factor in FACTORS:
        ics = daily_ic(df, factor)

        if ics.empty:
            continue

        std_ic = float(ics.std(ddof=1))
        mean_ic = float(ics.mean())
        icir = (
            mean_ic / std_ic * np.sqrt(len(ics))
            if std_ic > 0
            else np.nan
        )

        rolling = ics.rolling(ROLLING_DAYS, min_periods=max(20, ROLLING_DAYS // 2))
        rolling_mean = rolling.mean().dropna()

        spread = quintile_spread(df, factor)

        rows.append(
            {
                "factor": factor,
                "days": len(ics),
                "mean_ic": mean_ic,
                "median_ic": float(ics.median()),
                "std_ic": std_ic,
                "icir": icir,
                "positive_pct": float((ics > 0).mean() * 100),
                "negative_pct": float((ics < 0).mean() * 100),
                "abs_mean_ic": float(ics.abs().mean()),
                "min_ic": float(ics.min()),
                "max_ic": float(ics.max()),
                "q5_minus_q1_spread": spread,
                "rolling60_mean": (
                    float(rolling_mean.iloc[-1])
                    if not rolling_mean.empty
                    else np.nan
                ),
                "rolling60_min": (
                    float(rolling_mean.min())
                    if not rolling_mean.empty
                    else np.nan
                ),
                "rolling60_max": (
                    float(rolling_mean.max())
                    if not rolling_mean.empty
                    else np.nan
                ),
            }
        )

    result = pd.DataFrame(rows)

    print("\n===== FULL-SAMPLE SIGNAL STRENGTH =====")
    print(
        result.sort_values(
            "abs_mean_ic",
            ascending=False,
        ).round(5).to_string(index=False)
    )

    print("\n===== CURRENT 60-DAY SIGNAL STATE =====")
    current = result[
        [
            "factor",
            "rolling60_mean",
            "rolling60_min",
            "rolling60_max",
            "positive_pct",
            "icir",
        ]
    ].copy()

    print(current.round(5).to_string(index=False))

    print("\n===== SIGNAL QUALITY RANK =====")
    ranked = result.copy()
    ranked["quality_score"] = (
        ranked["abs_mean_ic"].fillna(0)
        * np.sqrt(ranked["days"].clip(lower=1))
    )
    print(
        ranked[
            ["factor", "quality_score", "mean_ic", "icir", "positive_pct"]
        ]
        .sort_values("quality_score", ascending=False)
        .round(5)
        .to_string(index=False)
    )

    print("\n===== TRACK B VERDICT =====")
    print(
        "Do not rank factors by mean IC alone. "
        "Use direction, ICIR, hit rate, rolling stability and "
        "top-minus-bottom spread together."
    )
    print(
        "Research only. No production weights or scoring logic were changed."
    )


if __name__ == "__main__":
    analyze()
