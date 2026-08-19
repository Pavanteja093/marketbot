import sqlite3
from pathlib import Path
from statistics import median, mean

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

SYMBOLS = ["SENSEX", "NIFTY", "BANKNIFTY", "FINNIFTY"]


def percentile(values, p):
    if not values:
        return 0.0

    values = sorted(values)

    k = (len(values) - 1) * p
    f = int(k)
    c = min(f + 1, len(values))

    if f == c:
        return values[f]

    return values[f] + (values[c] - values[f]) * (k - f)


def audit_symbol(conn, symbol):

    latest = conn.execute(
        """
        SELECT
            trade_time,
            expiry
        FROM option_chain_history
        WHERE symbol = ?
        ORDER BY trade_time DESC
        LIMIT 1
        """,
        (symbol,)
    ).fetchone()

    if not latest:
        print(f"\n{symbol}: NO SNAPSHOT")
        return []

    trade_time, expiry = latest

    rows = conn.execute(
        """
        SELECT
            strike,
            spot_price,
            call_ltp,
            put_ltp,
            call_oi,
            put_oi,
            call_volume,
            put_volume,
            call_iv,
            put_iv
        FROM option_chain_history
        WHERE symbol = ?
          AND trade_time = ?
          AND expiry = ?
        ORDER BY strike
        """,
        (symbol, trade_time, expiry)
    ).fetchall()

    if not rows:
        print(f"\n{symbol}: NO DATA")
        return []

    spot = float(rows[0][1])

    strikes = sorted(float(r[0]) for r in rows)

    atm = min(
        strikes,
        key=lambda x: abs(x - spot)
    )

    atm20 = sorted(
        strikes,
        key=lambda x: abs(x - atm)
    )[:41]

    atm20 = set(atm20)

    selected = [
        r for r in rows
        if float(r[0]) in atm20
    ]

    result = []

    for r in selected:

        (
            strike,
            spot_price,
            call_ltp,
            put_ltp,
            call_oi,
            put_oi,
            call_volume,
            put_volume,
            call_iv,
            put_iv
        ) = r

        call_ltp = float(call_ltp or 0)
        put_ltp = float(put_ltp or 0)

        call_oi = float(call_oi or 0)
        put_oi = float(put_oi or 0)

        call_volume = float(call_volume or 0)
        put_volume = float(put_volume or 0)

        call_iv = float(call_iv or 0)
        put_iv = float(put_iv or 0)

        total_oi = call_oi + put_oi
        total_volume = call_volume + put_volume

        valid_ltp = call_ltp > 0 and put_ltp > 0
        valid_iv = call_iv > 0 and put_iv > 0

        result.append({
            "symbol": symbol,
            "trade_time": trade_time,
            "expiry": expiry,
            "strike": float(strike),
            "spot": spot,
            "distance": abs(float(strike) - atm),
            "call_ltp": call_ltp,
            "put_ltp": put_ltp,
            "call_oi": call_oi,
            "put_oi": put_oi,
            "total_oi": total_oi,
            "call_volume": call_volume,
            "put_volume": put_volume,
            "total_volume": total_volume,
            "call_iv": call_iv,
            "put_iv": put_iv,
            "valid_ltp": valid_ltp,
            "valid_iv": valid_iv,
        })

    print("\n" + "=" * 78)
    print(symbol)
    print("=" * 78)

    print("Snapshot :", trade_time)
    print("Expiry   :", expiry)
    print(f"Spot     : {spot:.2f}")
    print(f"ATM      : {atm:.2f}")
    print("ATM ±20  :", len(result))

    oi = [x["total_oi"] for x in result]
    volume = [x["total_volume"] for x in result]

    oi_median = median(oi)
    volume_median = median(volume)

    oi_p25 = percentile(oi, 0.25)
    volume_p25 = percentile(volume, 0.25)

    print("\nLIQUIDITY DISTRIBUTION")
    print(f"Total OI     : min={min(oi):.0f} "
          f"p25={oi_p25:.0f} "
          f"median={oi_median:.0f} "
          f"p75={percentile(oi,0.75):.0f} "
          f"max={max(oi):.0f}")

    print(f"Total Volume : min={min(volume):.0f} "
          f"p25={volume_p25:.0f} "
          f"median={volume_median:.0f} "
          f"p75={percentile(volume,0.75):.0f} "
          f"max={max(volume):.0f}")

    valid_ltp = [x for x in result if x["valid_ltp"]]
    valid_iv = [x for x in result if x["valid_iv"]]

    print("\nDATA VALIDITY")
    print("Valid LTP pairs :", len(valid_ltp), "/", len(result))
    print("Valid IV pairs  :", len(valid_iv), "/", len(result))

    # Evidence-based diagnostic classifications.
    #
    # These are NOT production thresholds.
    # They intentionally use the snapshot's own median to expose
    # the liquidity structure before we establish a final filter.

    median_liquid = [
        x for x in result
        if x["valid_ltp"]
        and x["valid_iv"]
        and x["total_oi"] >= oi_median
        and x["total_volume"] >= volume_median
    ]

    print(
        "Above-median OI + volume + valid data:",
        len(median_liquid),
        "/",
        len(result)
    )

    # Show contracts with suspiciously high IV.
    suspicious = sorted(
        result,
        key=lambda x: max(x["call_iv"], x["put_iv"]),
        reverse=True
    )[:10]

    print("\nTOP 10 HIGHEST-IV CONTRACTS")
    print(
        "Strike      OI       Volume    Call IV    Put IV    "
        "Call LTP   Put LTP"
    )

    for x in suspicious:

        print(
            f"{x['strike']:8.0f} "
            f"{x['total_oi']:9.0f} "
            f"{x['total_volume']:9.0f} "
            f"{x['call_iv']:9.2f} "
            f"{x['put_iv']:9.2f} "
            f"{x['call_ltp']:9.2f} "
            f"{x['put_ltp']:9.2f}"
        )

    # Show lowest-liquidity contracts.
    lowest = sorted(
        result,
        key=lambda x: (x["total_volume"], x["total_oi"])
    )[:10]

    print("\n10 LOWEST-LIQUIDITY CONTRACTS")
    print(
        "Strike      OI       Volume    Call IV    Put IV    "
        "Call LTP   Put LTP"
    )

    for x in lowest:

        print(
            f"{x['strike']:8.0f} "
            f"{x['total_oi']:9.0f} "
            f"{x['total_volume']:9.0f} "
            f"{x['call_iv']:9.2f} "
            f"{x['put_iv']:9.2f} "
            f"{x['call_ltp']:9.2f} "
            f"{x['put_ltp']:9.2f}"
        )

    return result


def create_audit_table(conn):

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS option_liquidity_audit (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            trade_time TEXT NOT NULL,
            symbol TEXT NOT NULL,
            expiry TEXT NOT NULL,

            strike REAL NOT NULL,
            spot_price REAL,

            distance_from_atm REAL,

            call_ltp REAL,
            put_ltp REAL,

            call_oi REAL,
            put_oi REAL,
            total_oi REAL,

            call_volume REAL,
            put_volume REAL,
            total_volume REAL,

            call_iv REAL,
            put_iv REAL,

            valid_ltp INTEGER,
            valid_iv INTEGER,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(
                symbol,
                expiry,
                trade_time,
                strike
            )
        )
        """
    )

    conn.commit()


def persist(conn, rows):

    for x in rows:

        conn.execute(
            """
            INSERT OR REPLACE INTO option_liquidity_audit
            (
                trade_time,
                symbol,
                expiry,
                strike,
                spot_price,
                distance_from_atm,
                call_ltp,
                put_ltp,
                call_oi,
                put_oi,
                total_oi,
                call_volume,
                put_volume,
                total_volume,
                call_iv,
                put_iv,
                valid_ltp,
                valid_iv
            )
            VALUES
            (
                ?,?,?,?,?,?,?,?,?,?,
                ?,?,?,?,?,?,?,?
            )
            """,
            (
                x["trade_time"],
                x["symbol"],
                x["expiry"],
                x["strike"],
                x["spot"],
                x["distance"],
                x["call_ltp"],
                x["put_ltp"],
                x["call_oi"],
                x["put_oi"],
                x["total_oi"],
                x["call_volume"],
                x["put_volume"],
                x["total_volume"],
                x["call_iv"],
                x["put_iv"],
                int(x["valid_ltp"]),
                int(x["valid_iv"])
            )
        )

    conn.commit()


def main():

    print("=" * 80)
    print("MARKETBOT — ATM ±20 LIQUIDITY ANALYSIS")
    print("=" * 80)

    conn = sqlite3.connect(DB_PATH)

    create_audit_table(conn)

    all_rows = []

    for symbol in SYMBOLS:

        rows = audit_symbol(conn, symbol)
        all_rows.extend(rows)

    persist(conn, all_rows)

    print("\n" + "=" * 80)
    print("LIQUIDITY AUDIT STORAGE")
    print("=" * 80)

    count = conn.execute(
        """
        SELECT COUNT(*)
        FROM option_liquidity_audit
        """
    ).fetchone()[0]

    snapshots = conn.execute(
        """
        SELECT COUNT(DISTINCT symbol || '|' || expiry || '|' || trade_time)
        FROM option_liquidity_audit
        """
    ).fetchone()[0]

    print("Audit rows      :", count)
    print("Snapshots stored:", snapshots)

    conn.close()

    print("\nAUDIT COMPLETE")


if __name__ == "__main__":
    main()
