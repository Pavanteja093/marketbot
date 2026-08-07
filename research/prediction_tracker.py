import pandas as pd

from database.db import get_connection


def save_prediction(row):

    conn = get_connection()

    pd.DataFrame([row]).to_sql(
        "prediction_history",
        conn,
        if_exists="append",
        index=False
    )

    conn.close()