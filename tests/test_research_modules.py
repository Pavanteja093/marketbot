from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from research.regime_aware_model_v2 import ModelConfig, fit_weights, score_frame, quintile_spread, summarize
from research.candidate_gate import evaluate

FACTORS = ["relative_strength", "trend_score", "momentum_score", "volatility_score", "liquidity_score"]


def make_frame(seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2026-01-01", periods=45, freq="D")
    rows = []
    for d in dates:
        for i in range(20):
            trend = rng.normal()
            ret = 0.8 * trend + rng.normal(scale=0.5)
            rows.append({
                "prediction_date": d,
                "index_name": f"S{i:02d}",
                "return_5d": ret,
                "regime": "TREND_UP",
                "relative_strength": rng.normal(),
                "trend_score": trend,
                "momentum_score": rng.normal(),
                "volatility_score": rng.normal(),
                "liquidity_score": rng.normal(),
            })
    return pd.DataFrame(rows)


def test_fit_weights_sum_to_one_and_cap():
    df = make_frame()
    cfg = ModelConfig(min_regime_ic_days=10, min_global_ic_days=10, max_factor_weight=0.45)
    weights, fits = fit_weights(df, "TREND_UP", cfg)
    assert abs(sum(weights.values()) - 1.0) < 1e-9
    assert all(0 <= w <= 0.45 + 1e-9 for w in weights.values())
    assert fits["trend_score"].direction == 1
    assert weights["trend_score"] > weights["liquidity_score"]


def test_score_is_cross_sectional():
    df = make_frame().tail(20).copy()
    cfg = ModelConfig(min_regime_ic_days=10, min_global_ic_days=10)
    weights, fits = fit_weights(make_frame(), "TREND_UP", cfg)
    scores = score_frame(df, weights, fits)
    assert scores.notna().all()
    assert scores.nunique() > 5


def test_quintile_spread():
    df = make_frame().tail(20).copy()
    df["candidate_score"] = df["trend_score"]
    top, bottom, spread, days = quintile_spread(df, 10)
    assert days == 1
    assert spread > 0
    assert top > bottom


def test_summary_and_gate():
    results = pd.DataFrame({"spread": [0.2, 0.3, -0.1, 0.4, 0.2]})
    summary = summarize(results)
    assert summary["windows"] == 5
    gate = evaluate(results)
    assert gate["decision"] in {"PASS", "REVIEW", "FAIL"}


if __name__ == "__main__":
    test_fit_weights_sum_to_one_and_cap()
    test_score_is_cross_sectional()
    test_quintile_spread()
    test_summary_and_gate()
    print("ALL TESTS PASSED")
