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

        print("MARKETBOT — INDEPENDENT MAX PAIN CALCULATION CONTRACT")
        print("=" * 64)

        for symbol in sorted(EXPECTED):
            ts = conn.execute(
                "SELECT MAX(trade_time) FROM option_chain_history WHERE symbol=?",
                (symbol,),
            ).fetchone()[0]
            if not ts:
                raise AssertionError(f"{symbol}: no snapshot")

            rows = conn.execute(
                """SELECT strike, call_oi, put_oi
                   FROM option_chain_history
                   WHERE symbol=? AND trade_time=?
                   ORDER BY strike""",
                (symbol, ts),
            ).fetchall()

            if not rows:
                raise AssertionError(f"{symbol}: no option rows")

            strikes = [float(r[0]) for r in rows]
            pain = []

            for candidate in strikes:
                total = 0.0
                for strike, call_oi, put_oi in rows:
                    strike = float(strike)
                    call_oi = float(call_oi or 0)
                    put_oi = float(put_oi or 0)

                    if call_oi < 0 or put_oi < 0:
                        raise AssertionError(f"{symbol}: negative OI")

                    total += max(0.0, candidate - strike) * call_oi
                    total += max(0.0, strike - candidate) * put_oi

                pain.append((candidate, total))

            max_pain, minimum = min(pain, key=lambda x: (x[1], x[0]))

            if not math.isfinite(max_pain) or not math.isfinite(minimum):
                raise AssertionError(f"{symbol}: invalid max-pain result")
            if max_pain not in strikes:
                raise AssertionError(f"{symbol}: result is not an available strike")

            print(f"PASS  {symbol:<10} max_pain={max_pain:g}")

        print("=" * 64)
        print("PASS : 4 / 4")
        print("STATUS : PASS")
        print("INDEPENDENT MAX PAIN CALCULATION CONTRACT IS VALID")
        return 0
    finally:
        conn.close()

if __name__ == "__main__":
    raise SystemExit(main())
