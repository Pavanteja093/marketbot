import sqlite3
import pandas as pd

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def factor_importance():

    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql("""

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

        ON f.trade_date=r.trade_date

        AND f.index_name=r.symbol

    """, conn)

    conn.close()

    print(df.corr()["return_5d"].sort_values(ascending=False))


if __name__ == "__main__":

    factor_importance()