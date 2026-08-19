import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import upstox_client

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from config.upstox_config import ACCESS_TOKEN


DB_PATH = BASE_DIR / "market_intelligence.db"

IST = ZoneInfo("Asia/Kolkata")


# ============================================================
# UPSTOX CLIENT
# ============================================================

configuration = upstox_client.Configuration()
configuration.access_token = ACCESS_TOKEN

client = upstox_client.ApiClient(configuration)

options_api = upstox_client.OptionsApi(client)


# ============================================================
# EXPIRY
# ============================================================

def get_nearest_expiry(instrument_key):

    contracts = options_api.get_option_contracts(
        instrument_key
    )

    today = datetime.now(IST).date()

    expiries = sorted({
        c.expiry.date()
        for c in contracts.data
        if c.expiry.date() >= today
    })

    if not expiries:
        raise RuntimeError(
            f"No valid future expiry found for {instrument_key}"
        )

    return expiries[0].isoformat()


# ============================================================
# OPTION CHAIN STORAGE
# ============================================================

def save_option_chain(symbol, instrument_key, expiry):

    print(f"\nDownloading {symbol}...")
    print(f"Expiry: {expiry}")

    result = options_api.get_put_call_option_chain(
        instrument_key,
        expiry
    )

    if not result.data:
        raise RuntimeError(
            f"Upstox returned no option-chain data for "
            f"{symbol} / {expiry}"
        )

    print(
        f"Upstox returned {len(result.data)} option records."
    )

    # One timestamp for the complete snapshot
    trade_time = datetime.now(IST).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    rows_inserted = 0
    rows_skipped = 0

    for item in result.data:

        try:

            call_market = item.call_options.market_data
            put_market = item.put_options.market_data

            call_greeks = item.call_options.option_greeks
            put_greeks = item.put_options.option_greeks

            # ------------------------------------------------
            # Greeks
            # ------------------------------------------------

            call_iv = (
                call_greeks.iv
                if call_greeks
                else None
            )

            put_iv = (
                put_greeks.iv
                if put_greeks
                else None
            )

            call_delta = (
                call_greeks.delta
                if call_greeks
                else None
            )

            put_delta = (
                put_greeks.delta
                if put_greeks
                else None
            )

            call_gamma = (
                call_greeks.gamma
                if call_greeks
                else None
            )

            put_gamma = (
                put_greeks.gamma
                if put_greeks
                else None
            )

            call_theta = (
                call_greeks.theta
                if call_greeks
                else None
            )

            put_theta = (
                put_greeks.theta
                if put_greeks
                else None
            )

            call_vega = (
                call_greeks.vega
                if call_greeks
                else None
            )

            put_vega = (
                put_greeks.vega
                if put_greeks
                else None
            )

            call_pop = (
                call_greeks.pop
                if call_greeks
                else None
            )

            put_pop = (
                put_greeks.pop
                if put_greeks
                else None
            )

            # ------------------------------------------------
            # Market data
            # ------------------------------------------------

            call_oi = call_market.oi or 0
            put_oi = put_market.oi or 0

            previous_call_oi = (
                call_market.prev_oi or 0
            )

            previous_put_oi = (
                put_market.prev_oi or 0
            )

            call_change_oi = (
                call_oi - previous_call_oi
            )

            put_change_oi = (
                put_oi - previous_put_oi
            )

            call_volume = call_market.volume or 0
            put_volume = put_market.volume or 0

            call_ltp = call_market.ltp
            put_ltp = put_market.ltp

            pcr = item.pcr or 0

            spot_price = item.underlying_spot_price

            strike = item.strike_price

            # ------------------------------------------------
            # Raw storage
            # ------------------------------------------------

            cursor.execute(
                """
                INSERT INTO option_chain_history (

                    trade_time,
                    symbol,
                    expiry,
                    strike,

                    call_ltp,
                    put_ltp,

                    call_oi,
                    put_oi,

                    call_change_oi,
                    put_change_oi,

                    call_volume,
                    put_volume,

                    pcr,
                    spot_price,

                    call_iv,
                    put_iv,

                    call_delta,
                    put_delta,

                    call_gamma,
                    put_gamma,

                    call_theta,
                    put_theta,

                    call_vega,
                    put_vega,

                    call_pop,
                    put_pop

                )

                VALUES (
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?
                )
                """,
                (

                    trade_time,
                    symbol,
                    str(item.expiry.date()),
                    strike,

                    call_ltp,
                    put_ltp,

                    call_oi,
                    put_oi,

                    call_change_oi,
                    put_change_oi,

                    call_volume,
                    put_volume,

                    pcr,
                    spot_price,

                    call_iv,
                    put_iv,

                    call_delta,
                    put_delta,

                    call_gamma,
                    put_gamma,

                    call_theta,
                    put_theta,

                    call_vega,
                    put_vega,

                    call_pop,
                    put_pop
                )
            )

            rows_inserted += 1

        except Exception as e:

            rows_skipped += 1

            print(
                f"Skipped strike "
                f"{getattr(item, 'strike_price', 'UNKNOWN')}: "
                f"{e}"
            )

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print(f"{symbol} OPTION CHAIN COMPLETE")
    print("=" * 60)
    print(f"Expiry         : {expiry}")
    print(f"Rows received  : {len(result.data)}")
    print(f"Rows inserted  : {rows_inserted}")
    print(f"Rows skipped   : {rows_skipped}")
    print(f"Snapshot time  : {trade_time}")
    print("=" * 60)

    return {
        "symbol": symbol,
        "expiry": expiry,
        "rows_received": len(result.data),
        "rows_inserted": rows_inserted,
        "rows_skipped": rows_skipped,
        "trade_time": trade_time
    }


# ============================================================
# MAIN COLLECTOR
# ============================================================

def collect_all_indices():

    indices = [

        ("SENSEX", "BSE_INDEX|SENSEX"),

        ("NIFTY", "NSE_INDEX|Nifty 50"),

        ("BANKNIFTY", "NSE_INDEX|Nifty Bank"),

        ("FINNIFTY", "NSE_INDEX|Nifty Fin Service")

    ]

    results = []

    for symbol, instrument_key in indices:

        try:

            expiry = get_nearest_expiry(
                instrument_key
            )

            print(
                f"\n{symbol} Nearest Valid Expiry: "
                f"{expiry}"
            )

            result = save_option_chain(
                symbol=symbol,
                instrument_key=instrument_key,
                expiry=expiry
            )

            results.append(result)

        except Exception as e:

            print(
                f"\n{symbol} COLLECTION FAILED: {e}"
            )

            results.append({
                "symbol": symbol,
                "error": str(e)
            })

    print("\n" + "=" * 70)
    print("OPTION CHAIN COLLECTION SUMMARY")
    print("=" * 70)

    for result in results:

        print(result)

    print("=" * 70)

    return results


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    import traceback

    try:

        collect_all_indices()

    except Exception:

        print("\nCOLLECTION FAILED")

        traceback.print_exc()

    finally:

        try:
            client.close()

        except Exception:
            pass
