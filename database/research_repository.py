import sqlite3
import pandas as pd

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "market_intelligence.db"

def get_trend_research():

    conn = sqlite3.connect(str(DB_PATH))

    df = pd.read_sql(
        "SELECT * FROM trend_day_research ORDER BY trade_date",
        conn
    )

    conn.close()

    return df

def get_latest_trend_research():

    conn = sqlite3.connect(str(DB_PATH))

    df = pd.read_sql(
        """
        SELECT *
        FROM trend_day_research
        WHERE trade_date =
        (
            SELECT MAX(trade_date)
            FROM trend_day_research
        )
        """,
        conn
    )

    conn.close()

    return df

def save_trend_research(record):

    conn = sqlite3.connect(str(DB_PATH))

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO trend_day_research
        (
            trade_date,
            index_name,
            trendiness_score,
            efficiency_ratio,
            gap_percent,
            close_return,
            atr_multiple
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["trade_date"],
            record["index_name"],
            record["trendiness_score"],
            record["efficiency_ratio"],
            record["gap_percent"],
            record["close_return"],
            record["atr_multiple"]
        )
    )

    conn.commit()

    conn.close()

def get_research_between_dates(
    start_date,
    end_date
):

    conn = sqlite3.connect(str(DB_PATH))

    df = pd.read_sql(
        """
        SELECT *
        FROM trend_day_research
        WHERE trade_date
        BETWEEN ? AND ?
        ORDER BY trade_date
        """,
        conn,
        params=(start_date, end_date)
    )

    conn.close()

    return df
    pass