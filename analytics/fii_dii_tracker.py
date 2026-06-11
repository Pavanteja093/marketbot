import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def get_fii_dii():

    conn = sqlite3.connect(str(DB_PATH))

    query = """
    SELECT *
    FROM fii_dii_daily
    ORDER BY trade_date DESC
    LIMIT 1
    """

    df = pd.read_sql(query, conn)

    conn.close()

    if len(df) == 0:

        return {
            "available": False
        }

    row = df.iloc[0]

    fii_interpretation = (
        "Net Buyer"
        if row["fii_net"] > 0
        else "Net Seller"
    )

    dii_interpretation = (
        "Net Buyer"
        if row["dii_net"] > 0
        else "Net Seller"
    )

    return {
        "available": True,
        "trade_date": row["trade_date"],
        "fii_net": row["fii_net"],
        "dii_net": row["dii_net"],
        "fii_view": fii_interpretation,
        "dii_view": dii_interpretation
    }


# -----------------------------------
# STANDALONE EXECUTION
# -----------------------------------

if __name__ == "__main__":

    result = get_fii_dii()

    print("\n" + "=" * 60)
    print("FII / DII ACTIVITY")
    print("=" * 60)

    if not result["available"]:

        print("\nNo data available")

    else:

        print(
            f"\nDate : "
            f"{result['trade_date']}"
        )

        print(
            f"FII Net : "
            f"₹{result['fii_net']:,.0f} Cr"
        )

        print(
            f"DII Net : "
            f"₹{result['dii_net']:,.0f} Cr"
        )

        print(
            f"\nFII View : "
            f"{result['fii_view']}"
        )

        print(
            f"DII View : "
            f"{result['dii_view']}"
        )