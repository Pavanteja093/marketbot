import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def alpha_signal_backtest():

    conn = sqlite3.connect(str(DB_PATH))

    query = """
    SELECT

        f.position_52w,
        f.volume_expansion,

        r.return_5d,
        r.return_10d,
        r.return_20d

    FROM factor_library f

    JOIN forward_returns r

      ON date(f.trade_date)=date(r.trade_date)
     AND f.symbol=r.symbol

    WHERE r.return_20d IS NOT NULL
    """

    df = pd.read_sql(query, conn)

    conn.close()

    pos_cut = df["position_52w"].quantile(0.20)
    vol_cut = df["volume_expansion"].quantile(0.80)

    signals = df[
        (df["position_52w"] <= pos_cut)
        &
        (df["volume_expansion"] >= vol_cut)
    ].copy()

    print("\n" + "=" * 70)
    print("ALPHA SIGNAL BACKTEST")
    print("=" * 70)

    print(f"\nSignals Tested : {len(signals):,}")

    print(
        f"Win Rate 20D : "
        f"{(signals['return_20d'] > 0).mean()*100:.2f}%"
    )

    print(
        f"Avg 20D Return : "
        f"{signals['return_20d'].mean():.2f}%"
    )

    print(
        f"Median Return : "
        f"{signals['return_20d'].median():.2f}%"
    )

    print(
        f"Best Return : "
        f"{signals['return_20d'].max():.2f}%"
    )

    print(
        f"Worst Return : "
        f"{signals['return_20d'].min():.2f}%"
    )

    print("\n" + "=" * 70)


if __name__ == "__main__":
    alpha_signal_backtest()