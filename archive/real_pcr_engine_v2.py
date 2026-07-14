import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def get_real_pcr():

    conn = sqlite3.connect(DB_PATH)

    query = """
    SELECT
        symbol,
        SUM(call_oi) AS total_call_oi,
        SUM(put_oi) AS total_put_oi,
        MAX(spot_price) AS spot_price
    FROM option_chain_history
    GROUP BY symbol
    """

    df = pd.read_sql(query, conn)

    conn.close()

    results = {}

    for _, row in df.iterrows():

        pcr = (
            row["total_put_oi"] /
            row["total_call_oi"]
        )

        if pcr > 1.2:
            bias = "BULLISH"
        elif pcr < 0.8:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"

        results[row["symbol"]] = {
            "spot": row["spot_price"],
            "pcr": round(pcr, 2),
            "bias": bias
        }

    return results