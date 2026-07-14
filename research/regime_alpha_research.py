import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def regime_alpha_research():

    conn = sqlite3.connect(str(DB_PATH))

    query = """
    SELECT

        r.regime,

        f.position_52w,
        f.volume_expansion,

        h.sector_strength,

        fr.return_20d

    FROM factor_library f

    JOIN factor_history h

      ON date(f.trade_date)=date(h.trade_date)
     AND f.symbol=h.symbol

    JOIN forward_returns fr

      ON date(f.trade_date)=date(fr.trade_date)
     AND f.symbol=fr.symbol

    JOIN market_regime r

      ON date(f.trade_date)=date(r.trade_date)

    WHERE fr.return_20d IS NOT NULL
    """

    df = pd.read_sql(query, conn)

    conn.close()

    vol80 = df["volume_expansion"].quantile(0.80)
    low20 = df["position_52w"].quantile(0.20)
    sector80 = df["sector_strength"].quantile(0.80)

    signals = df[
        (df["volume_expansion"] >= vol80)
        &
        (df["position_52w"] <= low20)
        &
        (df["sector_strength"] >= sector80)
    ].copy()

    print("\n" + "=" * 70)
    print("ALPHA V2 BY MARKET REGIME")
    print("=" * 70)

    for regime in [
        "BULLISH",
        "SIDEWAYS",
        "BEARISH"
    ]:

        temp = signals[
            signals["regime"] == regime
        ]

        if len(temp) == 0:
            continue

        win_rate = (
            (temp["return_20d"] > 0)
            .mean()
            * 100
        )

        avg_return = (
            temp["return_20d"]
            .mean()
        )

        print("\n" + "-" * 70)

        print(f"REGIME: {regime}")

        print(
            f"Signals    : {len(temp)}"
        )

        print(
            f"Win Rate   : {win_rate:.2f}%"
        )

        print(
            f"Avg Return : {avg_return:.2f}%"
        )

    print("\n" + "=" * 70)


if __name__ == "__main__":

    regime_alpha_research()