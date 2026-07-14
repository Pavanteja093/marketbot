import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


sys.path.append(str(BASE_DIR))

import sqlite3
import pandas as pd

from analytics.ranking_engine_v2 import rank_signals
from analytics.ranking_engine_v2 import rank_signals


DB_PATH = BASE_DIR / "market_intelligence.db"


def alpha_signal_v3():

    conn = sqlite3.connect(str(DB_PATH))

    regime = pd.read_sql(
        """
        SELECT regime
        FROM market_regime
        ORDER BY trade_date DESC
        LIMIT 1
        """,
        conn
    ).iloc[0]["regime"]

    query = """
    SELECT

        h.symbol,
        h.sector,
        h.sector_strength,
        h.intelligence_score,

        f.position_52w,
        f.volume_expansion

    FROM factor_history h

    JOIN factor_library f

      ON date(h.trade_date)=date(f.trade_date)
     AND h.symbol=f.symbol

    WHERE h.trade_date = (
        SELECT MAX(trade_date)
        FROM factor_history
    )
    """

    df = pd.read_sql(query, conn)

    conn.close()

    signals = df[
        (df["volume_expansion"] >= 1.5)
        &
        (df["position_52w"] <= 20)
        &
        (df["sector_strength"] > 0)
    ].copy()

    if regime == "BEARISH":

        expected_return = 4.23
        confidence = "HIGH"

    elif regime == "SIDEWAYS":

        expected_return = 0.79
        confidence = "MEDIUM"

    else:

        expected_return = 1.74
        confidence = "MEDIUM"

    signals["expected_return"] = expected_return
    signals["confidence"] = confidence
    signals["regime"] = regime

    signals = rank_signals(signals)

    print("\n" + "=" * 70)
    print("ALPHA SIGNAL V3")
    print("=" * 70)

    print(f"\nMarket Regime : {regime}")
    print(f"Signals Found : {len(signals)}")

    if len(signals) > 0:

        print(
            signals[
                [
                    "symbol",
                    "sector",
                    "position_52w",
                    "volume_expansion",
                    "sector_strength"
                ]
            ]
            .round(2)
            .to_string(index=False)
        )

    return signals


if __name__ == "__main__":

    alpha_signal_v3()