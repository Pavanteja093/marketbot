import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

SYMBOLS = [
    "SENSEX",
    "NIFTY",
    "BANKNIFTY",
    "FINNIFTY",
]


def get_latest_snapshot(conn, symbol):

    return conn.execute(
        """
        SELECT MAX(trade_time)
        FROM option_chain_history
        WHERE symbol = ?
        """,
        (symbol,),
    ).fetchone()[0]


def build_atm20(symbol):

    conn = sqlite3.connect(DB_PATH)

    trade_time = get_latest_snapshot(conn, symbol)

    if trade_time is None:
        conn.close()
        return []

    rows = conn.execute(
        """
        SELECT
            trade_time,
            symbol,
            expiry,
            strike,
            spot_price,
            call_ltp,
            put_ltp,
            call_oi,
            put_oi,
            call_change_oi,
            put_change_oi,
            call_volume,
            put_volume,
            pcr,
            call_iv,
            put_iv,
            call_delta,
            put_delta,
            call_gamma,
            put_gamma,
            call_theta,
            put_theta,
            call_vega,
            put_vega
        FROM option_chain_history
        WHERE symbol = ?
          AND trade_time = ?
        ORDER BY strike
        """,
        (symbol, trade_time),
    ).fetchall()

    if not rows:
        conn.close()
        return []

    # Spot is constant within a valid snapshot.
    spot = rows[0][4]

    # Find nearest available strike to spot.
    strikes = sorted(set(row[3] for row in rows))

    atm_index = min(
        range(len(strikes)),
        key=lambda i: abs(strikes[i] - spot)
    )

    lower = max(0, atm_index - 20)
    upper = min(len(strikes), atm_index + 21)

    selected_strikes = set(strikes[lower:upper])

    selected = [
        row for row in rows
        if row[3] in selected_strikes
    ]

    conn.close()

    return selected


def run():

    print("=" * 80)
    print("MARKETBOT — ATM ±20 DATASET AUDIT")
    print("=" * 80)

    for symbol in SYMBOLS:

        rows = build_atm20(symbol)

        print(f"\n{symbol}")

        if not rows:
            print("NO DATA")
            continue

        spot = rows[0][4]
        strikes = sorted(row[3] for row in rows)

        print("Snapshot :", rows[0][0])
        print("Expiry   :", rows[0][2])
        print("Spot     :", spot)
        print("Rows     :", len(rows))
        print("Strikes  :", len(strikes))
        print("Lowest   :", min(strikes))
        print("Highest  :", max(strikes))
        print("ATM      :", min(strikes, key=lambda x: abs(x - spot)))

        print("Strike list:")
        print(strikes)


if __name__ == "__main__":
    run()
