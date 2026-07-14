import sys

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

sys.path.append(str(BASE_DIR))

import sqlite3
import pandas as pd

DB_PATH = BASE_DIR / "market_intelligence.db"


def performance_widget():

    conn = sqlite3.connect(str(DB_PATH))

    query = """
    SELECT

        regime,

        AVG(expected_return) AS avg_return,
        COUNT(*) AS recommendations

    FROM daily_recommendations

    GROUP BY regime
    """

    df = pd.read_sql(query, conn)

    conn.close()

    return df