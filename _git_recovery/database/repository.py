import pandas as pd
from database.db import get_connection

def get_latest_option_chain(symbol):

    conn = get_connection()

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

    conn = get_connection()

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

    conn = get_connection()

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

from models.market_state import MarketState


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
            strategy,
            expected_move,
            reward_risk,
            market_location,
            trade_quality
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

        expected_move=row[16],
        reward_risk=row[17],
        market_location=row[18],
        trade_quality=row[19],

        iv_regime=row[12],

        market_bias=row[13],
        confidence=row[14],
        recommended_strategy=row[15]
)

class Repository:

    @staticmethod
    def market_state(symbol):
        return get_market_state(symbol)

    @staticmethod
    def option_chain(symbol):
        return get_latest_option_chain(symbol)

    @staticmethod
    def market_features(symbol):
        return get_latest_market_features(symbol)


    @staticmethod
    def all_market_states():
        """
        Returns the latest MarketState for every supported index.
        """

        symbols = [
            "NIFTY",
            "BANKNIFTY",
            "FINNIFTY"
        ]

        states = {}

        for symbol in symbols:
            try:
                states[symbol] = Repository.market_state(symbol)
            except Exception as e:
                print(f"Unable to load {symbol}: {e}")

        return states

    @staticmethod
    def latest_indices():
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                index_name,
                open,
                high,
                low,
                close,
                change_pct
            FROM indices_daily
            WHERE trade_date = (
                SELECT MAX(trade_date)
                FROM indices_daily
            )
            ORDER BY index_name
        """)

        rows = rows = cursor.fetchall()
        conn.close()

        return rows

    @staticmethod
    def top_gainers(limit=5):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                symbol,
                close,
                price_change,
                change_pct
            FROM stocks_daily
            WHERE trade_date = (
                SELECT MAX(trade_date)
                FROM stocks_daily
            )
            ORDER BY change_pct DESC
            LIMIT ?
        """, (limit,))

        rows = rows = cursor.fetchall()
        conn.close()

        return rows

    @staticmethod
    def top_losers(limit=5):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                symbol,
                close,
                price_change,
                change_pct
            FROM stocks_daily
            WHERE trade_date = (
                SELECT MAX(trade_date)
                FROM stocks_daily
            )
            ORDER BY change_pct ASC
            LIMIT ?
        """, (limit,))

        rows = rows = cursor.fetchall()
        conn.close()

        return rows

    
