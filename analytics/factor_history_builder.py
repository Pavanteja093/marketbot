import pandas as pd

from analytics.intelligence_score import calculate_intelligence
from analytics.feature_engine import FeatureEngine
from database.db import get_connection


engine = FeatureEngine()


def build_factor_history():

    conn = get_connection()

    cursor = conn.cursor()

    symbols = pd.read_sql(
        """
        SELECT DISTINCT symbol
        FROM stocks_daily
        ORDER BY symbol
        """,
        conn
    )

    print(f"\nFound {len(symbols)} stocks.")

    for symbol in symbols["symbol"]:

        history_df = pd.read_sql(
            """
            SELECT *
            FROM stocks_daily
            WHERE symbol=?
            ORDER BY trade_date
            """,
            conn,
            params=(symbol,)
        )
        print(f"{symbol}: {len(history_df)} rows")

        if len(history_df) < 20:
            print(f"Skipping {symbol}")
            continue

        stock_return = history_df.iloc[-1]["change_pct"]

        features = engine.build_features(
            history_df=history_df,
            stock_return=stock_return,
            market_returns=0
        )
        print(features)

        intelligence_score = features["intelligence_score"]

        cursor.execute(
            """
            INSERT OR REPLACE INTO factor_history
            (
                trade_date,
                index_name,

                relative_strength,
                rs_grade,

                trend_score,
                trend_grade,

                momentum_score,
                momentum_grade,

                volatility_score,
                volatility_grade,

                liquidity_score,
                liquidity_grade,

                intelligence_score,

                prediction,

                actual-return,

                prediction_correct

            )

            VALUES
            (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                history_df.iloc[-1]["trade_date"],
                symbol,

                features["relative_strength"],
                features["rs_grade"],

                features["trend_score"],
                features["trend_grade"],

                features["momentum_score"],
                features["momentum_grade"],

                features["volatility_score"],
                features["volatility_grade"],

                features["liquidity_score"],
                features["liquidity_grade"],

                intelligence_score,
                features["signal"],

                0,

                0
            )
        )
        print(f"Inserting {symbol}")

    conn.commit()

    print("\nFactor History Updated")

    conn.close()
    
    print("\nFactor History Builder Complete")


if __name__ == "__main__":
    build_factor_history()