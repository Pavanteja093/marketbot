import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(str(DB_PATH))

query = """
SELECT

    f.position_52w,
    f.volume_expansion,

    r.return_20d

FROM factor_library f

JOIN forward_returns r

ON date(f.trade_date)=date(r.trade_date)
AND f.index_name=r.index_name

WHERE r.return_20d IS NOT NULL
"""

df = pd.read_sql(query, conn)

conn.close()

universe = df["return_20d"].mean()

high_volume = df[
    df["volume_expansion"]
    > df["volume_expansion"].quantile(0.8)
]

near_lows = df[
    df["position_52w"]
    < df["position_52w"].quantile(0.2)
]

combo = df[
    (df["volume_expansion"]
     > df["volume_expansion"].quantile(0.8))
    &
    (df["position_52w"]
     < df["position_52w"].quantile(0.2))
]

print("\nUNIVERSE")
print(round(universe,3))

print("\nHIGH VOLUME")
print(round(high_volume["return_20d"].mean(),3))

print("\nNEAR LOWS")
print(round(near_lows["return_20d"].mean(),3))

print("\nCOMBO")
print(round(combo["return_20d"].mean(),3))

print("\nCOMBO OBSERVATIONS")
print(len(combo))
