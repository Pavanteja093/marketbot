import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(str(DB_PATH))

query = """
SELECT

    f.volume_expansion,
    r.return_20d

FROM factor_library f

JOIN forward_returns r

ON date(f.trade_date)=date(r.trade_date)
AND f.symbol=r.symbol

WHERE r.return_20d IS NOT NULL
"""

df = pd.read_sql(query, conn)

conn.close()

df["bucket"] = pd.qcut(
    df["volume_expansion"],
    q=10,
    duplicates="drop"
)

result = (
    df.groupby("bucket")["return_20d"]
    .mean()
    .round(3)
)

print(result)