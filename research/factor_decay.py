import sqlite3
import pandas as pd

from database.db import get_connection


def factor_decay():

    conn = get_connection()

    df = pd.read_sql("""

        SELECT

            intelligence_score,

            return_5d,

            return_10d,

            return_20d

        FROM factor_history f

        JOIN forward_returns r

        ON f.trade_date=r.trade_date

        AND f.index_name=r.symbol

    """, conn)

    conn.close()

    print(df.corr())


if __name__ == "__main__":

    factor_decay()