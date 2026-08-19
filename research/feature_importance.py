"""Deterministic, non-ML feature importance research helper."""
import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "market_intelligence.db"

FEATURES = [
    "sector_strength", "position_pct", "total_score",
    "intelligence_score", "change_pct"
]

def _compute():
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(factor_history)")}
        wanted = [c for c in FEATURES if c in cols]
        if "return_5d" not in cols or not wanted:
            return pd.DataFrame(columns=["feature", "importance_score"])
        q = "SELECT " + ", ".join(wanted + ["return_5d"]) + " FROM factor_history"
        df = pd.read_sql(q, conn)
    finally:
        conn.close()

    rows = []
    for f in wanted:
        x = pd.to_numeric(df[f], errors="coerce")
        y = pd.to_numeric(df["return_5d"], errors="coerce")
        mask = x.notna() & y.notna()
        corr = x[mask].corr(y[mask]) if mask.sum() >= 3 else 0.0
        rows.append((f, float(abs(corr) if pd.notna(corr) else 0.0)))

    return pd.DataFrame(rows, columns=["feature", "importance_score"]).sort_values(
        "importance_score", ascending=False
    ).reset_index(drop=True)

def feature_importance(verbose=True):
    result = {"importance": _compute()}
    if verbose:
        print(result["importance"].to_string(index=False))
    return result

class FeatureImportance:
    def run(self, verbose=True):
        return feature_importance(verbose=verbose)

if __name__ == "__main__":
    feature_importance()
