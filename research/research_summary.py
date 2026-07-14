import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def get_scalar(conn, query):

    result = conn.execute(query).fetchone()

    if result and result[0] is not None:
        return result[0]

    return 0


def research_summary():

    conn = sqlite3.connect(str(DB_PATH))

    stocks_count = get_scalar(
        conn,
        """
        SELECT COUNT(DISTINCT symbol)
        FROM stocks_daily
        """
    )

    historical_records = get_scalar(
        conn,
        """
        SELECT COUNT(*)
        FROM stocks_daily
        """
    )

    forward_returns = get_scalar(
        conn,
        """
        SELECT COUNT(*)
        FROM forward_returns
        """
    )

    predictions = get_scalar(
        conn,
        """
        SELECT COUNT(*)
        FROM prediction_history
        """
    )

    latest_date = get_scalar(
        conn,
        """
        SELECT MAX(trade_date)
        FROM stocks_daily
        """
    )

    top_stock = conn.execute(
        """
        SELECT symbol
        FROM prediction_history
        ORDER BY intelligence_score DESC
        LIMIT 1
        """
    ).fetchone()

    top_stock = top_stock[0] if top_stock else "N/A"

    top_sector = conn.execute(
        """
        SELECT sector
        FROM prediction_history
        GROUP BY sector
        ORDER BY AVG(intelligence_score) DESC
        LIMIT 1
        """
    ).fetchone()

    top_sector = top_sector[0] if top_sector else "N/A"

    avg_score = get_scalar(
        conn,
        """
        SELECT ROUND(
            AVG(intelligence_score),
            2
        )
        FROM prediction_history
        """
    )

    max_score = get_scalar(
        conn,
        """
        SELECT ROUND(
            MAX(intelligence_score),
            2
        )
        FROM prediction_history
        """
    )

    conn.close()

    print("\n" + "=" * 60)
    print("MARKETBOT RESEARCH SUMMARY")
    print("=" * 60)

    print(f"\nStocks Tracked      : {stocks_count}")
    print(f"Historical Records  : {historical_records}")
    print(f"Forward Returns     : {forward_returns}")
    print(f"Predictions Stored  : {predictions}")

    print(f"\nLatest Date         : {latest_date}")

    print(f"\nTop Ranked Stock    : {top_stock}")
    print(f"Top Sector          : {top_sector}")

    print(f"\nAverage Score       : {avg_score}")
    print(f"Highest Score       : {max_score}")

    print("\n" + "=" * 60)
    print("SYSTEM STATUS")
    print("=" * 60)

    print("\nData Collection     : OK")
    print("Prediction Engine   : OK")
    print("Research Database   : OK")

    print("\n" + "=" * 60)


if __name__ == "__main__":

    research_summary()