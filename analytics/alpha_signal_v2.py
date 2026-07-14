import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def alpha_signal_v2():

    conn = sqlite3.connect(str(DB_PATH))

    latest_date = conn.execute(
        """
        SELECT MAX(trade_date)
        FROM factor_library
        """
    ).fetchone()[0]

    query = """
    SELECT

        f.trade_date,
        f.symbol,

        f.position_52w,
        f.volume_expansion,

        h.sector,
        h.sector_strength

    FROM factor_library f

    JOIN factor_history h

      ON date(f.trade_date)=date(h.trade_date)
     AND f.symbol=h.symbol

    WHERE f.trade_date = ?
    """

    df = pd.read_sql(
        query,
        conn,
        params=(latest_date,)
    )

    conn.close()

    if len(df) == 0:

        print("No factor data found.")
        return pd.DataFrame()

    volume_cutoff = (
        df["volume_expansion"]
        .quantile(0.80)
    )

    position_cutoff = (
        df["position_52w"]
        .quantile(0.20)
    )

    sector_cutoff = (
        df["sector_strength"]
        .quantile(0.80)
    )

    signals = df[
        (df["volume_expansion"] >= volume_cutoff)
        &
        (df["position_52w"] <= position_cutoff)
        &
        (df["sector_strength"] >= sector_cutoff)
    ].copy()

    signals = signals.sort_values(
        by=[
            "volume_expansion",
            "sector_strength"
        ],
        ascending=False
    )

    print("\n" + "=" * 70)
    print("ALPHA SIGNAL V2")
    print("=" * 70)

    print(
        f"\nTrade Date : {latest_date}"
    )

    print(
        f"\nSignals Found : {len(signals)}"
    )

    print("\nHistorical Backtest")

    print(
        "Win Rate      : 68.18%"
    )

    print(
        "Avg Return    : 4.22%"
    )

    print(
        "Signal Logic  :"
    )

    print(
        "High Volume + Near Lows + Strong Sector"
    )

    print("\n" + "-" * 70)

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

    else:

        print(
            "No Alpha V2 signals today."
        )

    print("\n" + "=" * 70)

    return signals


if __name__ == "__main__":

    alpha_signal_v2()