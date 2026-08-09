from __future__ import annotations

import sqlite3
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


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def load_research_data() -> pd.DataFrame:
    """Return one canonical research frame with factor values + forward outcomes.

    prediction_outcomes intentionally does not contain factor columns in the
    current schema, so all factor research must join it to factor_history.
    """
    conn = sqlite3.connect(str(DB_PATH))
    try:
        factor_cols = _table_columns(conn, "factor_history")
        outcome_cols = _table_columns(conn, "prediction_outcomes")

        missing = [c for c in FACTORS if c not in factor_cols]
        if missing:
            raise RuntimeError(
                "factor_history is missing factor columns: "
                + ", ".join(missing)
            )

        required_outcomes = {"prediction_date", "index_name", "return_5d"}
        missing_outcomes = sorted(required_outcomes - outcome_cols)
        if missing_outcomes:
            raise RuntimeError(
                "prediction_outcomes is missing columns: "
                + ", ".join(missing_outcomes)
            )

        query = """
            SELECT
                p.prediction_date,
                p.index_name,
                p.rank,
                p.intelligence_score,
                p.return_5d,
                f.relative_strength,
                f.trend_score,
                f.momentum_score,
                f.volatility_score,
                f.liquidity_score,
                f.change_pct,
                f.sector_strength,
                f.position_pct
            FROM prediction_outcomes p
            INNER JOIN factor_history f
                ON p.prediction_date = f.trade_date
               AND p.index_name = f.index_name
            WHERE p.return_5d IS NOT NULL
            ORDER BY p.prediction_date, p.index_name
        """

        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    df["prediction_date"] = pd.to_datetime(
        df["prediction_date"], errors="coerce"
    )
    for col in FACTORS + [
        "intelligence_score",
        "return_5d",
        "change_pct",
        "sector_strength",
        "position_pct",
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(
        subset=["prediction_date", "index_name", "return_5d"]
    ).copy()

    return df


def load_nifty_regime_data() -> pd.DataFrame:
    """Build a causal daily NIFTY regime label using information available on date t."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cols = _table_columns(conn, "indices_daily")
        if "index_name" not in cols:
            raise RuntimeError("indices_daily has no index_name column")

        df = pd.read_sql_query(
            """
            SELECT trade_date, index_name, close
            FROM indices_daily
            WHERE index_name = 'NIFTY50'
            ORDER BY trade_date
            """,
            conn,
        )
    finally:
        conn.close()

    if df.empty:
        raise RuntimeError("No NIFTY50 rows found in indices_daily")

    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["trade_date", "close"]).copy()
    df = df.drop_duplicates("trade_date").sort_values("trade_date")

    df["ret_1d"] = df["close"].pct_change()
    df["vol_20"] = df["ret_1d"].rolling(20, min_periods=20).std() * np.sqrt(252)
    df["sma20"] = df["close"].rolling(20, min_periods=20).mean()
    df["sma50"] = df["close"].rolling(50, min_periods=50).mean()

    # Causal volatility percentiles: only observations available up to date t.
    expanding = df["vol_20"].expanding(min_periods=60)
    df["vol_q25"] = expanding.quantile(0.25)
    df["vol_q75"] = expanding.quantile(0.75)

    def classify(row) -> str:
        vol = row["vol_20"]
        if pd.notna(vol) and pd.notna(row["vol_q75"]) and vol >= row["vol_q75"]:
            if pd.notna(row["sma20"]) and pd.notna(row["sma50"]):
                return "HIGH_VOL_UP" if row["sma20"] >= row["sma50"] else "HIGH_VOL_DOWN"

        if pd.notna(vol) and pd.notna(row["vol_q25"]) and vol <= row["vol_q25"]:
            return "LOW_VOL"

        if pd.notna(row["sma20"]) and pd.notna(row["sma50"]):
            if row["close"] > row["sma20"] > row["sma50"]:
                return "TREND_UP"
            if row["close"] < row["sma20"] < row["sma50"]:
                return "TREND_DOWN"

        return "SIDEWAYS"

    df["regime"] = df.apply(classify, axis=1)

    return df[
        [
            "trade_date",
            "close",
            "ret_1d",
            "vol_20",
            "regime",
        ]
    ].copy()


def merge_regime(df: pd.DataFrame) -> pd.DataFrame:
    regime = load_nifty_regime_data()
    out = df.merge(
        regime,
        left_on="prediction_date",
        right_on="trade_date",
        how="left",
    )
    return out.drop(columns=["trade_date"])


def daily_ic(frame: pd.DataFrame, factor: str) -> pd.Series:
    """Cross-sectional Spearman IC by prediction date."""
    values = []
    dates = []

    for date, group in frame.groupby("prediction_date", sort=True):
        x = pd.to_numeric(group[factor], errors="coerce")
        y = pd.to_numeric(group["return_5d"], errors="coerce")
        valid = x.notna() & y.notna()

        if valid.sum() < 5:
            continue

        x = x[valid]
        y = y[valid]

        if x.nunique() < 2 or y.nunique() < 2:
            continue

        ic = x.rank(method="average").corr(
            y.rank(method="average")
        )

        if pd.notna(ic):
            dates.append(date)
            values.append(float(ic))

    if not values:
        return pd.Series(dtype=float, name=factor)

    return pd.Series(values, index=pd.DatetimeIndex(dates), name=factor)


def quintile_spread(frame: pd.DataFrame, factor: str) -> float | None:
    pieces = []

    for _, group in frame.groupby("prediction_date", sort=False):
        x = pd.to_numeric(group[factor], errors="coerce")
        y = pd.to_numeric(group["return_5d"], errors="coerce")
        valid = x.notna() & y.notna()

        if valid.sum() < 10:
            continue

        work = pd.DataFrame({"x": x[valid], "y": y[valid]})
        work["q"] = pd.qcut(
            work["x"].rank(method="first"),
            5,
            labels=False,
        )

        if work["q"].nunique() < 5:
            continue

        pieces.append(
            float(
                work.loc[work["q"] == 4, "y"].mean()
                - work.loc[work["q"] == 0, "y"].mean()
            )
        )

    if not pieces:
        return None

    return float(np.mean(pieces))
