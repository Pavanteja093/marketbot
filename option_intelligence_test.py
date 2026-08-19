import sqlite3
import importlib
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
DB = ROOT / "market_intelligence.db"

PASS = 0
FAIL = 0
WARN = 0


def ok(name, detail=""):
    global PASS
    PASS += 1
    print(f"PASS  {name}")
    if detail:
        print(f"      {detail}")


def fail(name, detail=""):
    global FAIL
    FAIL += 1
    print(f"FAIL  {name}")
    if detail:
        print(f"      {detail}")


def warn(name, detail=""):
    global WARN
    WARN += 1
    print(f"WARN  {name}")
    if detail:
        print(f"      {detail}")


print("=" * 70)
print("MARKETBOT — OPTION INTELLIGENCE SEMANTIC TEST")
print("=" * 70)

EXPECTED_SYMBOLS = {
    "BANKNIFTY",
    "FINNIFTY",
    "NIFTY",
    "SENSEX",
}

# ============================================================
# DATABASE
# ============================================================

try:
    conn = sqlite3.connect(DB)

    # Get the latest snapshot independently for EACH symbol.
    df = pd.read_sql_query(
        """
        SELECT o.*
        FROM option_chain_history o
        INNER JOIN (
            SELECT symbol, MAX(trade_time) AS latest_trade_time
            FROM option_chain_history
            GROUP BY symbol
        ) latest
        ON o.symbol = latest.symbol
        AND o.trade_time = latest.latest_trade_time
        """,
        conn,
    )

    conn.close()

    required = {
        "symbol",
        "expiry",
        "strike",
        "call_oi",
        "put_oi",
        "spot_price",
        "call_iv",
        "put_iv",
    }

    missing = required - set(df.columns)

    if missing:
        fail(
            "OPTION DATABASE SCHEMA",
            f"Missing columns: {sorted(missing)}"
        )
    else:
        ok(
            "OPTION DATABASE SCHEMA",
            f"{len(required)} required fields present"
        )

except Exception as e:
    fail(
        "OPTION DATABASE ACCESS",
        f"{type(e).__name__}: {e}"
    )
    df = pd.DataFrame()


# ============================================================
# SYMBOL COVERAGE
# ============================================================

if not df.empty:

    symbols = set(df["symbol"].dropna().unique())

    missing_symbols = EXPECTED_SYMBOLS - symbols
    unexpected_symbols = symbols - EXPECTED_SYMBOLS

    if missing_symbols:
        fail(
            "OPTION SYMBOL COVERAGE",
            f"Missing: {sorted(missing_symbols)}"
        )
    else:
        detail = f"All {len(EXPECTED_SYMBOLS)} expected symbols present"

        if unexpected_symbols:
            detail += f"; unexpected: {sorted(unexpected_symbols)}"

        ok("OPTION SYMBOL COVERAGE", detail)


# ============================================================
# FRESH SNAPSHOT CHECK
# ============================================================

if not df.empty:

    freshness = (
        df.groupby("symbol")["trade_time"]
        .first()
        .to_dict()
    )

    missing_freshness = EXPECTED_SYMBOLS - set(freshness)

    if missing_freshness:
        fail(
            "LATEST SNAPSHOT COVERAGE",
            f"No latest snapshot for: {sorted(missing_freshness)}"
        )
    else:
        ok(
            "LATEST SNAPSHOT COVERAGE",
            "Fresh snapshot found for all 4 indices"
        )


# ============================================================
# NUMERIC VALIDATION
# ============================================================

if not df.empty:

    numeric_columns = [
        "strike",
        "call_oi",
        "put_oi",
        "spot_price",
        "call_iv",
        "put_iv",
    ]

    bad_numeric = [
        col
        for col in numeric_columns
        if not pd.api.types.is_numeric_dtype(df[col])
    ]

    if bad_numeric:
        fail(
            "OPTION NUMERIC TYPES",
            f"Non-numeric: {bad_numeric}"
        )
    else:
        ok(
            "OPTION NUMERIC TYPES",
            "All required numeric fields valid"
        )


# ============================================================
# NULL VALIDATION
# ============================================================

if not df.empty:

    required_runtime = [
        "symbol",
        "strike",
        "call_oi",
        "put_oi",
        "spot_price",
    ]

    null_counts = {
        col: int(df[col].isna().sum())
        for col in required_runtime
        if df[col].isna().any()
    }

    if null_counts:
        fail(
            "OPTION REQUIRED VALUES",
            f"Null counts: {null_counts}"
        )
    else:
        ok(
            "OPTION REQUIRED VALUES",
            "No nulls in required runtime fields"
        )


# ============================================================
# OI INVARIANT
# ============================================================

if not df.empty:

    negative_oi = (
        (df["call_oi"] < 0).sum()
        +
        (df["put_oi"] < 0).sum()
    )

    if negative_oi:
        fail(
            "OI NON-NEGATIVE",
            f"{negative_oi} negative OI values"
        )
    else:
        ok("OI NON-NEGATIVE")


# ============================================================
# PCR INVARIANT
# ============================================================

if not df.empty:

    if "pcr" not in df.columns:
        fail(
            "PCR VALIDITY",
            "PCR column missing"
        )
    else:

        negative_pcr = int(
            (df["pcr"].dropna() < 0).sum()
        )

        if negative_pcr:
            fail(
                "PCR VALIDITY",
                f"{negative_pcr} negative PCR values"
            )
        else:
            ok("PCR VALIDITY")


# ============================================================
# ENGINE IMPORTS
# ============================================================

modules = [
    "analytics.pcr_engine",
    "analytics.oi_engine",
    "analytics.max_pain_engine",
    "analytics.strategy_engine",
]

for module_name in modules:

    try:
        importlib.import_module(module_name)
        ok(f"IMPORT {module_name}")
    except Exception as e:
        fail(
            f"IMPORT {module_name}",
            f"{type(e).__name__}: {e}"
        )


# ============================================================
# FEATURE ENGINE CONTRACT
# ============================================================

try:

    from analytics.feature_engine import FeatureEngine

    engine = FeatureEngine()

    if callable(getattr(engine, "build_features", None)):
        ok(
            "FEATURE ENGINE CONTRACT",
            "FeatureEngine.build_features available"
        )
    else:
        fail(
            "FEATURE ENGINE CONTRACT",
            "FeatureEngine.build_features missing"
        )

except Exception as e:

    fail(
        "FEATURE ENGINE CONTRACT",
        f"{type(e).__name__}: {e}"
    )


# ============================================================
# DATASET-LEVEL OI STRUCTURE
# ============================================================

if not df.empty:

    for symbol in sorted(EXPECTED_SYMBOLS):

        temp = df[df["symbol"] == symbol].copy()

        if temp.empty:
            fail(
                f"OPTION DATA {symbol}",
                "No rows in latest snapshot"
            )
            continue

        spot_values = temp["spot_price"].dropna().unique()

        if len(spot_values) != 1:
            fail(
                f"OPTION DATA {symbol}",
                f"Expected one spot price, found {len(spot_values)}"
            )
            continue

        spot = float(spot_values[0])

        strikes = temp["strike"].dropna()

        if strikes.empty:
            fail(
                f"OPTION DATA {symbol}",
                "No strikes"
            )
            continue

        below_or_at = strikes[strikes <= spot]
        above_or_at = strikes[strikes >= spot]

        if below_or_at.empty:
            fail(
                f"STRIKE STRUCTURE {symbol}",
                f"No strike <= spot ({spot})"
            )
            continue

        if above_or_at.empty:
            fail(
                f"STRIKE STRUCTURE {symbol}",
                f"No strike >= spot ({spot})"
            )
            continue

        nearest_support = float(below_or_at.max())
        nearest_resistance = float(above_or_at.min())

        if nearest_support <= spot <= nearest_resistance:
            ok(
                f"STRIKE STRUCTURE {symbol}",
                f"spot={spot:.2f}, nearest_support={nearest_support:.0f}, nearest_resistance={nearest_resistance:.0f}"
            )
        else:
            fail(
                f"STRIKE STRUCTURE {symbol}",
                f"Spot {spot} outside nearest strike interval"
            )


# ============================================================
# FINAL
# ============================================================

print()
print("=" * 70)
print("OPTION INTELLIGENCE TEST SUMMARY")
print("=" * 70)

print(f"PASS : {PASS}")
print(f"WARN : {WARN}")
print(f"FAIL : {FAIL}")

if FAIL == 0:
    print()
    print("STATUS : PASS")
    print("OPTION INTELLIGENCE DATA CONTRACT IS STABLE")
else:
    print()
    print("STATUS : FAIL")
    print("ACTION : INVESTIGATE ONLY THE FAILED CONTRACTS ABOVE")

print("=" * 70)
