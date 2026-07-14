import pandas as pd



def rank_signals(df):

    if len(df) == 0:
        return df

    ranked = df.copy()

    ranked["volume_rank"] = (
        ranked["volume_expansion"]
        .rank(pct=True)
    )

    ranked["sector_rank"] = (
        ranked["sector_strength"]
        .rank(pct=True)
    )

    ranked["intel_rank"] = (
        ranked["intelligence_score"]
        .rank(pct=True)
    )

    ranked["position_rank"] = (
        1 -
        ranked["position_52w"]
        .rank(pct=True)
    )

    ranked["ranking_score"] = (

        ranked["volume_rank"] * 0.40 +

        ranked["sector_rank"] * 0.30 +

        ranked["intel_rank"] * 0.20 +

        ranked["position_rank"] * 0.10

    )

    ranked = ranked.sort_values(
        "ranking_score",
        ascending=False
    )

    return ranked