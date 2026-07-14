import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def factor_research():

    conn = sqlite3.connect(str(DB_PATH))

    query = """
    SELECT

        f.trade_date,
        f.symbol,

        f.change_pct,
        f.sector_strength,
        f.position_pct,
        f.total_score,
        f.intelligence_score,

        r.return_5d

    FROM factor_history f

    JOIN forward_returns r

        ON date(f.trade_date) = date(r.trade_date)
       AND f.symbol = r.symbol

    WHERE r.return_5d IS NOT NULL
    """

    df = pd.read_sql(query, conn)

    conn.close()

    print("\n" + "=" * 70)
    print("FACTOR RESEARCH")
    print("=" * 70)

    print(f"\nRecords Analysed: {len(df):,}")

    factors = [
        "change_pct",
        "sector_strength",
        "position_pct",
        "total_score",
        "intelligence_score"
    ]

    for factor in factors:

        print("\n" + "-" * 70)
        print(f"FACTOR: {factor}")
        print("-" * 70)

        try:

            df["bucket"] = pd.qcut(
                df[factor],
                q=5,
                duplicates="drop"
            )

            result = (
                df.groupby("bucket")["return_5d"]
                .mean()
                .round(3)
            )

            print(result)

        except Exception as e:

            print(f"Failed: {factor}")
            print(e)

    print("\n" + "=" * 70)


if __name__ == "__main__":
    factor_research()