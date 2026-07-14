import sqlite3
import pandas as pd
from pathlib import Path

from analytics.sector_mapping import SECTORS

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def get_stock_scores(trade_date=None):

    conn = sqlite3.connect(str(DB_PATH))

    if trade_date is None:

        query = """
        SELECT
             symbol,
            close,
            volume,
            change_pct
        FROM stocks_daily
        WHERE trade_date = (
            SELECT MAX(trade_date)
            FROM stocks_daily
        )
        """
    else:

        query= f"""
        SELECT
            symbol,
            close,
            volume,
            change_pct
        FROM stocks_daily
        WHERE trade_date = '{trade_date}'
        """        


    df = pd.read_sql(query, conn)

    conn.close()

    # -----------------------------
    # Sector Mapping
    # -----------------------------

    sector_lookup = {}

    for sector, stocks in SECTORS.items():

        for stock in stocks:

            sector_lookup[stock] = sector

    df["sector"] = df["symbol"].map(
        sector_lookup
    )

    # -----------------------------
    # Sector Strength
    # -----------------------------

    sector_strength = (
        df.groupby("sector")["change_pct"]
        .mean()
        .to_dict()
    )

    df["sector_strength"] = (
        df["sector"]
        .map(sector_strength)
    )

    # -----------------------------
    # Scoring
    # -----------------------------

    df["price_score"] = (
        df["change_pct"].rank(pct=True) * 40
    )

    df["volume_score"] = (
        df["volume"].rank(pct=True) * 30
    )

    df["sector_score"] = (
        df["sector_strength"].rank(pct=True) * 30
    )

    df["total_score"] = (
        df["price_score"]
        + df["volume_score"]
        + df["sector_score"]
    )

    # -----------------------------
    # Grade
    # -----------------------------

    def get_grade(score):

        if score >= 85:
            return "A"

        elif score >= 70:
            return "B"

        else:
            return "C"

    df["grade"] = (
        df["total_score"]
        .apply(get_grade)
    )

    df = df.sort_values(
        by="total_score",
        ascending=False
    )

    df = df.reset_index(
        drop=True
    )

    return df


def save_signals(df):

    conn = sqlite3.connect(str(DB_PATH))

    latest_date = pd.read_sql(
        """
        SELECT MAX(trade_date) AS trade_date
        FROM stocks_daily
        """,
        conn
    ).iloc[0]["trade_date"]

    # -----------------------------
    # Delete Existing Signals
    # -----------------------------

    conn.execute(
        """
        DELETE FROM signal_history
        WHERE trade_date = ?
        """,
        (latest_date,)
    )

    # -----------------------------
    # Save Top 10 Signals
    # -----------------------------

    top10 = df.head(10)

    for rank, (_, row) in enumerate(
        top10.iterrows(),
        start=1
    ):

        conn.execute(
            """
            INSERT INTO signal_history
            (
                trade_date,
                symbol,
                sector,
                score,
                rank
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                latest_date,
                row["symbol"],
                row["sector"],
                float(row["total_score"]),
                rank
            )
        )

    conn.commit()

    conn.close()

    print(
        f"\nSaved {len(top10)} signals for {latest_date}"
    )


# -----------------------------------
# STANDALONE EXECUTION
# -----------------------------------

if __name__ == "__main__":

    df = get_stock_scores()

    save_signals(df)

    print("\n" + "=" * 70)
    print("STOCK SCORING ENGINE")
    print("=" * 70)

    print(
        df[
            [
                "grade",
                "symbol",
                "sector",
                "change_pct",
                "sector_strength",
                "total_score"
            ]
        ]
        .head(15)
        .to_string(index=False)
    )