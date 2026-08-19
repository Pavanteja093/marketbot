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


OPTION_CHAIN_COLUMNS = (
    "trade_time",
    "symbol",
    "expiry",
    "strike",
    "call_ltp",
    "put_ltp",
    "call_oi",
    "put_oi",
    "call_change_oi",
    "put_change_oi",
    "call_volume",
    "put_volume",
    "pcr",
    "spot_price",
    "call_iv",
    "put_iv",
    "call_delta",
    "put_delta",
    "call_gamma",
    "put_gamma",
    "call_theta",
    "put_theta",
    "call_vega",
    "put_vega",
    "call_pop",
    "put_pop",
)

OPTION_CHAIN_PLACEHOLDERS = ", ".join("?" for _ in OPTION_CHAIN_COLUMNS)
OPTION_CHAIN_INSERT_SQL = f"""
INSERT INTO option_chain_history ({', '.join(OPTION_CHAIN_COLUMNS)})
VALUES ({OPTION_CHAIN_PLACEHOLDERS})
"""


def _greek(greeks, name):
    return getattr(greeks, name, None) if greeks is not None else None


def build_option_row(item, symbol, trade_time):
    """Build exactly one row matching OPTION_CHAIN_COLUMNS."""
    call_md = item.call_options.market_data
    put_md = item.put_options.market_data
    call_g = item.call_options.option_greeks
    put_g = item.put_options.option_greeks

    row = (
        trade_time,
        symbol,
        str(item.expiry.date()),
        item.strike_price,
        call_md.ltp,
        put_md.ltp,
        call_md.oi or 0,
        put_md.oi or 0,
        (call_md.oi or 0) - (call_md.prev_oi or 0),
        (put_md.oi or 0) - (put_md.prev_oi or 0),
        call_md.volume or 0,
        put_md.volume or 0,
        item.pcr if item.pcr is not None else 0,
        item.underlying_spot_price,
        _greek(call_g, "iv"),
        _greek(put_g, "iv"),
        _greek(call_g, "delta"),
        _greek(put_g, "delta"),
        _greek(call_g, "gamma"),
        _greek(put_g, "gamma"),
        _greek(call_g, "theta"),
        _greek(put_g, "theta"),
        _greek(call_g, "vega"),
        _greek(put_g, "vega"),
        _greek(call_g, "pop"),
        _greek(put_g, "pop"),
    )

    if len(row) != len(OPTION_CHAIN_COLUMNS):
        raise RuntimeError(
            f"Option-chain row contract mismatch: {len(row)} values for "
            f"{len(OPTION_CHAIN_COLUMNS)} columns"
        )

    return row


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
    rows_skipped = 0
    trade_time = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

    try:
        rows = []
        for item in result.data:
            try:
                rows.append(build_option_row(item, symbol, trade_time))
            except Exception as e:
                rows_skipped += 1
                print("Skipped strike:", e)

        if rows:
            cursor.executemany(OPTION_CHAIN_INSERT_SQL, rows)
            rows_inserted = len(rows)

        conn.commit()
    finally:
        conn.close()

    print(f"{symbol} option rows received : {len(result.data)}")
    print(f"{symbol} option rows inserted : {rows_inserted}")
    print(f"{symbol} option rows skipped  : {rows_skipped}")


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


