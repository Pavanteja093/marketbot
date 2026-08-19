import pandas as pd

from database.db import get_connection
from models.market_state import MarketState


def get_latest_option_chain(symbol):
    conn = get_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT *
            FROM option_chain_history
            WHERE symbol = ?
              AND trade_time = (
                  SELECT MAX(trade_time)
                  FROM option_chain_history
                  WHERE symbol = ?
              )
            ORDER BY strike
            """,
            conn,
            params=(symbol, symbol)
        )
    finally:
        conn.close()


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
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO iv_analysis
            (
                analysis_time,
                index_name,
                avg_call_iv,
                avg_put_iv,
                avg_iv,
                iv_regime,
                recommendation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade_time,
                symbol,
                avg_call_iv,
                avg_put_iv,
                avg_iv,
                iv_regime,
                recommended_strategy
            )
        )
        conn.commit()
    finally:
        conn.close()


def get_latest_market_features(symbol):
    conn = get_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT *
            FROM market_features
            WHERE symbol = ?
            ORDER BY trade_time DESC
            LIMIT 1
            """,
            conn,
            params=(symbol,)
        )
    finally:
        conn.close()


def get_market_state(symbol="NIFTY"):
    conn = get_connection()

    try:
        row = conn.execute(
            """
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
            """,
            (symbol,)
        ).fetchone()

        if row is None:
            return None

        return MarketState(
            symbol=row["symbol"],
            trade_time=row["trade_time"],
            spot_price=row["spot_price"] or 0.0,
            change_pct=0.0,
            support=row["support"] or 0.0,
            resistance=row["resistance"] or 0.0,
            max_pain=row["max_pain"] or 0.0,
            pcr=row["real_pcr"] or 0.0,
            avg_iv=row["avg_iv"] or 0.0,
            delta=row["delta"] or 0.0,
            gamma=row["gamma"] or 0.0,
            theta=row["theta"] or 0.0,
            vega=row["vega"] or 0.0,
            expected_move=row["expected_move"] or 0.0,
            reward_risk=row["reward_risk"] or 0.0,
            market_location=row["market_location"] or "UNKNOWN",
            trade_quality=row["trade_quality"] or 0.0,
            iv_regime=row["iv_regime"] or "UNKNOWN",
            market_bias=row["market_bias"] or "NEUTRAL",
            confidence=row["confidence"] or 0.0,
            recommended_strategy=row["strategy"] or ""
        )

    finally:
        conn.close()


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
        symbols = ["SENSEX", "NIFTY", "BANKNIFTY", "FINNIFTY"]
        return {
            symbol: get_market_state(symbol)
            for symbol in symbols
        }

    @staticmethod
    def latest_indices():
        conn = get_connection()
        try:
            return conn.execute(
                """
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
                """
            ).fetchall()
        finally:
            conn.close()

    @staticmethod
    def top_gainers(limit=5):
        conn = get_connection()
        try:
            return conn.execute(
                """
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
                """,
                (limit,)
            ).fetchall()
        finally:
            conn.close()

    @staticmethod
    def top_losers(limit=5):
        conn = get_connection()
        try:
            return conn.execute(
                """
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
                """,
                (limit,)
            ).fetchall()
        finally:
            conn.close()
