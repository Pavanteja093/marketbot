import sqlite3
import pandas as pd
from pathlib import Path
from database.db import get_connection

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def get_latest_option_chain(symbol):

    conn = sqlite3.connect(DB_PATH)

    query = """
    SELECT *

    FROM option_chain_history

    WHERE symbol = ?

    AND trade_time = (

        SELECT MAX(trade_time)

        FROM option_chain_history

        WHERE symbol = ?

    )
    """

    df = pd.read_sql(query, conn, params=(symbol, symbol))

    conn.close()

    return df


def save_iv_analysis(
    trade_time,
    symbol,
    avg_call_iv,
    avg_put_iv,
    avg_iv,
    iv_regime,
    recommended_strategy
):

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR REPLACE INTO iv_analysis
    (
        trade_time,
        symbol,
        avg_call_iv,
        avg_put_iv,
        avg_iv,
        iv_regime,
        recommended_strategy
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        trade_time,
        symbol,
        avg_call_iv,
        avg_put_iv,
        avg_iv,
        iv_regime,
        recommended_strategy
    ))

    conn.commit()
    conn.close()

def get_latest_market_features(symbol):

    conn = sqlite3.connect(DB_PATH)

    query = """
    SELECT *

    FROM market_features

    WHERE symbol = ?

    ORDER BY trade_time DESC

    LIMIT 1
    """

    df = pd.read_sql(
        query,
        conn,
        params=(symbol,)
    )

    conn.close()

    return df

from core.market_state import MarketState


def get_market_state(symbol):
    """
    Returns the latest MarketState for one instrument.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            trade_time,
            symbol,
            spot_price,
            real_pcr,
            support,
            resistance,
            max_pain,
            avg_iv,
            delta,
            gamma,
            theta,
            vega,
            iv_regime,
            market_bias,
            confidence,
            strategy
        FROM market_features
        WHERE symbol = ?
        ORDER BY trade_time DESC
        LIMIT 1
    """, (symbol,))

    row = cursor.fetchone()

    conn.close()

    if row is None:
        return None

    return MarketState(
        symbol=row[1],
        trade_time=row[0],
        spot_price=row[2],
        change_pct=0.0,

        support=row[4],
        resistance=row[5],
        max_pain=row[6],

        pcr=row[3],
        avg_iv=row[7],

        delta=row[8],
        gamma=row[9],
        theta=row[10],
        vega=row[11],

        reward_risk=0.0,
        market_location="UNKNOWN",
        expected_move=0.0,
        trade_quality=0.0,

        iv_regime=row[12],

        market_bias=row[13],
        confidence=row[14],
        recommended_strategy=row[15]
)