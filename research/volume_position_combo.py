import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(str(DB_PATH))

query = """
SELECT

    f.index_name AS symbol,
    f.position_52w,
    f.index_name AS symbol,
    f.volume_expansion,

    r.return_20d

FROM factor_library f

JOIN forward_returns r

ON date(f.trade_date)=date(r.trade_date)
AND f.index_name=r.symbol

WHERE r.return_20d IS NOT NULL
"""

df = pd.read_sql(query, conn)

conn.close()

high_volume = (
    df["volume_expansion"]
    > df["volume_expansion"].quantile(0.8)
)

near_lows = (
    df["position_52w"]
    < df["position_52w"].quantile(0.2)
)

combo = df[
    high_volume &
    near_lows
]

print("\nRows:", len(combo))

print(
    "\nAverage 20D Return:",
    round(
        combo["return_20d"].mean(),
        3
    )
)