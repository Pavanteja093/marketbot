import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

import sqlite3

from analytics.alpha_signal_v3 import alpha_signal_v3

DB_PATH = BASE_DIR / "market_intelligence.db"


def daily_recommendation():

    signals = alpha_signal_v3()

    if len(signals) == 0:

        print("No signals found.")
        return

    top = signals.iloc[0]

    print("\n" + "=" * 70)
    print("DAILY RECOMMENDATION")
    print("=" * 70)

    print(f"\nSymbol            : {top['symbol']}")
    print(f"Regime            : {top['regime']}")
    print(f"Expected Return   : {top['expected_return']:.2f}%")
    print(f"Confidence        : {top['confidence']}")

    conn = sqlite3.connect(str(DB_PATH))

    conn.execute(
        """
        INSERT INTO daily_recommendations (

            trade_date,
            symbol,
            regime,
            expected_return,
            confidence,
            weight_pct

        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            None,
            top["symbol"],
            top["regime"],
            top["expected_return"],
            top["confidence"],
            100
        )
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":

    daily_recommendation()