import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def factor_correlation():

    conn = sqlite3.connect(str(DB_PATH))

    query = """
    SELECT

        f.change_pct,
        f.sector_strength,
        f.position_pct,
        f.total_score,
        f.intelligence_score,

        r.return_5d,
        r.return_10d,
        r.return_20d

    FROM factor_history f

    JOIN forward_returns r

        ON date(f.trade_date) = date(r.trade_date)
       AND f.symbol = r.symbol
    """

    df = pd.read_sql(query, conn)

    conn.close()

    print("\n" + "=" * 70)
    print("FACTOR CORRELATION REPORT")
    print("=" * 70)

    factors = [
        "change_pct",
        "sector_strength",
        "position_pct",
        "total_score",
        "intelligence_score"
    ]

    targets = [
        "return_5d",
        "return_10d",
        "return_20d"
    ]

    for factor in factors:

        print("\n" + "-" * 70)
        print(f"FACTOR: {factor}")
        print("-" * 70)

        for target in targets:

            corr = df[factor].corr(df[target])

            print(
                f"{target:<12}: {corr:.4f}"
            )

    print("\n" + "=" * 70)


if __name__ == "__main__":

    factor_correlation()