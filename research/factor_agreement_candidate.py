from __future__ import annotations

"""MarketBot Track B - Factor Agreement Candidate

Research-only, leakage-safe test of the hypothesis that baseline ranking
performance differs materially by factor-agreement state.

The module does not write to the MarketBot database and does not modify
production scoring, weights, challenger logic, or live trading.
"""

import sqlite3
from pathlib import Path
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = BASE_DIR / "market_intelligence.db"

FACTORS = [
    "relative_strength",
    "trend_score",
    "momentum_score",
    "volatility_score",
    "liquidity_score",
]

MIN_STOCKS = 10
WINDOW_TRAIN_DAYS = 120
WINDOW_TEST_DAYS = 20
AGREEMENT_Q = 0.75


def load_data(db_path=DEFAULT_DB):
    conn = sqlite3.connect(str(db_path))
    try:
        q = """
        SELECT
            DATE(f.trade_date) AS trade_date,
            f.index_name AS entity,
            f.relative_strength,
            f.trend_score,
            f.momentum_score,
            f.volatility_score,
            f.liquidity_score,
            o.return_5d
        FROM factor_history f
        JOIN prediction_outcomes o
          ON DATE(f.trade_date)=DATE(o.prediction_date)
         AND f.index_name=o.index_name
        WHERE o.return_5d IS NOT NULL
        ORDER BY DATE(f.trade_date), f.index_name
        """
        df = pd.read_sql_query(q, conn)
    finally:
        conn.close()

    for c in FACTORS + ["return_5d"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")

    return df.dropna(
        subset=["trade_date", "return_5d"] + FACTORS
    ).reset_index(drop=True)


def add_agreement(df):
    out = df.copy()

    # Cross-sectional percentile ranks; no future information is used.
    for factor in FACTORS:
        out[f"{factor}_rank"] = (
            out.groupby("trade_date", sort=False)[factor]
            .rank(method="average", pct=True)
        )

    ranks = out[[f"{f}_rank" for f in FACTORS]]
    # Agreement = average pairwise directional agreement.
    # Same-side factor ranks (>0.5 or <0.5) increase agreement.
    signs = np.sign(ranks - 0.5)
    pairs = []
    for i in range(len(FACTORS)):
        for j in range(i + 1, len(FACTORS)):
            pairs.append((signs.iloc[:, i] == signs.iloc[:, j]).astype(float))
    out["agreement_score"] = pd.concat(pairs, axis=1).mean(axis=1)

    # Daily aggregate agreement used as the conditioning variable.
    daily = (
        out.groupby("trade_date", as_index=False)["agreement_score"]
        .mean()
        .rename(columns={"agreement_score": "daily_agreement"})
    )
    out = out.merge(daily, on="trade_date", how="left")
    return out


def add_baseline_score(df, weights=None):
    out = df.copy()
    if weights is None:
        weights = {f: 1.0 / len(FACTORS) for f in FACTORS}
    out["baseline_score"] = sum(
        out[f] * float(weights[f]) for f in FACTORS
    )
    return out


def evaluate_day(day_df, min_stocks=MIN_STOCKS):
    work = day_df.dropna(subset=["baseline_score", "return_5d"]).copy()
    if len(work) < min_stocks:
        return None

    ranked = work.sort_values("baseline_score", ascending=False)
    n = max(1, len(ranked) // 5)
    top = ranked.head(n)["return_5d"].mean()
    bottom = ranked.tail(n)["return_5d"].mean()

    return {
        "date": work["trade_date"].iloc[0],
        "spread": float(top - bottom),
        "top_return": float(top),
        "bottom_return": float(bottom),
        "agreement": float(work["daily_agreement"].iloc[0]),
        "n": int(len(work)),
    }


def classify_threshold(train_daily):
    """Determine threshold using training data only."""
    if train_daily.empty:
        return None
    return float(train_daily["agreement"].quantile(AGREEMENT_Q))


def run_walk_forward(df):
    df = add_agreement(df)
    df = add_baseline_score(df)

    dates = sorted(df["trade_date"].dropna().unique())
    rows = []

    for start in range(0, len(dates) - WINDOW_TRAIN_DAYS - WINDOW_TEST_DAYS + 1,
                       WINDOW_TEST_DAYS):
        train_dates = dates[start:start + WINDOW_TRAIN_DAYS]
        test_dates = dates[
            start + WINDOW_TRAIN_DAYS:
            start + WINDOW_TRAIN_DAYS + WINDOW_TEST_DAYS
        ]

        train = df[df["trade_date"].isin(train_dates)]
        test = df[df["trade_date"].isin(test_dates)]

        train_daily = (
            train.groupby("trade_date")["daily_agreement"]
            .first()
            .reset_index(name="agreement")
        )
        threshold = classify_threshold(train_daily)

        for date, day in test.groupby("trade_date", sort=True):
            result = evaluate_day(day)
            if result is None:
                continue

            result["window"] = len(set(r["window"] for r in rows)) + 1 if rows else 1
            result["train_start"] = pd.Timestamp(train_dates[0])
            result["train_end"] = pd.Timestamp(train_dates[-1])
            result["test_date"] = pd.Timestamp(date)
            result["threshold"] = threshold
            result["high_agreement"] = (
                bool(result["agreement"] >= threshold)
                if threshold is not None else False
            )
            rows.append(result)

    return pd.DataFrame(rows)


def summarize(results):
    if results.empty:
        return pd.DataFrame()

    rows = []
    for label, mask in {
        "ALL_DAYS": np.ones(len(results), dtype=bool),
        "LOW_AGREEMENT": ~results["high_agreement"],
        "HIGH_AGREEMENT": results["high_agreement"],
    }.items():
        work = results.loc[mask]
        if work.empty:
            continue
        rows.append({
            "condition": label,
            "days": len(work),
            "mean_spread": work["spread"].mean(),
            "median_spread": work["spread"].median(),
            "positive_day_pct": (work["spread"] > 0).mean() * 100,
            "worst_day": work["spread"].min(),
            "best_day": work["spread"].max(),
        })
    return pd.DataFrame(rows)


def main(db_path=DEFAULT_DB):
    df = load_data(db_path)
    if df.empty:
        print("No matched factor/outcome observations.")
        return

    results = run_walk_forward(df)
    summary = summarize(results)

    print("\n" + "=" * 78)
    print("MARKETBOT TRACK B - FACTOR AGREEMENT CANDIDATE")
    print("=" * 78)
    print(f"\nMatched observations : {len(df):,}")
    print(f"Trading dates        : {df['trade_date'].nunique():,}")
    print(f"OOS evaluated days   : {len(results):,}")

    print("\nAGREEMENT-CONDITIONED OOS")
    print(summary.round(4).to_string(index=False))

    print("\nResearch only: production scoring, weights, challenger logic, and live trading were NOT changed.")


if __name__ == "__main__":
    main()
