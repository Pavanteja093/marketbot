import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.regime_aware_walk_forward import build_regimes, Config, evaluate_test_day


def test_regime_builder():
    dates = pd.date_range("2025-01-01", periods=120, freq="D")
    close = np.linspace(100, 150, len(dates))
    df = pd.DataFrame({"trade_date": dates, "close": close})

    result = build_regimes(df)

    assert len(result) == 120
    assert "regime" in result.columns
    assert result["regime"].notna().all()


def test_daily_quintile_evaluation():
    n = 25
    df = pd.DataFrame(
        {
            "candidate_score": np.arange(n, dtype=float),
            "return_5d": np.linspace(-1, 2, n),
        }
    )

    result = evaluate_test_day(df, min_stocks=10)

    assert result is not None
    assert result["spread"] > 0


def test_config_defaults():
    cfg = Config()
    assert cfg.train_days == 120
    assert cfg.test_days == 20
    assert cfg.max_factor_weight == 0.45


if __name__ == "__main__":
    test_regime_builder()
    test_daily_quintile_evaluation()
    test_config_defaults()
    print("ALL C2.1 TESTS PASSED")
