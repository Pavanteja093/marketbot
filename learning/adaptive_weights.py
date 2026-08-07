import sqlite3


def save_weight(name, value):

    conn = sqlite3.connect(
        "market_intelligence.db"
    )

    conn.execute(
        """
        INSERT OR REPLACE INTO adaptive_weights
        VALUES (?, ?)
        """,
        (name, value)
    )

    conn.commit()

    conn.close()
def load_weights(conn):

    rows = conn.execute(

        """

        SELECT

            factor,

            weight

        FROM adaptive_weights

        """

    ).fetchall()

    return {

        row[0]: row[1]

        for row in rows

    }