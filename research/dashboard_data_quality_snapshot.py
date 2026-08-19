import sqlite3
from pathlib import Path
BASE_DIR=Path(__file__).resolve().parent.parent
DB_PATH=BASE_DIR/"market_intelligence.db"
conn=sqlite3.connect(DB_PATH)
print("="*78); print("MARKETBOT — DASHBOARD DATA QUALITY SNAPSHOT"); print("="*78)
tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
for name,q in [("option_chain_history","SELECT COUNT(*) FROM option_chain_history"),("market_features","SELECT COUNT(*) FROM market_features"),("signal_performance","SELECT COUNT(*) FROM signal_performance"),("daily_recommendations","SELECT COUNT(*) FROM daily_recommendations"),("trade_performance","SELECT COUNT(*) FROM trade_performance")]:
    print(f"{name:24}: {conn.execute(q).fetchone()[0] if name in tables else 'TABLE MISSING'}")
if "market_features" in tables:
    print("\nLatest MarketBrain states:")
    for r in conn.execute("SELECT symbol,trade_time,spot_price,avg_iv,iv_regime,market_bias,confidence,strategy FROM market_features ORDER BY trade_time DESC LIMIT 4"): print(r)
print("\nLatest option snapshots:")
for r in conn.execute("SELECT symbol,expiry,trade_time,COUNT(*) FROM option_chain_history GROUP BY symbol,expiry,trade_time ORDER BY trade_time DESC LIMIT 4"): print(r)
conn.close()
