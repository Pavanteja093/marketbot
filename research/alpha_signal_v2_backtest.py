import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(str(DB_PATH))

query = """
SELECT

    f.index_name AS symbol,
    f.position_52w,
    f.index_name AS symbol,
    f.volume_expansion,

    h.sector_strength,

    r.return_20d

FROM factor_library f

JOIN factor_history h

  ON date(f.trade_date)=date(h.trade_date)
 AND f.index_name=h.symbol

JOIN forward_returns r

  ON date(f.trade_date)=date(r.trade_date)
 AND f.index_name=r.symbol

WHERE r.return_20d IS NOT NULL
"""

df = pd.read_sql(query, conn)

conn.close()

vol80 = df["volume_expansion"].quantile(0.80)

low20 = df["position_52w"].quantile(0.20)

sector80 = df["sector_strength"].quantile(0.80)

signals = df[
    (df["volume_expansion"] >= vol80)
    &
    (df["position_52w"] <= low20)
    &
    (df["sector_strength"] >= sector80)
]

print("\nSIGNALS:", len(signals))

print(
    "WIN RATE:",
    round(
        (signals["return_20d"] > 0).mean() * 100,
        2
    )
)

print(
    "AVG RETURN:",
    round(
        signals["return_20d"].mean(),
        2
    )
)

print(
    "MEDIAN RETURN:",
    round(
        signals["return_20d"].median(),
        2
    )
)

print(
    "BEST:",
    round(
        signals["return_20d"].max(),
        2
    )
)

print(
    "WORST:",
    round(
        signals["return_20d"].min(),
        2
    )
)