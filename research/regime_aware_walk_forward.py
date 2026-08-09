from __future__ import annotations

"""MarketBot Track C2.2
Leakage-safe, regime-specific walk-forward research.

This module is deliberately research-only.
It does not import or modify production scoring.

Important corrections:
1. Regime is determined independently for each test date from NIFTY history
   available through that date.
2. Each regime gets its own training weights.
3. Sparse regime IC estimates are shrunk toward the global training IC.
4. Weight concentration is capped correctly at MAX_FACTOR_WEIGHT.
5. No future test-window regime aggregation is used.
"""

import argparse
import json
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

MAX_FACTOR_WEIGHT = 0.45
MIN_GLOBAL_IC_DAYS = 30
MIN_REGIME_IC_DAYS = 20
PRIOR_DAYS = 40.0


def build_regimes(index_df: pd.DataFrame) -> pd.DataFrame:
    x = index_df.copy()
    x["trade_date"] = pd.to_datetime(x["trade_date"], errors="coerce")
    x["close"] = pd.to_numeric(x["close"], errors="coerce")
    x = (
        x.dropna(subset=["trade_date", "close"])
        .drop_duplicates("trade_date")
        .sort_values("trade_date")
        .reset_index(drop=True)
    )

    x["ret_1d"] = x["close"].pct_change()
    x["vol20"] = x["ret_1d"].rolling(20, min_periods=20).std()
    x["sma20"] = x["close"].rolling(20, min_periods=20).mean()
    x["sma50"] = x["close"].rolling(50, min_periods=50).mean()

    # Expanding thresholds use only information available up to each date.
    x["vol_q25"] = x["vol20"].expanding(min_periods=60).quantile(0.25)
    x["vol_q75"] = x["vol20"].expanding(min_periods=60).quantile(0.75)

    regime = []
    for _, r in x.iterrows():
        close = r["close"]
        sma20 = r["sma20"]
        sma50 = r["sma50"]
        vol = r["vol20"]
        q25 = r["vol_q25"]
        q75 = r["vol_q75"]

        value = "SIDEWAYS"

        if pd.notna(vol) and pd.notna(q75) and vol >= q75:
            if pd.notna(sma20) and pd.notna(sma50):
                value = "HIGH_VOL_UP" if sma20 >= sma50 else "HIGH_VOL_DOWN"
            else:
                value = "HIGH_VOL"
        elif pd.notna(vol) and pd.notna(q25) and vol <= q25:
            value = "LOW_VOL"
        elif pd.notna(sma20) and pd.notna(sma50):
            if close > sma20 > sma50:
                value = "TREND_UP"
            elif close < sma20 < sma50:
                value = "TREND_DOWN"

        regime.append(value)

    x["regime"] = regime
    return x[["trade_date", "regime"]]


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def load_data(db_path: Path = DEFAULT_DB) -> tuple[pd.DataFrame, pd.DataFrame]:
    conn = sqlite3.connect(str(db_path))
    try:
        factor_cols = _columns(conn, "factor_history")
        outcome_cols = _columns(conn, "prediction_outcomes")
        index_cols = _columns(conn, "indices_daily")

        required_factors = set(FACTORS)
        missing = sorted(required_factors - factor_cols)

        for col in ("prediction_date", "index_name", "return_5d"):
            if col not in outcome_cols:
                missing.append(f"prediction_outcomes.{col}")

        if "trade_date" not in index_cols or "close" not in index_cols:
            missing.append("indices_daily.trade_date/close")

        if missing:
            raise RuntimeError(
                "Missing required database columns: " + ", ".join(missing)
            )

        # The factor-history date is joined to prediction date.  Index name is
        # also included when available in both tables to avoid accidental
        # cross-index matching.
        factor_index = "AND p.index_name = f.index_name" if "index_name" in factor_cols else ""

        sql = f"""
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
              {factor_index}
            WHERE p.return_5d IS NOT NULL
            ORDER BY p.prediction_date, p.index_name
        """

        df = pd.read_sql_query(sql, conn)

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
        raise RuntimeError("No factor/outcome observations found.")
    if nifty.empty:
        raise RuntimeError("No NIFTY50 history found.")

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

    return pd.Series(
        values,
        index=pd.DatetimeIndex(dates),
        dtype=float,
    )


def _cap_weights(raw: dict[str, float]) -> dict[str, float]:
    """Normalize positive raw weights while enforcing a hard max per factor."""
    clean = {
        f: max(0.0, float(raw.get(f, 0.0)))
        for f in FACTORS
    }

    if sum(clean.values()) <= 0:
        return {f: 1.0 / len(FACTORS) for f in FACTORS}

    # Water-filling under an upper bound.
    remaining = set(FACTORS)
    final = {f: 0.0 for f in FACTORS}
    mass = 1.0

    while remaining:
        total_raw = sum(clean[f] for f in remaining)

        if total_raw <= 0:
            equal = mass / len(remaining)
            for f in remaining:
                final[f] = equal
            break

        proposed = {
            f: mass * clean[f] / total_raw
            for f in remaining
        }

        capped = [f for f in remaining if proposed[f] > MAX_FACTOR_WEIGHT]

        if not capped:
            for f in remaining:
                final[f] = proposed[f]
            break

        for f in capped:
            final[f] = MAX_FACTOR_WEIGHT
            mass -= MAX_FACTOR_WEIGHT
            remaining.remove(f)

        if mass <= 1e-12:
            break

    total = sum(final.values())

    # Numerical normalization only; never let it violate the cap.
    if total <= 0:
        return {f: 1.0 / len(FACTORS) for f in FACTORS}

    final = {f: final[f] / total for f in FACTORS}

    # Safety assertion catches future implementation mistakes.
    if max(final.values()) > MAX_FACTOR_WEIGHT + 1e-9:
        raise AssertionError(
            f"Weight cap violated: {max(final.values()):.6f}"
        )

    return final


def fit_weights(
    train: pd.DataFrame,
    target_regime: str,
) -> tuple[dict[str, float], dict[str, dict]]:
    global_ic = {f: daily_ic(train, f) for f in FACTORS}
    regime_train = train[train["regime"] == target_regime].copy()
    regime_ic = {f: daily_ic(regime_train, f) for f in FACTORS}

    raw = {}
    meta = {}

    for factor in FACTORS:
        g = global_ic[factor]
        r = regime_ic[factor]

        g_mean = float(g.mean()) if len(g) >= MIN_GLOBAL_IC_DAYS else 0.0

        if len(r) >= MIN_REGIME_IC_DAYS:
            r_mean = float(r.mean())
            source = "REGIME"
        else:
            r_mean = g_mean
            source = "GLOBAL_FALLBACK"

        n = len(r)
        alpha = n / (n + PRIOR_DAYS) if n else 0.0
        shrunk = alpha * r_mean + (1.0 - alpha) * g_mean

        std = float(r.std(ddof=1)) if len(r) > 1 else np.nan
        icir = (
            abs(float(r.mean()) / std * np.sqrt(len(r)))
            if pd.notna(std) and std > 0
            else 0.0
        )

        reliability = min(1.0, n / MIN_REGIME_IC_DAYS)
        reliability *= min(1.0, max(icir, 0.10) / 2.0)

        raw[factor] = abs(shrunk) * reliability

        meta[factor] = {
            "global_ic": g_mean,
            "regime_ic": r_mean,
            "shrunk_ic": shrunk,
            "regime_days": int(n),
            "icir": icir,
            "direction": 1 if shrunk >= 0 else -1,
            "source": source,
        }

    weights = _cap_weights(raw)

    for factor in FACTORS:
        meta[factor]["weight"] = weights[factor]

    return weights, meta


def score_day(
    day: pd.DataFrame,
    weights: dict[str, float],
    meta: dict[str, dict],
) -> pd.Series:
    score = pd.Series(0.0, index=day.index, dtype=float)

    for factor in FACTORS:
        x = pd.to_numeric(day[factor], errors="coerce")
        rank = x.rank(method="average", pct=True)
        centered = rank - 0.5

        score = score.add(
            centered
            * weights[factor]
            * meta[factor]["direction"],
            fill_value=0.0,
        )

    return score


def evaluate_day(
    day: pd.DataFrame,
    min_stocks: int = 10,
) -> dict | None:
    work = day[["candidate_score", "return_5d"]].dropna().copy()

    if len(work) < min_stocks:
        return None

    # Rank first prevents qcut problems from duplicated scores.
    rank = work["candidate_score"].rank(method="first")
    zone = pd.qcut(rank, 5, labels=False)

    if zone.nunique() != 5:
        return None

    top = work.loc[zone == 4, "return_5d"]
    bottom = work.loc[zone == 0, "return_5d"]

    return {
        "top_return": float(top.mean()),
        "bottom_return": float(bottom.mean()),
        "spread": float(top.mean() - bottom.mean()),
        "top_win_rate": float((top > 0).mean() * 100),
        "bottom_win_rate": float((bottom > 0).mean() * 100),
        "observations": int(len(work)),
    }


def run(
    df: pd.DataFrame,
    train_days: int = 120,
    test_days: int = 20,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = sorted(df["prediction_date"].dropna().unique())

    results = []
    fit_records = []
    window = 0

    for start in range(train_days, len(dates), test_days):
        train_dates = dates[start - train_days:start]
        test_dates = dates[start:start + test_days]

        if len(test_dates) < test_days:
            break

        train = df[df["prediction_date"].isin(train_dates)].copy()
        test = df[df["prediction_date"].isin(test_dates)].copy()

        # IMPORTANT:
        # We fit one model per regime using TRAIN ONLY.
        regimes = [
            str(x)
            for x in train["regime"].dropna().unique()
            if str(x)
        ]

        models = {}

        for regime in regimes:
            weights, meta = fit_weights(train, regime)
            models[regime] = (weights, meta)

            for factor in FACTORS:
                row = dict(meta[factor])
                row.update(
                    {
                        "window": window + 1,
                        "regime": regime,
                        "factor": factor,
                    }
                )
                fit_records.append(row)

        day_results = []

        for date, day in test.groupby("prediction_date", sort=True):
            regime_values = day["regime"].dropna().unique()

            if len(regime_values) != 1:
                continue

            regime = str(regime_values[0])

            # Regime for this date is produced from NIFTY data through this
            # date. The model itself was fitted only on TRAIN observations.
            if regime not in models:
                # Unseen regime: use the global model, which is still TRAIN-only.
                weights, meta = fit_weights(train, "___UNSEEN___")
            else:
                weights, meta = models[regime]

            scored = day.copy()
            scored["candidate_score"] = score_day(
                scored,
                weights,
                meta,
            )

            evaluated = evaluate_day(scored)

            if evaluated is None:
                continue

            evaluated.update(
                {
                    "prediction_date": date,
                    "regime": regime,
                }
            )
            day_results.append(evaluated)

        if day_results:
            window += 1
            daily = pd.DataFrame(day_results)

            results.append(
                {
                    "window": window,
                    "train_start": str(train_dates[0]),
                    "train_end": str(train_dates[-1]),
                    "test_start": str(test_dates[0]),
                    "test_end": str(test_dates[-1]),
                    "valid_test_days": int(len(daily)),
                    "top_return": float(daily["top_return"].mean()),
                    "bottom_return": float(daily["bottom_return"].mean()),
                    "spread": float(daily["spread"].mean()),
                    "top_win_rate": float(daily["top_win_rate"].mean()),
                    "bottom_win_rate": float(daily["bottom_win_rate"].mean()),
                }
            )

    return pd.DataFrame(results), pd.DataFrame(fit_records)


def summarize(results: pd.DataFrame) -> dict:
    if results.empty:
        return {
            "windows": 0,
            "average_spread": None,
            "median_spread": None,
            "positive_window_pct": None,
            "worst_window": None,
            "best_window": None,
        }

    s = pd.to_numeric(results["spread"], errors="coerce").dropna()

    return {
        "windows": int(len(s)),
        "average_spread": float(s.mean()),
        "median_spread": float(s.median()),
        "positive_window_pct": float((s > 0).mean() * 100),
        "worst_window": float(s.min()),
        "best_window": float(s.max()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--train-days", type=int, default=120)
    parser.add_argument("--test-days", type=int, default=20)
    args = parser.parse_args()

    df, regimes = load_data(args.db)

    results, fits = run(
        df,
        train_days=args.train_days,
        test_days=args.test_days,
    )

    summary = summarize(results)

    output = BASE_DIR / "research" / "artifacts"
    output.mkdir(parents=True, exist_ok=True)

    results.to_csv(
        output / "c22_regime_specific_walk_forward.csv",
        index=False,
    )
    fits.to_csv(
        output / "c22_regime_specific_factor_fits.csv",
        index=False,
    )

    (output / "c22_summary.json").write_text(
        json.dumps(
            {
                "summary": summary,
                "regime_counts": regimes["regime"].value_counts().to_dict(),
                "production_changed": False,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 79)
    print("MARKETBOT C2.2 - REGIME-SPECIFIC LEAKAGE-SAFE WALK-FORWARD")
    print("=" * 79)
    print(f"Observations : {len(df):,}")
    print(f"Trading dates: {df['prediction_date'].nunique()}")
    print(f"Train days   : {args.train_days}")
    print(f"Test days    : {args.test_days}")

    for _, row in results.iterrows():
        print(f"\nWINDOW {int(row['window'])}")
        print(
            f"Train : {row['train_start']} -> {row['train_end']}\n"
            f"Test  : {row['test_start']} -> {row['test_end']}"
        )
        print(f"Top return    : {row['top_return']:+.4f}%")
        print(f"Bottom return : {row['bottom_return']:+.4f}%")
        print(f"Spread        : {row['spread']:+.4f}%")

    print("\n" + "=" * 79)
    print("C2.2 SUMMARY")
    print("=" * 79)
    print(f"Windows             : {summary['windows']}")
    print(f"Average spread      : {summary['average_spread']}")
    print(f"Median spread       : {summary['median_spread']}")
    print(f"Positive windows    : {summary['positive_window_pct']}%")
    print(f"Worst window        : {summary['worst_window']}")
    print(f"Best window         : {summary['best_window']}")
    print("\nProduction scoring has NOT been changed.")


if __name__ == "__main__":
    main()
