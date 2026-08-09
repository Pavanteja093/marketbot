from __future__ import annotations

"""MarketBot Track C2.1 - leakage-safe regime-aware walk-forward.

Key correction versus the first C2 implementation:
- The regime used for each test date is calculated using NIFTY50 data available
  on or before that date.
- The model never selects a single regime from the future test window.
- Training factor IC is estimated separately for each regime.
- Sparse regime estimates are shrunk toward the global training estimate.
- Each test date is scored with the weights for THAT DATE'S regime.
- Production scoring is never modified.

This is a research module only.
"""

import argparse
import json
import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path

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
class Config:
    train_days: int = 120
    test_days: int = 20
    min_stocks_per_day: int = 10
    min_global_ic_days: int = 30
    min_regime_ic_days: int = 20
    prior_strength_days: float = 40.0
    max_factor_weight: float = 0.45


def table_columns(conn, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def build_regimes(index_df: pd.DataFrame) -> pd.DataFrame:
    x = index_df.copy()
    x["trade_date"] = pd.to_datetime(x["trade_date"], errors="coerce")
    x["close"] = pd.to_numeric(x["close"], errors="coerce")
    x = x.dropna(subset=["trade_date", "close"]).drop_duplicates("trade_date")
    x = x.sort_values("trade_date").reset_index(drop=True)

    x["ret_1d"] = x["close"].pct_change()
    x["vol_20"] = x["ret_1d"].rolling(20, min_periods=20).std() * np.sqrt(252)
    x["sma20"] = x["close"].rolling(20, min_periods=20).mean()
    x["sma50"] = x["close"].rolling(50, min_periods=50).mean()

    # Expanding thresholds use only observations available through the date.
    x["vol_q25"] = x["vol_20"].expanding(min_periods=60).quantile(0.25)
    x["vol_q75"] = x["vol_20"].expanding(min_periods=60).quantile(0.75)

    regimes = []
    for _, row in x.iterrows():
        vol = row["vol_20"]
        sma20, sma50, close = row["sma20"], row["sma50"], row["close"]
        q25, q75 = row["vol_q25"], row["vol_q75"]

        regime = "SIDEWAYS"

        if pd.notna(vol) and pd.notna(q75) and vol >= q75:
            if pd.notna(sma20) and pd.notna(sma50):
                regime = "HIGH_VOL_UP" if sma20 >= sma50 else "HIGH_VOL_DOWN"
        elif pd.notna(vol) and pd.notna(q25) and vol <= q25:
            regime = "LOW_VOL"
        elif pd.notna(sma20) and pd.notna(sma50):
            if close > sma20 > sma50:
                regime = "TREND_UP"
            elif close < sma20 < sma50:
                regime = "TREND_DOWN"

        regimes.append(regime)

    x["regime"] = regimes
    return x[["trade_date", "regime"]]


def load_data(db_path: Path = DB_PATH) -> tuple[pd.DataFrame, pd.DataFrame]:
    conn = sqlite3.connect(str(db_path))
    try:
        factor_cols = table_columns(conn, "factor_history")
        outcome_cols = table_columns(conn, "prediction_outcomes")
        index_cols = table_columns(conn, "indices_daily")

        missing = [f for f in FACTORS if f not in factor_cols]
        missing += [
            c for c in ("prediction_date", "index_name", "return_5d")
            if c not in outcome_cols
        ]
        if "trade_date" not in index_cols or "close" not in index_cols:
            missing += ["indices_daily.trade_date/close"]

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
        raise RuntimeError("No NIFTY50 index history available")

    df["prediction_date"] = pd.to_datetime(df["prediction_date"], errors="coerce")
    df["return_5d"] = pd.to_numeric(df["return_5d"], errors="coerce")
    for factor in FACTORS:
        df[factor] = pd.to_numeric(df[factor], errors="coerce")

    df = df.dropna(
        subset=["prediction_date", "index_name", "return_5d"]
    ).copy()

    regimes = build_regimes(nifty)
    df = df.merge(
        regimes,
        left_on="prediction_date",
        right_on="trade_date",
        how="left",
    ).drop(columns=["trade_date"])

    return df, regimes


def daily_ic(frame: pd.DataFrame, factor: str) -> pd.Series:
    values = []
    dates = []

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
            values.append(float(ic))

    return pd.Series(values, index=pd.DatetimeIndex(dates), dtype=float)


def fit_regime_weights(
    train: pd.DataFrame,
    regime: str,
    cfg: Config,
) -> tuple[dict[str, float], dict[str, dict]]:
    global_ic = {f: daily_ic(train, f) for f in FACTORS}
    regime_train = train[train["regime"] == regime].copy()
    regime_ic = {f: daily_ic(regime_train, f) for f in FACTORS}

    raw = {}
    meta = {}

    for factor in FACTORS:
        g = global_ic[factor]
        r = regime_ic[factor]

        g_mean = float(g.mean()) if len(g) >= cfg.min_global_ic_days else 0.0

        if len(r) >= cfg.min_regime_ic_days:
            r_mean = float(r.mean())
            n = len(r)
            source = "REGIME"
        else:
            r_mean = g_mean
            n = len(r)
            source = "GLOBAL_FALLBACK"

        alpha = n / (n + cfg.prior_strength_days) if n > 0 else 0.0
        shrunk_ic = alpha * r_mean + (1.0 - alpha) * g_mean

        std = float(r.std(ddof=1)) if len(r) > 1 else np.nan
        icir = (
            abs(float(r.mean()) / std * np.sqrt(len(r)))
            if pd.notna(std) and std > 0
            else 0.0
        )

        hit = float((r > 0).mean()) if len(r) else 0.5
        sample_quality = min(1.0, n / max(cfg.min_regime_ic_days, 1))
        stability = min(1.0, icir / 2.0)
        hit_quality = 0.5 + abs(hit - 0.5)

        reliability = float(
            np.clip(
                sample_quality * max(stability, 0.10) * hit_quality,
                0.0,
                1.0,
            )
        )

        raw_weight = abs(shrunk_ic) * reliability
        raw[factor] = raw_weight

        meta[factor] = {
            "global_ic": g_mean,
            "regime_ic": r_mean,
            "shrunk_ic": shrunk_ic,
            "regime_days": int(n),
            "icir": icir,
            "hit_rate": hit,
            "reliability": reliability,
            "direction": 1 if shrunk_ic >= 0 else -1,
            "source": source,
        }

    total = sum(raw.values())

    if total <= 0:
        weights = {f: 1.0 / len(FACTORS) for f in FACTORS}
    else:
        weights = {f: raw[f] / total for f in FACTORS}

    # Iteratively cap concentration and redistribute excess.
    for _ in range(20):
        excess = sum(
            max(0.0, weights[f] - cfg.max_factor_weight)
            for f in FACTORS
        )
        if excess <= 1e-12:
            break

        capped = {
            f: min(weights[f], cfg.max_factor_weight)
            for f in FACTORS
        }

        room = [
            f for f in FACTORS
            if capped[f] < cfg.max_factor_weight - 1e-12
        ]

        if not room:
            weights = capped
            break

        room_total = sum(capped[f] for f in room)

        for f in room:
            share = (
                capped[f] / room_total
                if room_total > 0
                else 1.0 / len(room)
            )
            capped[f] += excess * share

        weights = capped

    total = sum(weights.values())
    weights = {f: weights[f] / total for f in FACTORS}

    for f in FACTORS:
        meta[f]["weight"] = weights[f]

    return weights, meta


def score_day(
    day: pd.DataFrame,
    weights: dict[str, float],
    meta: dict[str, dict],
) -> pd.Series:
    score = pd.Series(0.0, index=day.index, dtype=float)

    for factor in FACTORS:
        x = pd.to_numeric(day[factor], errors="coerce")
        ranks = x.rank(method="average", pct=True)
        centered = ranks - 0.5

        score = score.add(
            centered
            * weights[factor]
            * meta[factor]["direction"],
            fill_value=0.0,
        )

    return score


def evaluate_test_day(
    day: pd.DataFrame,
    min_stocks: int,
) -> dict | None:
    work = day[["candidate_score", "return_5d"]].dropna().copy()

    if len(work) < min_stocks:
        return None

    ranked = work["candidate_score"].rank(method="first")
    q = pd.qcut(ranked, 5, labels=False)

    if q.nunique() < 5:
        return None

    top = float(work.loc[q == 4, "return_5d"].mean())
    bottom = float(work.loc[q == 0, "return_5d"].mean())

    return {
        "top_return": top,
        "bottom_return": bottom,
        "spread": top - bottom,
        "top_win_rate": float(
            (work.loc[q == 4, "return_5d"] > 0).mean() * 100
        ),
        "bottom_win_rate": float(
            (work.loc[q == 0, "return_5d"] > 0).mean() * 100
        ),
        "observations": int(len(work)),
    }


def run_walk_forward(
    df: pd.DataFrame,
    cfg: Config,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = sorted(df["prediction_date"].dropna().unique())

    results = []
    fit_rows = []

    # Only completed train/test blocks are evaluated.
    start = cfg.train_days
    window = 0

    while start + cfg.test_days <= len(dates):
        train_dates = dates[start - cfg.train_days:start]
        test_dates = dates[start:start + cfg.test_days]

        train = df[df["prediction_date"].isin(train_dates)].copy()
        test = df[df["prediction_date"].isin(test_dates)].copy()

        # Critical leakage rule:
        # weights are fit only once per regime using TRAIN data.
        regimes_in_test = [
            r for r in test["regime"].dropna().unique()
            if isinstance(r, str)
        ]

        if not regimes_in_test:
            start += cfg.test_days
            continue

        cache = {}

        for regime in regimes_in_test:
            cache[regime] = fit_regime_weights(train, regime, cfg)

        daily_results = []

        for date, day in test.groupby("prediction_date", sort=True):
            regime_values = day["regime"].dropna().unique()

            if len(regime_values) != 1:
                continue

            regime = str(regime_values[0])

            # The regime is determined from NIFTY history through `date`.
            # No future test-day regime is used to choose the model.
            weights, meta = cache[regime]

            day = day.copy()
            day["candidate_score"] = score_day(day, weights, meta)

            evaluated = evaluate_test_day(
                day,
                cfg.min_stocks_per_day,
            )

            if evaluated is None:
                continue

            evaluated.update(
                {
                    "prediction_date": date,
                    "regime": regime,
                }
            )
            daily_results.append(evaluated)

        if daily_results:
            daily_df = pd.DataFrame(daily_results)

            window += 1

            results.append(
                {
                    "window": window,
                    "train_start": train_dates[0],
                    "train_end": train_dates[-1],
                    "test_start": test_dates[0],
                    "test_end": test_dates[-1],
                    "valid_test_days": len(daily_df),
                    "top_return": float(daily_df["top_return"].mean()),
                    "bottom_return": float(daily_df["bottom_return"].mean()),
                    "spread": float(daily_df["spread"].mean()),
                    "top_win_rate": float(daily_df["top_win_rate"].mean()),
                    "bottom_win_rate": float(daily_df["bottom_win_rate"].mean()),
                }
            )

            for regime, (_, meta) in cache.items():
                for factor, values in meta.items():
                    row = dict(values)
                    row.update(
                        {
                            "window": window,
                            "test_regime": regime,
                            "factor": factor,
                        }
                    )
                    fit_rows.append(row)

        start += cfg.test_days

    return pd.DataFrame(results), pd.DataFrame(fit_rows)


def summarize(results: pd.DataFrame) -> dict:
    spreads = pd.to_numeric(
        results.get("spread", pd.Series(dtype=float)),
        errors="coerce",
    ).dropna()

    if spreads.empty:
        return {
            "windows": 0,
            "average_spread": None,
            "median_spread": None,
            "positive_window_pct": None,
            "worst_window": None,
            "best_window": None,
        }

    return {
        "windows": int(len(spreads)),
        "average_spread": float(spreads.mean()),
        "median_spread": float(spreads.median()),
        "positive_window_pct": float((spreads > 0).mean() * 100),
        "worst_window": float(spreads.min()),
        "best_window": float(spreads.max()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--train-days", type=int, default=120)
    parser.add_argument("--test-days", type=int, default=20)
    parser.add_argument(
        "--output",
        type=Path,
        default=BASE_DIR / "research" / "artifacts",
    )
    args = parser.parse_args()

    cfg = Config(
        train_days=args.train_days,
        test_days=args.test_days,
    )

    df, regimes = load_data(args.db)
    results, fits = run_walk_forward(df, cfg)
    summary = summarize(results)

    args.output.mkdir(parents=True, exist_ok=True)

    results.to_csv(
        args.output / "regime_aware_c21_walk_forward.csv",
        index=False,
    )
    fits.to_csv(
        args.output / "regime_aware_c21_factor_fits.csv",
        index=False,
    )

    (args.output / "regime_aware_c21_summary.json").write_text(
        json.dumps(
            {
                "config": asdict(cfg),
                "summary": summary,
                "regime_distribution": regimes["regime"].value_counts().to_dict(),
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 79)
    print("MARKETBOT TRACK C2.1 - LEAKAGE-SAFE REGIME WALK-FORWARD")
    print("=" * 79)
    print(f"Observations : {len(df):,}")
    print(f"Windows      : {summary['windows']}")
    print(f"Average spread : {summary['average_spread']}")
    print(f"Median spread  : {summary['median_spread']}")
    print(f"Positive %     : {summary['positive_window_pct']}")
    print(f"Worst window   : {summary['worst_window']}")
    print("\nResearch-only. Production scoring has NOT been changed.")


if __name__ == "__main__":
    main()
