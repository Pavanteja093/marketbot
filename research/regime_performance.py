import pandas as pd
from database.db import get_connection

def regime_performance():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT
            regime,
            intelligence_score
        FROM factor_history
        WHERE regime IS NOT NULL
        """,
        conn
    )

    conn.close()

    if df.empty:
        print("No regime data.")
        return

    print("\n" + "=" * 60)
    print("REGIME PERFORMANCE")
    print("=" * 60)

    print(
        df.groupby("regime")
        .agg(
            AverageScore=("intelligence_score", "mean"),
            Stocks=("intelligence_score", "count")
        )
        .round(2)
    )


if __name__ == "__main__":
    regime_performance()