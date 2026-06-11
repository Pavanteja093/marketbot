import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(str(DB_PATH))

# ----------------------------------
# SIGNAL DATES
# ----------------------------------

dates = pd.read_sql(
    """
    SELECT DISTINCT trade_date
    FROM signal_history
    ORDER BY trade_date
    """,
    conn
)

print("\n" + "=" * 70)
print("SIGNAL ACCURACY ENGINE")
print("=" * 70)

if len(dates) < 2:

    print(
        "\nNot enough signal history yet."
    )

    print(
        "\nCurrent signal dates:"
    )

    print(
        dates.to_string(index=False)
    )

    print(
        "\nNeed at least 2 signal dates "
        "before accuracy can be calculated."
    )

    conn.close()
    exit()

# ----------------------------------
# FUTURE VERSION
# ----------------------------------

print(
    "\nSufficient history detected."
)

conn.close()