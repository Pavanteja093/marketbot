import pandas as pd
from pathlib import Path

from database.db import get_connection


def get_market_regime():

    conn = get_connection()

    # -----------------------------------
    # LATEST NIFTY DAsTA
    # -----------------------------------

    index_query = """
    SELECT
        index_name,
        close,
        change_pct
    FROM indices_daily
    WHERE index_name = 'NIFTY50'
    ORDER BY id DESC
    LIMIT 1
    """

    index_df = pd.read_sql(index_query, conn)

    # -----------------------------------
    # MARKET BREADTH
    # -----------------------------------

    breadth_query = """
    SELECT

        COUNT(
            CASE
                WHEN change_pct > 0 THEN 1
            END
        ) AS advancing,

        COUNT(
            CASE
                WHEN change_pct < 0 THEN 1
            END
        ) AS declining

    FROM stocks_daily

    WHERE trade_date = (
        SELECT MAX(trade_date)
        FROM stocks_daily
    )
    """

    breadth_df = pd.read_sql(
        breadth_query,
        conn
    )

    conn.close()

    nifty_change = float(
        index_df["change_pct"].iloc[0]
    )

    advancing = int(
        breadth_df["advancing"].iloc[0]
    )

    declining = int(
        breadth_df["declining"].iloc[0]
    )

    if declining > 0:
        ad_ratio = advancing / declining
    else:
        ad_ratio = 999

    # -----------------------------------
    # REGIME
    # -----------------------------------

    if nifty_change > 0.5 and ad_ratio > 1.2:

        regime = "BULLISH TREND"

    elif nifty_change < -0.5 and ad_ratio < 0.8:

        regime = "BEARISH TREND"

    else:

        regime = "RANGE BOUND"

    return {
        "nifty_change": nifty_change,
        "advancing": advancing,
        "declining": declining,
        "ad_ratio": round(ad_ratio, 2),
        "regime": regime
    }


# -----------------------------------
# STANDALONE EXECUTION
# -----------------------------------

if __name__ == "__main__":

    result = get_market_regime()

    print("\n" + "=" * 50)
    print("MARKET REGIME")
    print("=" * 50)

    print(
        f"\nNIFTY Change : "
        f"{result['nifty_change']}%"
    )

    print(
        f"Advancing Stocks : "
        f"{result['advancing']}"
    )

    print(
        f"Declining Stocks : "
        f"{result['declining']}"
    )

    print(
        f"A/D Ratio : "
        f"{result['ad_ratio']}"
    )

    print(
        f"\nREGIME : "
        f"{result['regime']}"
    )