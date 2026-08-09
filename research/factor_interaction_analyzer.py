from __future__ import annotations

import itertools
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


def _resolve_entity_column(conn, table: str) -> str:
    columns = {
        row[1]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if "index_name" in columns:
        return "index_name"
    if "symbol" in columns:
        return "symbol"
    raise RuntimeError(f"{table} has neither index_name nor symbol.")


def load_data(db_path=DB_PATH) -> pd.DataFrame:
    """Load factor/outcome observations without assuming a legacy schema."""
    conn = sqlite3.connect(str(db_path))
    try:
        factor_cols = {row[1] for row in conn.execute("PRAGMA table_info(factor_history)")}
        outcome_cols = {row[1] for row in conn.execute("PRAGMA table_info(prediction_outcomes)")}

        missing = [f for f in FACTORS if f not in factor_cols]
        if missing:
            raise RuntimeError(f"factor_history missing factors: {missing}")
        if "return_5d" not in outcome_cols:
            raise RuntimeError("prediction_outcomes missing return_5d.")

        f_entity = _resolve_entity_column(conn, "factor_history")
        o_entity = _resolve_entity_column(conn, "prediction_outcomes")

        query = f"""
            SELECT
                DATE(f.trade_date) AS trade_date,
                f.{f_entity} AS entity,
                {", ".join(f"f.{f}" for f in FACTORS)},
                o.return_5d
            FROM factor_history AS f
            INNER JOIN prediction_outcomes AS o
                ON DATE(f.trade_date) = DATE(o.prediction_date)
               AND f.{f_entity} = o.{o_entity}
            WHERE o.return_5d IS NOT NULL
            ORDER BY DATE(f.trade_date), f.{f_entity}
        """
        df = pd.read_sql(query, conn)
    finally:
        conn.close()

    for col in FACTORS + ["return_5d"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.dropna(subset=FACTORS + ["return_5d"]).reset_index(drop=True)


def cross_sectional_rank(df: pd.DataFrame, columns=FACTORS) -> pd.DataFrame:
    out = df.copy()
    for factor in columns:
        out[f"{factor}__rank"] = (
            out.groupby("trade_date", sort=False)[factor]
            .rank(method="average", pct=True)
        )
    return out


def build_interactions(df: pd.DataFrame):
    ranked = cross_sectional_rank(df)
    names = []

    for left, right in itertools.combinations(FACTORS, 2):
        name = f"{left}__x__{right}"
        ranked[name] = (
            (ranked[f"{left}__rank"] - 0.5)
            * (ranked[f"{right}__rank"] - 0.5)
        )
        names.append(name)

    return ranked, names


def _daily_ic(group: pd.DataFrame, column: str) -> float:
    x = pd.to_numeric(group[column], errors="coerce")
    y = pd.to_numeric(group["return_5d"], errors="coerce")
    valid = x.notna() & y.notna()

    if valid.sum() < 5 or x[valid].nunique() < 2 or y[valid].nunique() < 2:
        return np.nan

    return float(x[valid].corr(y[valid], method="spearman"))


def interaction_diagnostics(df: pd.DataFrame, interactions) -> pd.DataFrame:
    rows = []

    for column in interactions:
        daily = (
            df.groupby("trade_date", sort=True)
            .apply(lambda g: _daily_ic(g, column), include_groups=False)
            .dropna()
        )

        if daily.empty:
            continue

        std = float(daily.std(ddof=1)) if len(daily) > 1 else 0.0
        mean = float(daily.mean())

        rows.append({
            "interaction": column.replace("__x__", " × "),
            "days": int(len(daily)),
            "mean_ic": mean,
            "median_ic": float(daily.median()),
            "std_ic": std,
            "positive_days": int((daily > 0).sum()),
            "negative_days": int((daily < 0).sum()),
            "positive_pct": float((daily > 0).mean() * 100),
            "icir": float(mean / std) if std > 0 else 0.0,
            "min_ic": float(daily.min()),
            "max_ic": float(daily.max()),
        })

    return pd.DataFrame(rows).sort_values(
        ["mean_ic", "icir"], ascending=False
    ).reset_index(drop=True) if rows else pd.DataFrame()


def quintile_spreads(df: pd.DataFrame, interactions) -> pd.DataFrame:
    rows = []

    for column in interactions:
        work = df[["trade_date", column, "return_5d"]].dropna().copy()

        def assign(group):
            # Ranking first guarantees unique bin edges even with tied interaction values.
            ranks = group[column].rank(method="first")
            return pd.qcut(ranks, 5, labels=False)

        work["quintile"] = work.groupby("trade_date", sort=False).transform(
            lambda g: g
        )[column]  # placeholder overwritten below

        work["quintile"] = (
            work.groupby("trade_date", sort=False, group_keys=False)
            .apply(lambda g: assign(g), include_groups=False)
            .reset_index(level=0, drop=True)
        )

        q1 = work.loc[work["quintile"] == 0, "return_5d"]
        q5 = work.loc[work["quintile"] == 4, "return_5d"]

        if q1.empty or q5.empty:
            continue

        rows.append({
            "interaction": column.replace("__x__", " × "),
            "q1_return": float(q1.mean()),
            "q5_return": float(q5.mean()),
            "q5_minus_q1": float(q5.mean() - q1.mean()),
            "q1_win_rate": float((q1 > 0).mean() * 100),
            "q5_win_rate": float((q5 > 0).mean() * 100),
        })

    return pd.DataFrame(rows)


def analyze(db_path=DB_PATH):
    print("\n" + "=" * 78)
    print("MARKETBOT C3.1 - FACTOR INTERACTION ANALYZER")
    print("=" * 78)

    df = load_data(db_path)

    if df.empty:
        print("\nNo matched factor/outcome observations.")
        return {"observations": 0}

    ranked, interactions = build_interactions(df)
    diagnostics = interaction_diagnostics(ranked, interactions)
    spreads = quintile_spreads(ranked, interactions)

    print(f"\nObservations : {len(df):,}")
    print(f"Trading dates: {df['trade_date'].nunique():,}")
    print(f"Entities     : {df['entity'].nunique():,}")
    print(f"Interactions : {len(interactions)}")

    print("\n" + "=" * 78)
    print("INTERACTION IC DIAGNOSTICS")
    print("=" * 78)
    print(diagnostics.round(4).to_string(index=False) if not diagnostics.empty else "No diagnostics.")

    print("\n" + "=" * 78)
    print("INTERACTION QUINTILE SPREADS")
    print("=" * 78)
    print(spreads.round(4).to_string(index=False) if not spreads.empty else "No spreads.")

    print("\nResearch only: production scoring and weights were NOT changed.")

    return {
        "observations": len(df),
        "trading_dates": int(df["trade_date"].nunique()),
        "diagnostics": diagnostics,
        "spreads": spreads,
    }


if __name__ == "__main__":
    analyze()
