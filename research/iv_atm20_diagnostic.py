import sqlite3
from pathlib import Path
import statistics

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

SYMBOLS = [
    "SENSEX",
    "NIFTY",
    "BANKNIFTY",
    "FINNIFTY",
]


def audit(symbol):

    conn = sqlite3.connect(DB_PATH)

    latest = conn.execute(
        """
        SELECT MAX(trade_time)
        FROM option_chain_history
        WHERE symbol = ?
        """,
        (symbol,),
    ).fetchone()[0]

    rows = conn.execute(
        """
        SELECT
            strike,
            spot_price,
            call_iv,
            put_iv,
            call_oi,
            put_oi,
            call_volume,
            put_volume
        FROM option_chain_history
        WHERE symbol = ?
          AND trade_time = ?
        ORDER BY strike
        """,
        (symbol, latest),
    ).fetchall()

    conn.close()

    if not rows:
        return

    spot = rows[0][1]

    strikes = sorted(set(r[0] for r in rows))

    atm = min(
        strikes,
        key=lambda x: abs(x - spot)
    )

    atm20_strikes = sorted(
        strikes,
        key=lambda x: abs(x - atm)
    )[:41]

    atm20 = [
        r for r in rows
        if r[0] in atm20_strikes
    ]

    def clean(values):
        return [
            float(v)
            for v in values
            if v is not None and float(v) > 0
        ]

    raw_call_iv = clean(r[2] for r in rows)
    raw_put_iv = clean(r[3] for r in rows)

    atm_call_iv = clean(r[2] for r in atm20)
    atm_put_iv = clean(r[3] for r in atm20)

    print("\n" + "=" * 70)
    print(symbol)
    print("=" * 70)

    print("Snapshot :", latest)
    print("Spot     :", spot)
    print("ATM      :", atm)
    print("ATM ±20  :", len(atm20))

    def stats(values):
        if not values:
            return "N/A"

        return (
            f"min={min(values):.2f} "
            f"max={max(values):.2f} "
            f"avg={statistics.mean(values):.2f}"
        )

    print("\nRAW CHAIN")

    print("Call IV:", stats(raw_call_iv))
    print("Put IV :", stats(raw_put_iv))

    print("\nATM ±20")

    print("Call IV:", stats(atm_call_iv))
    print("Put IV :", stats(atm_put_iv))


def main():

    print("=" * 80)
    print("MARKETBOT — RAW VS ATM ±20 IV DIAGNOSTIC")
    print("=" * 80)

    for symbol in SYMBOLS:
        audit(symbol)


if __name__ == "__main__":
    main()
