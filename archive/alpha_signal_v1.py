import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def alpha_signal_v1():

    conn = sqlite3.connect(str(DB_PATH))

    latest_date = conn.execute(
        """
        SELECT MAX(trade_date)
        FROM factor_library
        """
    ).fetchone()[0]

    query = """
    SELECT

        trade_date,
        symbol,

        position_52w,
        volume_expansion

    FROM factor_library

    WHERE trade_date = ?
    """

    df = pd.read_sql(
        query,
        conn,
        params=(latest_date,)
    )

    conn.close()

    if len(df) == 0:

        print("No factor data found.")
        return

    position_cutoff = (
        df["position_52w"]
        .quantile(0.20)
    )

    volume_cutoff = (
        df["volume_expansion"]
        .quantile(0.80)
    )

    signals = df[
        (df["position_52w"] <= position_cutoff)
        &
        (df["volume_expansion"] >= volume_cutoff)
    ].copy()

    signals = signals.sort_values(
        by="volume_expansion",
        ascending=False
    )

    print("\n" + "=" * 70)
    print("ALPHA SIGNAL V1")
    print("=" * 70)

    print(f"\nTrade Date : {latest_date}")

    print(
        f"\nSignals Found : {len(signals)}"
    )

    print(
        "\nHistorical Research:"
    )

    print(
        "High Volume + Near Lows"
    )

    print(
        "Average 20D Return = 1.943%"
    )

    print("\n" + "-" * 70)

    if len(signals) > 0:

        display_cols = [
            "symbol",
            "position_52w",
            "volume_expansion"
        ]

        print(
            signals[display_cols]
            .round(2)
            .to_string(index=False)
        )

    else:

        print(
            "No qualifying stocks today."
        )

    print("\n" + "=" * 70)

    return signals


if __name__ == "__main__":

    alpha_signal_v1()