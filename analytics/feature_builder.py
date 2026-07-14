from database.repository import (
    get_latest_option_chain
)

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def save_features(
    trade_time,
    symbol,
    spot_price,
    avg_iv,
    iv_regime,
    strategy
):

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR REPLACE INTO market_features
    (
        trade_time,
        symbol,
        spot_price,
        avg_iv,
        iv_regime,
        strategy
    )

    VALUES
    (
        ?, ?, ?, ?, ?, ?
    )
    """,(
        trade_time,
        symbol,
        spot_price,
        avg_iv,
        iv_regime,
        strategy
    ))

    conn.commit()
    conn.close()


def build_features():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    rows = cursor.execute("""

    SELECT *

    FROM iv_analysis

    """).fetchall()

    conn.close()

    for row in rows:

        trade_time = row[0]
        symbol = row[1]

        df = get_latest_option_chain(symbol)

        if df.empty:
            continue

        spot_price = df.iloc[0]["spot_price"]

        save_features(

            trade_time,

            symbol,

            spot_price,

            row[4],      # avg_iv

            row[5],      # regime

            row[6]       # strategy

        )

    print("\nFeature Store Updated")


if __name__ == "__main__":

    build_features()