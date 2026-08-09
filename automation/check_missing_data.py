from database.db import get_connection

import pandas as pd


def missing_days(table):

    conn = get_connection()

    df = pd.read_sql(

        f"""

        SELECT trade_date

        FROM {table}

        ORDER BY trade_date

        """,

        conn

    )

    conn.close()

    if df.empty:

        return

    dates = pd.DatetimeIndex(pd.to_datetime(df.trade_date))

    expected = pd.date_range(

        dates.min(),

        dates.max(),

        freq="B"

    )

    missing = expected.difference(dates)

    print("\n", table)

    print(missing)


if __name__ == "__main__":

    missing_days("stocks_daily")

    missing_days("indices_daily")