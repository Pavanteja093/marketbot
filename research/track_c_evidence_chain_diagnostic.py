import sqlite3
from pathlib import Path
import pandas as pd

DB = Path("market_intelligence.db")
ART = Path("research/artifacts")

print("=" * 80)
print("MARKETBOT — TRACK C EVIDENCE-CHAIN DIAGNOSTIC")
print("=" * 80)

# ---------------------------------------------------------------------
# 1. DATABASE TABLE INVENTORY
# ---------------------------------------------------------------------

print("\n[1] DATABASE TABLES")
print("-" * 80)

conn = sqlite3.connect(DB)

tables = pd.read_sql_query(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
    conn
)

for name in tables["name"]:
    print(name)

# ---------------------------------------------------------------------
# 2. FIND SCENARIO / WEAPON / OOS TABLES
# ---------------------------------------------------------------------

print("\n[2] RELEVANT TABLE SCHEMAS")
print("-" * 80)

names = tables["name"].tolist()

keywords = (
    "scenario",
    "weapon",
    "oos",
    "outcome",
    "prediction",
    "signal",
    "factor",
    "history"
)

relevant = [
    n for n in names
    if any(k in n.lower() for k in keywords)
]

for table in relevant:
    print(f"\nTABLE: {table}")

    try:
        schema = pd.read_sql_query(
            f'PRAGMA table_info("{table}")',
            conn
        )

        print(
            schema[["name", "type"]]
            .to_string(index=False)
        )

        try:
            count = pd.read_sql_query(
                f'SELECT COUNT(*) AS rows FROM "{table}"',
                conn
            ).iloc[0, 0]

            print("ROWS:", count)

        except Exception as e:
            print("ROW COUNT ERROR:", e)

    except Exception as e:
        print("SCHEMA ERROR:", e)

# ---------------------------------------------------------------------
# 3. SCENARIO HISTORY
# ---------------------------------------------------------------------

print("\n[3] SCENARIO HISTORY CANDIDATES")
print("-" * 80)

for table in relevant:
    if "scenario" in table.lower():

        try:
            df = pd.read_sql_query(
                f'SELECT * FROM "{table}" LIMIT 5',
                conn
            )

            print(f"\n{table}")
            print("columns:", list(df.columns))
            print(df.to_string(index=False))

        except Exception as e:
            print(table, "ERROR:", e)

# ---------------------------------------------------------------------
# 4. RESEARCH ARTIFACTS
# ---------------------------------------------------------------------

print("\n[4] RESEARCH ARTIFACT SCHEMAS")
print("-" * 80)

artifact_names = [
    "scenario_weapon_research_batch_execution.csv",
    "scenario_weapon_research_batches.csv",
    "scenario_weapon_research_queue.csv",
    "scenario_weapon_evidence.csv",
    "scenario_weapon_oos.csv",
    "scenario_weapon_walk_forward.csv",
    "scenario_weapon_walk_forward_ledger.csv",
    "scenario_weapon_walk_forward_summary.csv",
    "scenario_weapon_eligibility.csv",
    "scenario_weapon_execution_readiness.csv",
    "scenario_coverage_audit.csv",
]

for filename in artifact_names:

    path = ART / filename

    if not path.exists():
        print(f"\n{filename}: MISSING")
        continue

    try:
        df = pd.read_csv(path)

        print(f"\n{filename}")
        print("rows:", len(df))
        print("columns:")
        print(list(df.columns))

        if len(df):
            print("sample:")
            print(df.head(3).to_string(index=False))

    except Exception as e:
        print(filename, "ERROR:", e)

# ---------------------------------------------------------------------
# 5. EVIDENCE COUNTS BY SCENARIO / WEAPON
# ---------------------------------------------------------------------

print("\n[5] EVIDENCE COUNTS")
print("-" * 80)

for filename in [
    "scenario_weapon_evidence.csv",
    "scenario_weapon_oos.csv",
    "scenario_weapon_walk_forward.csv",
    "scenario_weapon_research_batches.csv",
]:

    path = ART / filename

    if not path.exists():
        continue

    try:
        df = pd.read_csv(path)

        print(f"\n{filename}: {len(df)} rows")

        possible_cols = [
            c for c in df.columns
            if any(
                x in c.lower()
                for x in [
                    "scenario",
                    "weapon",
                    "candidate",
                    "oos",
                    "evidence",
                    "status"
                ]
            )
        ]

        print("diagnostic columns:", possible_cols)

        for c in possible_cols:
            if df[c].nunique(dropna=False) <= 20:
                print(f"\n{c} distribution:")
                print(df[c].value_counts(dropna=False).head(20))

    except Exception as e:
        print("ERROR:", e)

# ---------------------------------------------------------------------
# 6. CURRENT READINESS BLOCKER BREAKDOWN
# ---------------------------------------------------------------------

print("\n[6] CURRENT READINESS BLOCKER")
print("-" * 80)

path = ART / "scenario_weapon_execution_readiness.csv"

if path.exists():

    df = pd.read_csv(path)

    print("rows:", len(df))
    print("columns:", list(df.columns))

    for c in df.columns:

        if (
            "status" in c.lower()
            or "readiness" in c.lower()
            or "holdout" in c.lower()
            or "evidence" in c.lower()
        ):

            print(f"\n{c}:")
            print(
                df[c]
                .value_counts(dropna=False)
                .head(30)
            )

# ---------------------------------------------------------------------
# 7. FINAL DIAGNOSIS
# ---------------------------------------------------------------------

print("\n" + "=" * 80)
print("TRACK C EVIDENCE-CHAIN DIAGNOSTIC COMPLETE")
print("=" * 80)

conn.close()
