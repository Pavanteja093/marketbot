import sqlite3
from pathlib import Path

from analytics.oi_engine import calculate_oi_levels


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

EXPECTED_SYMBOLS = {
    "BANKNIFTY",
    "FINNIFTY",
    "NIFTY",
    "SENSEX",
}


def main():

    print()
    print("=" * 68)
    print("MARKETBOT — OI ENGINE REGRESSION TEST")
    print("=" * 68)

    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT *
        FROM option_chain_history o
        WHERE trade_time = (
            SELECT MAX(trade_time)
            FROM option_chain_history
            WHERE symbol = o.symbol
        )
    """

    import pandas as pd

    df = pd.read_sql(query, conn)
    conn.close()

    failures = []

    symbols = set(df["symbol"].dropna().unique())

    missing = EXPECTED_SYMBOLS - symbols

    if missing:
        failures.append(
            f"Missing expected symbols: {sorted(missing)}"
        )

    for symbol in sorted(EXPECTED_SYMBOLS & symbols):

        temp = df[df["symbol"] == symbol]

        try:
            result = calculate_oi_levels(temp)

            spot = result["spot_price"]
            support = result["support"]
            resistance = result["resistance"]

            if support > spot:
                failures.append(
                    f"{symbol}: support {support} > spot {spot}"
                )

            if resistance < spot:
                failures.append(
                    f"{symbol}: resistance {resistance} < spot {spot}"
                )

            if result["range_width"] < 0:
                failures.append(
                    f"{symbol}: negative range width"
                )

            if support <= spot <= resistance:
                print(
                    f"PASS  {symbol:<10} "
                    f"support={support:g} "
                    f"spot={spot:.2f} "
                    f"resistance={resistance:g}"
                )

        except Exception as exc:

            failures.append(
                f"{symbol}: {type(exc).__name__}: {exc}"
            )

    print()
    print("=" * 68)
    print("OI REGRESSION SUMMARY")
    print("=" * 68)

    if failures:

        print("STATUS : FAIL")

        for failure in failures:
            print("FAIL   :", failure)

        raise SystemExit(1)

    print(
        f"PASS   : {len(EXPECTED_SYMBOLS)} / "
        f"{len(EXPECTED_SYMBOLS)}"
    )
    print("STATUS : PASS")
    print("OI ENGINE REGRESSION CONTRACT IS STABLE")


if __name__ == "__main__":
    main()
