import math
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "market_intelligence.db"
EXPECTED = {"BANKNIFTY", "FINNIFTY", "NIFTY", "SENSEX"}

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        symbols = {r[0] for r in conn.execute("SELECT DISTINCT symbol FROM option_chain_history")}
        missing = EXPECTED - symbols
        if missing:
            raise AssertionError(f"Missing symbols: {sorted(missing)}")

        print("MARKETBOT — INDEPENDENT PCR CALCULATION CONTRACT")
        print("=" * 64)

        for symbol in sorted(EXPECTED):
            ts = conn.execute(
                "SELECT MAX(trade_time) FROM option_chain_history WHERE symbol=?",
                (symbol,),
            ).fetchone()[0]
            if not ts:
                raise AssertionError(f"{symbol}: no snapshot")

            call_oi, put_oi = conn.execute(
                """SELECT COALESCE(SUM(call_oi),0), COALESCE(SUM(put_oi),0)
                   FROM option_chain_history
                   WHERE symbol=? AND trade_time=?""",
                (symbol, ts),
            ).fetchone()

            if call_oi <= 0:
                raise AssertionError(f"{symbol}: call OI must be > 0")
            if put_oi < 0:
                raise AssertionError(f"{symbol}: put OI must be >= 0")

            pcr = put_oi / call_oi
            if not math.isfinite(pcr):
                raise AssertionError(f"{symbol}: PCR is not finite")

            print(f"PASS  {symbol:<10} call_oi={call_oi:,.0f} put_oi={put_oi:,.0f} PCR={pcr:.6f}")

        print("=" * 64)
        print("PASS : 4 / 4")
        print("STATUS : PASS")
        print("INDEPENDENT PCR CALCULATION CONTRACT IS VALID")
        return 0
    finally:
        conn.close()

if __name__ == "__main__":
    raise SystemExit(main())
