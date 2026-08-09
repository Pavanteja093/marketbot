from __future__ import annotations

"""MarketBot regime-aware factor model (research candidate only).

This module is deliberately isolated from production scoring.  It fixes a key
limitation of the first Track C prototype: the prototype was labelled
"regime-aware" but learned one global set of weights for each walk-forward
window.  V2 learns factor behaviour conditional on the regime observed on the
prediction date, while shrinking sparse regime estimates toward the global
training estimate.

No future data is used to determine the regime or train weights.
"""

import argparse
import json
import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"
FACTORS = [
    "relative_strength",
    "trend_score",
    "momentum_score",
    "volatility_score",
    "liquidity_score",
]


@dataclass(frozen=True)
class ModelConfig:
    train_days: int = 120
    test_days: int = 20
    min_stocks_per_day: int = 10
    min_global_ic_days: int = 30
    min_regime_ic_days: int = 20
    prior_strength_days: float = 40.0
    max_factor_weight: float = 0.45
    min_factor_weight: float = 0.0
    shrink_reliability: bool = True


@dataclass(frozen=True)
class FactorFit:
    factor: str
    global_ic: float
    regime_ic: float
    shrunk_ic: float
    icir: float
    hit_rate: float
    regime_days: int
    reliability: float
    direction: int
    weight: float


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def load_data(db_path: Path = DB_PATH) -> pd.DataFrame:
    conn = sqlite3.connect(str(db_path))
    try:
        factor_cols = table_columns(conn, "factor_history")
        outcome_cols = table_columns(conn, "prediction_outcomes")
        index_cols = table_columns(conn, "indices_daily")

        missing = [c for c in FACTORS if c not in factor_cols]
        missing += [c for c in ("prediction_date", "index_name", "return_5d") if c not in outcome_cols]
        if "index_name" not in index_cols:
            raise RuntimeError("indices_daily must contain index_name")
        if missing:
            raise RuntimeError("Missing required database columns: " + ", ".join(missing))

        q = """
            SELECT
                p.prediction_date,
                p.index_name,
                p.return_5d,
                f.relative_strength,
                f.trend_score,
                f.momentum_score,
                f.volatility_score,
                f.liquidity_score
            FROM prediction_outcomes p
            INNER JOIN factor_history f
              ON p.prediction_date = f.trade_date
             AND p.index_name = f.index_name
            WHERE p.return_5d IS NOT NULL
            ORDER BY p.prediction_date, p.index_name
        """
        df = pd.read_sql_query(q, conn)

        nifty = pd.read_sql_query(
            """
            SELECT trade_date, close
            FROM indices_daily
            WHERE index_name = 'NIFTY50'
            ORDER BY trade_date
            """,
            conn,
        )
    finally:
        conn.close()

    if df.empty:
        raise RuntimeError("No prediction_outcomes/factor_history rows available")
    if nifty.empty:
        raise RuntimeError("No NIFTY50 rows available")

    df["prediction_date"] = pd.to_datetime(df["prediction_date"], errors="coerce")
    df["return_5d"] = pd.to_numeric(df["return_5d"], errors="coerce")
    for f in FACTORS:
        df[f] = pd.to_numeric(df[f], errors="coerce")
    df = df.dropna(subset=["prediction_date", "index_name", "return_5d"]).copy()

    nifty["trade_date"] = pd.to_datetime(nifty["trade_date"], errors="coerce")
    nifty["close"] = pd.to_numeric(nifty["close"], errors="coerce")
    nifty = nifty.dropna(subset=["trade_date", "close"]).drop_duplicates("trade_date").sort_values("trade_date")
    nifty["ret_1d"] = nifty["close"].pct_change()
    nifty["vol_20"] = nifty["ret_1d"].rolling(20, min_periods=20).std() * np.sqrt(252)
    nifty["sma20"] = nifty["close"].rolling(20, min_periods=20).mean()
    nifty["sma50"] = nifty["close"].rolling(50, min_periods=50).mean()
    expanding = nifty["vol_20"].expanding(min_periods=60)
    nifty["vol_q25"] = expanding.quantile(0.25)
    nifty["vol_q75"] = expanding.quantile(0.75)

    def classify(row: pd.Series) -> str:
        vol = row["vol_20"]
        sma20, sma50, close = row["sma20"], row["sma50"], row["close"]
        if pd.notna(vol) and pd.notna(row["vol_q75"]) and vol >= row["vol_q75"]:
            if pd.notna(sma20) and pd.notna(sma50):
                return "HIGH_VOL_UP" if sma20 >= sma50 else "HIGH_VOL_DOWN"
        if pd.notna(vol) and pd.notna(row["vol_q25"]) and vol <= row["vol_q25"]:
            return "LOW_VOL"
        if pd.notna(sma20) and pd.notna(sma50):
            if close > sma20 > sma50:
                return "TREND_UP"
            if close < sma20 < sma50:
                return "TREND_DOWN"
        return "SIDEWAYS"

    nifty["regime"] = nifty.apply(classify, axis=1)
    regime = nifty[["trade_date", "regime"]].copy()
    df = df.merge(regime, left_on="prediction_date", right_on="trade_date", how="left").drop(columns=["trade_date"])
    return df


def daily_ic(frame: pd.DataFrame, factor: str) -> pd.Series:
    vals, dates = [], []
    for date, group in frame.groupby("prediction_date", sort=True):
        x = pd.to_numeric(group[factor], errors="coerce")
        y = pd.to_numeric(group["return_5d"], errors="coerce")
        valid = x.notna() & y.notna()
        if valid.sum() < 5:
            continue
        xr = x[valid].rank(method="average")
        yr = y[valid].rank(method="average")
        if xr.nunique() < 2 or yr.nunique() < 2:
            continue
        ic = xr.corr(yr)
        if pd.notna(ic):
            dates.append(date)
            vals.append(float(ic))
    return pd.Series(vals, index=pd.DatetimeIndex(dates), dtype=float)


def _reliability(ics: pd.Series, days: int, cfg: ModelConfig) -> float:
    if days <= 0 or ics.empty:
        return 0.0
    std = float(ics.std(ddof=1)) if len(ics) > 1 else np.nan
    mean = float(ics.mean())
    icir = abs(mean / std * np.sqrt(len(ics))) if pd.notna(std) and std > 0 else 0.0
    hit = float((ics > 0).mean())
    sample = min(1.0, days / max(cfg.min_regime_ic_days, 1))
    stability = min(1.0, icir / 2.0)
    hit_quality = 0.5 + 0.5 * abs(hit - 0.5) * 2.0
    return float(np.clip(sample * max(stability, 0.10) * hit_quality, 0.0, 1.0))


def fit_weights(train: pd.DataFrame, regime: str, cfg: ModelConfig) -> tuple[dict[str, float], dict[str, FactorFit]]:
    global_ics = {f: daily_ic(train, f) for f in FACTORS}
    regime_train = train[train["regime"] == regime].copy()
    regime_ics = {f: daily_ic(regime_train, f) for f in FACTORS}

    fits: Dict[str, FactorFit] = {}
    raw = {}
    for factor in FACTORS:
        g = global_ics[factor]
        r = regime_ics[factor]
        g_mean = float(g.mean()) if len(g) >= cfg.min_global_ic_days else 0.0
        r_mean = float(r.mean()) if len(r) >= cfg.min_regime_ic_days else g_mean
        n = len(r)
        alpha = n / (n + cfg.prior_strength_days) if n > 0 else 0.0
        shrunk = alpha * r_mean + (1.0 - alpha) * g_mean
        reliability = _reliability(r if n >= cfg.min_regime_ic_days else g, n if n >= cfg.min_regime_ic_days else len(g), cfg)
        if not cfg.shrink_reliability:
            reliability = 1.0
        raw_weight = abs(shrunk) * reliability
        direction = 1 if shrunk >= 0 else -1
        std = float(r.std(ddof=1)) if len(r) > 1 else np.nan
        icir = abs(float(r.mean()) / std * np.sqrt(len(r))) if pd.notna(std) and std > 0 else 0.0
        hit = float((r > 0).mean()) if len(r) else 0.5
        raw[factor] = raw_weight
        fits[factor] = FactorFit(
            factor=factor,
            global_ic=g_mean,
            regime_ic=r_mean,
            shrunk_ic=shrunk,
            icir=icir,
            hit_rate=hit,
            regime_days=n,
            reliability=reliability,
            direction=direction,
            weight=0.0,
        )

    total = sum(raw.values())
    if total <= 0:
        weights = {f: 1.0 / len(FACTORS) for f in FACTORS}
    else:
        weights = {f: raw[f] / total for f in FACTORS}

    # Cap concentration and renormalize. Iterative redistribution keeps the
    # model from becoming a one-factor bet when a regime is sparse/noisy.
    for _ in range(10):
        excess = sum(max(0.0, weights[f] - cfg.max_factor_weight) for f in FACTORS)
        if excess <= 1e-12:
            break
        capped = {f: min(weights[f], cfg.max_factor_weight) for f in FACTORS}
        room = [f for f in FACTORS if capped[f] < cfg.max_factor_weight - 1e-12]
        room_total = sum(capped[f] for f in room)
        if not room:
            weights = capped
            break
        for f in room:
            share = capped[f] / room_total if room_total > 0 else 1.0 / len(room)
            capped[f] += excess * share
        weights = capped

    total = sum(weights.values())
    weights = {f: weights[f] / total for f in FACTORS}
    for f in FACTORS:
        old = fits[f]
        fits[f] = FactorFit(**{**asdict(old), "weight": weights[f]})
    return weights, fits


def score_frame(frame: pd.DataFrame, weights: dict[str, float], fits: dict[str, FactorFit]) -> pd.Series:
    out = pd.Series(np.nan, index=frame.index, dtype=float)
    for _, group in frame.groupby("prediction_date", sort=False):
        score = pd.Series(0.0, index=group.index)
        for factor in FACTORS:
            x = pd.to_numeric(group[factor], errors="coerce")
            ranks = x.rank(method="average", pct=True)
            centered = ranks - 0.5
            score = score.add(centered * weights[factor] * fits[factor].direction, fill_value=0.0)
        out.loc[group.index] = score
    return out


def quintile_spread(frame: pd.DataFrame, min_stocks: int) -> tuple[float, float, float, int]:
    top, bottom = [], []
    for _, day in frame.groupby("prediction_date", sort=True):
        work = day[["candidate_score", "return_5d"]].dropna()
        if len(work) < min_stocks:
            continue
        q = pd.qcut(work["candidate_score"].rank(method="first"), 5, labels=False)
        if q.nunique() < 5:
            continue
        top.append(float(work.loc[q == 4, "return_5d"].mean()))
        bottom.append(float(work.loc[q == 0, "return_5d"].mean()))
    if not top:
        return np.nan, np.nan, np.nan, 0
    top_m, bottom_m = float(np.mean(top)), float(np.mean(bottom))
    return top_m, bottom_m, top_m - bottom_m, len(top)


def run_walk_forward(df: pd.DataFrame, cfg: ModelConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = sorted(df["prediction_date"].dropna().unique())
    rows, fits_rows = [], []
    start = cfg.train_days
    window = 0
    while start + cfg.test_days <= len(dates):
        train_dates = dates[start - cfg.train_days:start]
        test_dates = dates[start:start + cfg.test_days]
        train = df[df["prediction_date"].isin(train_dates)].copy()
        test = df[df["prediction_date"].isin(test_dates)].copy()
        regime_values = test["regime"].dropna().value_counts()
        if regime_values.empty:
            start += cfg.test_days
            continue
        regime = str(regime_values.index[0])
        weights, fits = fit_weights(train, regime, cfg)
        test["candidate_score"] = score_frame(test, weights, fits)
        top, bottom, spread, days = quintile_spread(test, cfg.min_stocks_per_day)
        window += 1
        rows.append({
            "window": window,
            "train_start": train_dates[0],
            "train_end": train_dates[-1],
            "test_start": test_dates[0],
            "test_end": test_dates[-1],
            "test_regime": regime,
            "top_return": top,
            "bottom_return": bottom,
            "spread": spread,
            "valid_test_days": days,
        })
        for fit in fits.values():
            row = asdict(fit)
            row.update({"window": window, "test_regime": regime})
            fits_rows.append(row)
        start += cfg.test_days
    return pd.DataFrame(rows), pd.DataFrame(fits_rows)


def summarize(results: pd.DataFrame) -> dict:
    spreads = pd.to_numeric(results.get("spread", pd.Series(dtype=float)), errors="coerce").dropna()
    if spreads.empty:
        return {"windows": 0, "average_spread": None, "median_spread": None, "positive_window_pct": None, "worst_window": None}
    return {
        "windows": int(len(spreads)),
        "average_spread": float(spreads.mean()),
        "median_spread": float(spreads.median()),
        "positive_window_pct": float((spreads > 0).mean() * 100.0),
        "worst_window": float(spreads.min()),
        "best_window": float(spreads.max()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MarketBot regime-aware factor walk-forward V2")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--train-days", type=int, default=120)
    parser.add_argument("--test-days", type=int, default=20)
    parser.add_argument("--output", type=Path, default=BASE_DIR / "research" / "artifacts")
    args = parser.parse_args()

    cfg = ModelConfig(train_days=args.train_days, test_days=args.test_days)
    df = load_data(args.db)
    results, fits = run_walk_forward(df, cfg)
    summary = summarize(results)

    args.output.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.output / "regime_aware_v2_walk_forward.csv", index=False)
    fits.to_csv(args.output / "regime_aware_v2_factor_fits.csv", index=False)
    (args.output / "regime_aware_v2_summary.json").write_text(json.dumps({"config": asdict(cfg), "summary": summary}, indent=2, default=str), encoding="utf-8")

    print("\n" + "=" * 79)
    print("MARKETBOT TRACK C2 - REGIME-AWARE SHRINKAGE WALK-FORWARD")
    print("=" * 79)
    print(f"Observations : {len(df):,}")
    print(f"Windows      : {summary['windows']}")
    if results.empty:
        print("No valid windows.")
        return
    print(results.round(4).to_string(index=False))
    print(f"\nAverage spread      : {summary['average_spread']:+.4f}%")
    print(f"Median spread       : {summary['median_spread']:+.4f}%")
    print(f"Positive window %   : {summary['positive_window_pct']:.2f}%")
    print(f"Worst window        : {summary['worst_window']:+.4f}%")
    print("\nResearch-only candidate. Production scoring has NOT been changed.")


if __name__ == "__main__":
    main()
