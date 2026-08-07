import pandas as pd

from database.db import get_connection


def feature_stability():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT
            relative_strength,
            trend_score,
            momentum_score,
            volatility_score,
            liquidity_score
        FROM factor_history
        """,
        conn
    )

    conn.close()

    print("\n" + "=" * 60)
    print("FEATURE STABILITY")
    print("=" * 60)

    print(df.std().sort_values())
    

if __name__ == "__main__":
    feature_stability()