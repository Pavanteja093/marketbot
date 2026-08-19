import time
import sqlite3

from datetime import datetime
from zoneinfo import ZoneInfo

from data_collectors.option_chain_upstox import collect_all_indices

DB_PATH = r"C:\Users\pavan\Documents\Python\Marketbot\market_intelligence.db"

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
        rows_inserted,
        last_error,
        status
    )
    VALUES
    (
        'option_chain_collector',
        CURRENT_TIMESTAMP,
        NULL,
        ?,
        ?
    )
    """, (
        error,
        status
    ))

    conn.commit()

    conn.close()

IST = ZoneInfo("Asia/Kolkata")

MARKET_OPEN = (9, 15)
MARKET_CLOSE = (15, 30)

print("LIVE COLLECTOR STARTED")


def market_is_open():

    now = datetime.now(IST)

    # Saturday=5 Sunday=6
    if now.weekday() >= 5:
        return False

    current_minutes = now.hour * 60 + now.minute

    open_minutes = MARKET_OPEN[0] * 60 + MARKET_OPEN[1]
    close_minutes = MARKET_CLOSE[0] * 60 + MARKET_CLOSE[1]

    return open_minutes <= current_minutes <= close_minutes



while True:

    now = datetime.now(IST)

    print(
        f"\n[{now.strftime('%d-%m-%Y %H:%M:%S')}]"
    )

    if not market_is_open():

        print("Market Closed")

        # Check again in 5 minutes
        time.sleep(300)

        continue

    try:

        print("=" * 60)

        collect_all_indices()

        update_system_status(status= "OK")

        print("Collection Successful")

    except Exception as e:

        print("COLLECTION FAILED")
        print(str(e))

        update_system_status(
            status="FAILED",
            error=str(e)
        )

    print("\nSleeping 60 seconds...\n")

    time.sleep(60)
