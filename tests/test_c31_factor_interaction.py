import numpy as np
import pandas as pd

from research.factor_interaction_analyzer import (
    FACTORS,
    build_interactions,
    cross_sectional_rank,
    interaction_diagnostics,
    quintile_spreads,
)


def make_data():
    rows = []
    for day in range(12):
        for symbol in range(10):
            x = symbol / 9
            rows.append({
                "trade_date": f"2026-01-{day + 1:02d}",
                "entity": f"S{symbol}",
                "relative_strength": x,
                "trend_score": x,
                "momentum_score": x,
                "volatility_score": 1 - x,
                "liquidity_score": 0.5 + x * 0.1,
                "return_5d": x * 2.0 + np.random.default_rng(day + symbol).normal(0, 0.05),
            })
    return pd.DataFrame(rows)


def main():
    df = make_data()

    ranked = cross_sectional_rank(df)
    assert all(f"{f}__rank" in ranked.columns for f in FACTORS)

    interaction_df, names = build_interactions(df)
    assert len(names) == 10
    assert all(name in interaction_df.columns for name in names)

    diagnostics = interaction_diagnostics(interaction_df, names)
    assert not diagnostics.empty
    assert {"interaction", "mean_ic", "positive_pct"}.issubset(diagnostics.columns)

    spreads = quintile_spreads(interaction_df, names)
    assert not spreads.empty
    assert "q5_minus_q1" in spreads.columns

    print("ALL C3.1 TESTS PASSED")


if __name__ == "__main__":
    main()
