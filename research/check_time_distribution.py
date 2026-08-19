"""MarketBot option-chain time distribution diagnostic (read-only)."""
from __future__ import annotations
import argparse
import sqlite3
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = BASE_DIR / "market_intelligence.db"

def analyze(db_path: Path = DEFAULT_DB) -> pd.DataFrame:
    conn = sqlite3.connect(str(db_path))
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(option_chain_history)")}
        if "trade_time" not in cols:
            raise RuntimeError("option_chain_history.trade_time is missing")
        df = pd.read_sql_query(
            "SELECT trade_time FROM option_chain_history WHERE trade_time IS NOT NULL ORDER BY trade_time",
            conn,
        )
    finally:
        conn.close()
    if df.empty:
        print("No option-chain trade_time observations found.")
        return pd.DataFrame(columns=["hour", "observations", "pct"])
    df["trade_time"] = pd.to_datetime(df["trade_time"], format="mixed", errors="coerce")
    df = df.dropna(subset=["trade_time"])
    if df.empty:
        print("No parseable trade_time observations found.")
        return pd.DataFrame(columns=["hour", "observations", "pct"])
    result = df.assign(hour=df["trade_time"].dt.hour).groupby("hour").size().rename("observations").reset_index()
    result["pct"] = result["observations"] / result["observations"].sum() * 100
    print("=" * 70)
    print("MARKETBOT - OPTION CHAIN TIME DISTRIBUTION")
    print("=" * 70)
    print(f"Database     : {db_path}")
    print(f"Observations : {len(df):,}")
    print(result.round(2).to_string(index=False))
    print("\nDiagnostic only: database was not modified.")
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    analyze(p.parse_args().db)

if __name__ == "__main__":
    main()
