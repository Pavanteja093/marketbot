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

IST = ZoneInfo("Asia/kolkata")

configuration = upstox_client.Configuration()
configuration.access_token = ACCESS_TOKEN

client = upstox_client.ApiClient(configuration)

options_api = upstox_client.OptionsApi(client)

def get_nearest_expiry(instrument_key):

    contracts = options_api.get_option_contracts(
        instrument_key
    )

    expiries = sorted(
        list(set([
            str(c.expiry.date())
            for c in contracts.data
        ])) 
    )

    return expiries[0]


def save_option_chain(symbol, instrument_key, expiry):

    print(f"\nDownloading {symbol}...")

    result = options_api.get_put_call_option_chain(
        instrument_key,
        expiry
    )

    if len(result.data) > 0:

        print("\n" + "=" * 60)
        print("FIRST OPTION RECORD")
        print("=" * 60)

        print(result.data[0])

        print("=" * 60 + "\n")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    rows_inserted = 0

    for item in result.data:

        try:

            call_greeks = item.call_options.option_greeks
            put_greeks = item.put_options.option_greeks

            call_iv = call_greeks.iv if call_greeks else None
            put_iv = put_greeks.iv if put_greeks else None

            call_delta = call_greeks.delta if call_greeks else None
            put_delta = put_greeks.delta if put_greeks else None

            call_gamma = call_greeks.gamma if call_greeks else None
            put_gamma = put_greeks.gamma if put_greeks else None

            call_theta = call_greeks.theta if call_greeks else None
            put_theta = put_greeks.theta if put_greeks else None

            call_vega = call_greeks.vega if call_greeks else None
            put_vega = put_greeks.vega if put_greeks else None

            call_pop = call_greeks.pop if call_greeks else None
            put_pop = put_greeks.pop if put_greeks else None

            cursor.execute("""
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

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (

                datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),

                symbol,

                str(item.expiry.date()),

                item.strike_price,

                item.call_options.market_data.ltp,
                item.put_options.market_data.ltp,

                item.call_options.market_data.oi or 0,
                item.put_options.market_data.oi or 0,

            (
                (item.call_options.market_data.oi or 0)
                -
                (item.call_options.market_data.prev_oi or 0)
            ),

            (
                (item.put_options.market_data.oi or 0)
                -
                (item.put_options.market_data.prev_oi or 0)
                
            ),

                item.call_options.market_data.volume or 0,
                item.put_options.market_data.volume or 0,

                item.pcr if item.pcr else 0,

                item.underlying_spot_price,

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

            ))

            rows_inserted += 1

        except Exception as e:

            print("Skipped strike:", e)

    conn.commit()
    conn.close()

    print(f"{rows_inserted} rows inserted.")


# ============================================================
# MAIN COLLECTOR
# ============================================================

def collect_all_indices():

    INDICES = [

        ("NIFTY", "NSE_INDEX|Nifty 50"),

        ("BANKNIFTY", "NSE_INDEX|Nifty Bank"),

        ("FINNIFTY", "NSE_INDEX|Nifty Fin Service")

    ]

    for symbol, instrument_key in INDICES:

        expiry = get_nearest_expiry(instrument_key)

        print(
            f"\n{symbol} Nearest Expiry:",
            expiry
        )

        save_option_chain(
            symbol=symbol,
            instrument_key=instrument_key,
            expiry=expiry
        )
    update_system_status("OK")


def update_system_status(
        status,
        error=None
        ):

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR REPLACE INTO system_status
    (
        component,
        last_successful_write,
        status
    )
    VALUES
    (
        'option_chain_collector',
        ?,
        ?
    )
    """,(
        datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
        status
        ))

    conn.commit()
    conn.close()

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
        update_system_status("FAILED")

    finally:
        try:
            client.close()
        except Exception:
            pass


