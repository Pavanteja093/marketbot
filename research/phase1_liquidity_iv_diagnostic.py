import sqlite3
from pathlib import Path
from statistics import median

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"
SYMBOLS = ["SENSEX", "NIFTY", "BANKNIFTY", "FINNIFTY"]

def audit(symbol):
    conn = sqlite3.connect(DB_PATH)
    latest = conn.execute("SELECT MAX(trade_time) FROM option_chain_history WHERE symbol=?", (symbol,)).fetchone()[0]
    rows = conn.execute('''SELECT strike,spot_price,call_iv,put_iv,call_oi,put_oi,call_volume,put_volume,call_ltp,put_ltp
                           FROM option_chain_history WHERE symbol=? AND trade_time=? ORDER BY strike''', (symbol, latest)).fetchall()
    conn.close()
    if not rows:
        print(symbol, "NO DATA"); return
    spot = float(rows[0][1])
    strikes = sorted(set(float(r[0]) for r in rows))
    atm = min(strikes, key=lambda x: abs(x-spot))
    atm20 = sorted(strikes, key=lambda x: abs(x-atm))[:41]
    data = [r for r in rows if float(r[0]) in atm20]
    oi = [float((r[4] or 0)+(r[5] or 0)) for r in data]
    vol = [float((r[6] or 0)+(r[7] or 0)) for r in data]
    print("\n"+"="*78); print(symbol); print("="*78)
    print(f"Snapshot : {latest}\nSpot     : {spot:.2f}\nATM      : {atm:.2f}\nATM ±20  : {len(data)}")
    print(f"Total OI  : min={min(oi):.0f} median={median(oi):.0f} max={max(oi):.0f}")
    print(f"Total Vol : min={min(vol):.0f} median={median(vol):.0f} max={max(vol):.0f}")
    print("\nTop IV outliers:")
    outliers=[]
    for r in data:
        civ=float(r[2]) if r[2] is not None and float(r[2])>0 else 0
        piv=float(r[3]) if r[3] is not None and float(r[3])>0 else 0
        outliers.append((max(civ,piv),float(r[0]),civ,piv,float(r[4] or 0)+float(r[5] or 0),float(r[6] or 0)+float(r[7] or 0),float(r[8] or 0),float(r[9] or 0)))
    for x in sorted(outliers, reverse=True)[:10]:
        print(f"strike={x[1]:.2f} call_iv={x[2]:.2f} put_iv={x[3]:.2f} OI={x[4]:.0f} volume={x[5]:.0f} call_ltp={x[6]:.2f} put_ltp={x[7]:.2f}")
    print(f"Zero total OI : {sum(x==0 for x in oi)}/{len(data)}")
    print(f"Zero total Vol: {sum(x==0 for x in vol)}/{len(data)}")

if __name__ == "__main__":
    print("="*78); print("MARKETBOT — PHASE 1 LIQUIDITY / IV DIAGNOSTIC"); print("="*78)
    for s in SYMBOLS: audit(s)
