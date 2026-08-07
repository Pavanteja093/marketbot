import pandas as pd

from database.db import get_connection


def build_ml_dataset():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT
            intelligence_score,
            relative_strength,
            trend_score,
            momentum_score,
            volatility_score,
            liquidity_score,
            return_5d
        FROM factor_history f
        JOIN forward_returns r
            ON f.index_name=r.symbol
           AND f.trade_date=r.trade_date
        """,
        conn
    )

    conn.close()

    print()
    print("="*60)
    print("ML DATASET")
    print("="*60)

    print(df.head())

    return df


if __name__=="__main__":
    build_ml_dataset()