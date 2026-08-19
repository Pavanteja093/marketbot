import sqlite3
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "market_intelligence.db"

EXPECTED = ["BANKNIFTY", "FINNIFTY", "NIFTY", "SENSEX"]

print()
print("=" * 68)
print("MARKETBOT — OI CALCULATION CONTRACT AUDIT")
print("=" * 68)

conn = sqlite3.connect(DB_PATH)

# ------------------------------------------------------------
# Latest snapshot per symbol
# ------------------------------------------------------------

query = """
SELECT symbol, MAX(trade_time) AS latest_time
FROM option_chain_history
GROUP BY symbol
"""

latest = pd.read_sql(query, conn)

print()
print("LATEST SNAPSHOTS")
print("-" * 68)

for _, row in latest.iterrows():
    print(f"{row['symbol']:12} {row['latest_time']}")

# ------------------------------------------------------------
# Independent OI calculation
# ------------------------------------------------------------

failures = []
passes = []

print()
print("=" * 68)
print("INDEPENDENT SUPPORT / RESISTANCE CONTRACT")
print("=" * 68)

for symbol in EXPECTED:

    latest_time_row = latest[latest["symbol"] == symbol]

    if latest_time_row.empty:
        failures.append(f"{symbol}: no snapshot")
        continue

    latest_time = latest_time_row.iloc[0]["latest_time"]

    df = pd.read_sql(
        """
        SELECT
            symbol,
            strike,
            call_oi,
            put_oi,
            spot_price
        FROM option_chain_history
        WHERE symbol = ?
          AND trade_time = ?
        ORDER BY strike
        """,
        conn,
        params=(symbol, latest_time),
    )

    if df.empty:
        failures.append(f"{symbol}: empty latest snapshot")
        continue

    df["strike"] = pd.to_numeric(
        df["strike"],
        errors="coerce",
    )

    df["call_oi"] = pd.to_numeric(
        df["call_oi"],
        errors="coerce",
    )

    df["put_oi"] = pd.to_numeric(
        df["put_oi"],
        errors="coerce",
    )

    df["spot_price"] = pd.to_numeric(
        df["spot_price"],
        errors="coerce",
    )

    df = df.dropna(
        subset=[
            "strike",
            "call_oi",
            "put_oi",
            "spot_price",
        ]
    )

    spot = float(df["spot_price"].iloc[0])

    # Create the two candidate sets.
    below = df[df["strike"] <= spot].copy()
    above = df[df["strike"] >= spot].copy()

    if below.empty:
        failures.append(
            f"{symbol}: no support strike at or below spot"
        )
        continue

    if above.empty:
        failures.append(
            f"{symbol}: no resistance strike at or above spot"
        )
        continue

    below["strike"] = pd.to_numeric(below["strike"], errors="coerce")
    below["put_oi"] = pd.to_numeric(below["put_oi"], errors="coerce")

    above["strike"] = pd.to_numeric(above["strike"], errors="coerce")
    above["call_oi"] = pd.to_numeric(above["call_oi"], errors="coerce")

    # Nearest strike on each side of spot.
    nearest_support = float(
        pd.to_numeric(
            below.loc[
                (spot - below["strike"]).abs().idxmin(),
                "strike"
            ],
            errors="coerce",
        )
    )

    nearest_resistance = float(
        pd.to_numeric(
            above.loc[
                (above["strike"] - spot).abs().idxmin(),
                "strike"
            ],
            errors="coerce",
        )
    )

    # OI-based candidates.
    support_idx = below["put_oi"].idxmax()
    resistance_idx = above["call_oi"].idxmax()

    oi_support = float(
        pd.to_numeric(
            below.at[support_idx, "strike"],
            errors="coerce",
        )
    )

    oi_resistance = float(
        pd.to_numeric(
            above.at[resistance_idx, "strike"],
            errors="coerce",
        )
    )

    oi_support_put_oi = float(
        pd.to_numeric(
            below.at[support_idx, "put_oi"],
            errors="coerce",
        )
    )

    oi_resistance_call_oi = float(
        pd.to_numeric(
            above.at[resistance_idx, "call_oi"],
            errors="coerce",
        )
    )

    print()
    print(symbol)
    print("-" * 68)
    print(f"Spot                    : {spot:.2f}")

    print(
        f"Nearest support        : {nearest_support:g}"
    )
    print(
        f"Nearest resistance     : {nearest_resistance:g}"
    )

    print(
        f"Put-OI support         : {oi_support:g}"
    )
    print(
        f"Call-OI resistance     : {oi_resistance:g}"
    )
    
    print(
        f"Put OI                : {oi_support_put_oi:g}"
    )

    print(
        f"Call OI               : {oi_resistance_call_oi:g}"
    )

    # Contract checks.
    support_ok = oi_support <= spot
    resistance_ok = oi_resistance >= spot

    if support_ok:
        print("PASS  SUPPORT SIDE")
        passes.append(f"{symbol}: support")
    else:
        print(
            f"FAIL  SUPPORT SIDE: {oi_support:g} > spot {spot:.2f}"
        )
        failures.append(
            f"{symbol}: support {oi_support:g} above spot {spot:.2f}"
        )

    if resistance_ok:
        print("PASS  RESISTANCE SIDE")
        passes.append(f"{symbol}: resistance")
    else:
        print(
            f"FAIL  RESISTANCE SIDE: "
            f"{oi_resistance:g} < spot {spot:.2f}"
        )
        failures.append(
            f"{symbol}: resistance {oi_resistance:g} below spot {spot:.2f}"
        )

conn.close()

print()
print("=" * 68)
print("OI CALCULATION CONTRACT SUMMARY")
print("=" * 68)

print(f"PASS : {len(passes)}")
print(f"FAIL : {len(failures)}")

if failures:
    print()
    print("FAILURES")
    print("-" * 68)
    for item in failures:
        print("FAIL:", item)

    print()
    print("STATUS : FAIL")
    print("ACTION : OI ENGINE CALCULATION REQUIRES REPAIR")
else:
    print()
    print("STATUS : PASS")
    print("OI SUPPORT/RESISTANCE SIDE CONTRACT IS VALID")
