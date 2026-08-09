import sqlite3

from database.db import get_connection


def save_prediction(

    trade_date,

    index_name,

    intelligence_score,

    prediction

):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(

        """

        INSERT INTO prediction_history(

            trade_date,

            index_name,

            intelligence_score,

            prediction,

            prediction_correct

        )

        VALUES(?,?,?,?,0)

        """,

        (

            trade_date,

            index_name,

            intelligence_score,

            prediction

        )

    )

    conn.commit()

    conn.close()