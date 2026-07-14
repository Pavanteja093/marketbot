import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def factor_discovery():

    conn = sqlite3.connect(str(DB_PATH))

    query = """
    SELECT

        f.position_52w,
        f.breakout_distance,
        f.volume_expansion,

        r.return_5d,
        r.return_10d,
        r.return_20d

    FROM factor_library f

    JOIN forward_returns r

        ON date(f.trade_date) = date(r.trade_date)
       AND f.symbol = r.symbol

    WHERE r.return_5d IS NOT NULL
    """

    df = pd.read_sql(query, conn)

    conn.close()

    print("\n" + "=" * 70)
    print("FACTOR DISCOVERY REPORT")
    print("=" * 70)

    factors = [
        "position_52w",
        "breakout_distance",
        "volume_expansion"
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

    factor_discovery()