import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def save_learning_record(record):

    conn = sqlite3.connect(str(DB_PATH))

    conn.execute(
        """
        INSERT OR REPLACE INTO learning_history (

            trade_date,
            symbol,

            prediction,
            actual_outcome,

            confidence,
            strategy,
            trade_quality,

            spot_price,
            next_close,

            next_day_return,
            five_day_return,

            correct

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,

        (
            record["trade_date"],
            record["symbol"],

            record["prediction"],
            record["actual_outcome"],

            record["confidence"],
            record["strategy"],
            record["trade_quality"],

            record["spot_price"],
            record["next_close"],

            record["next_day_return"],
            record["five_day_return"],

            record["correct"]
        )

    )

    conn.commit()

    conn.close()

def save_market_prediction(record):

    conn = sqlite3.connect(str(DB_PATH))

    conn.execute(
        """
        INSERT OR REPLACE INTO market_prediction_history(

            trade_time,
            symbol,

            prediction,
            confidence,

            strategy,
            trade,

            risk,
            score,

            support,
            resistance,

            spot_price,
            pcr,
            avg_iv

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,

        (

            record["trade_time"],
            record["symbol"],

            record["prediction"],
            record["confidence"],

            record["strategy"],
            record["trade"],

            record["risk"],
            record["score"],

            record["support"],
            record["resistance"],

            record["spot_price"],
            record["pcr"],
            record["avg_iv"]

        )

    )

    conn.commit()

    conn.close()

def get_pending_predictions():

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT *
        FROM market_prediction_history
        WHERE processed = 0
        ORDER BY trade_time
        """
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


def mark_prediction_processed(prediction_id):

    conn = sqlite3.connect(str(DB_PATH))

    conn.execute(
        """
        UPDATE market_prediction_history
        SET processed = 1
        WHERE id = ?
        """,
        (prediction_id,)
    )

    conn.commit()
    conn.close()



def get_next_index_close(symbol, trade_time):

    # Temporary mapping
    if symbol == "NIFTY":
        symbol = "NIFTY50"

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    row = conn.execute(
        """
        SELECT
            trade_date,
            close
        FROM indices_daily
        WHERE index_name = ?
        AND trade_date > DATE(?)
        ORDER BY trade_date
        LIMIT 1
        """,
        (
            symbol,
            trade_time
        )
    ).fetchone()

    conn.close()

    if row is None:
        return None

    return dict(row)

def get_learning_history():

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT *
        FROM learning_history
        ORDER BY trade_date DESC
        """
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]