import numpy as np
import pandas as pd

from research.regime_aware_walk_forward import (
    build_regimes,
    _cap_weights,
    evaluate_day,
)


def test_regime_builder():
    dates = pd.date_range("2025-01-01", periods=140, freq="D")
    close = np.linspace(100, 160, len(dates))
    result = build_regimes(
        pd.DataFrame(
            {"trade_date": dates, "close": close}
        )
    )
    assert len(result) == 140
    assert result["regime"].notna().all()


def test_weight_cap():
    weights = _cap_weights(
        {
            "relative_strength": 0.01,
            "trend_score": 1.0,
            "momentum_score": 0.2,
            "volatility_score": 0.1,
            "liquidity_score": 0.9,
        }
    )
    assert abs(sum(weights.values()) - 1.0) < 1e-9
    assert max(weights.values()) <= 0.45 + 1e-9


def test_daily_evaluation():
    n = 25
    frame = pd.DataFrame(
        {
            "candidate_score": np.arange(n, dtype=float),
            "return_5d": np.linspace(-1.0, 2.0, n),
        }
    )
    result = evaluate_day(frame)
    assert result is not None
    assert result["spread"] > 0


if __name__ == "__main__":
    test_regime_builder()
    test_weight_cap()
    test_daily_evaluation()
    print("ALL C2.2 TESTS PASSED")
