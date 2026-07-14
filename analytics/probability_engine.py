import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def get_signal_probability():

    conn = sqlite3.connect(str(DB_PATH))

    query = """
    SELECT

        f.position_52w,
        f.volume_expansion,

        h.sector_strength,

        r.return_20d

    FROM factor_library f

    Join factor_history h
    
    ON date(f.trade_date)=date(h.trade_date)
    AND f.symbol=h.symbol

    JOIN forward_returns r

      ON date(f.trade_date)=date(r.trade_date)
     AND f.symbol=r.symbol

    WHERE r.return_20d IS NOT NULL
    """

    df = pd.read_sql(query, conn)

    conn.close()

    pos_cut = df["position_52w"].quantile(0.20)
    vol_cut = df["volume_expansion"].quantile(0.80)
    sector_cut = df["sector_strength"].quantile(0.80)   

    signals = df[
        (df["position_52w"] <= pos_cut)
        &
        (df["volume_expansion"] >= vol_cut)
         &
        (df["sector_strength"] >= sector_cut)
    ]

    win_rate = (
        (signals["return_20d"] > 0)
        .mean()
        * 100
    )

    avg_return = (
        signals["return_20d"]
        .mean()
    )

    confidence = (
        (win_rate * 0.7)
        +
        (min(avg_return, 5) * 6)
    )

    confidence = min(
        round(confidence, 1),
        100
    )

    return {
        "win_rate": round(win_rate, 2),
        "avg_return": round(avg_return, 2),
        "confidence": confidence
    }


if __name__ == "__main__":

    result = get_signal_probability()

    print("\nPROBABILITY ENGINE")
    print("=" * 50)

    print(
        f"Win Rate      : {result['win_rate']}%"
    )

    print(
        f"Avg Return    : {result['avg_return']}%"
    )

    print(
        f"Confidence    : {result['confidence']}/100"
    )