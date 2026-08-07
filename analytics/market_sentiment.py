from database.db import get_connection

import pandas as pd


def sentiment():

    conn = get_connection()

    df = pd.read_sql(

        """

        SELECT intelligence_score

        FROM factor_history

        """,

        conn

    )

    conn.close()

    if df.empty:

        return "UNKNOWN"

    avg = df["intelligence_score"].mean()

    if avg >= 80:

        return "BULLISH"

    elif avg >= 60:

        return "POSITIVE"

    elif avg >= 40:

        return "NEUTRAL"

    else:

        return "BEARISH"