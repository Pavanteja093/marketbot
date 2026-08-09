import sqlite3

conn = sqlite3.connect("market_intelligence.db")

cursor = conn.cursor()

columns = [
    ("prediction", "TEXT"),
    ("confidence", "REAL"),
    ("risk", "TEXT"),
    ("future_return_5d", "REAL"),
    ("future_return_20d", "REAL"),
    ("prediction_correct", "INTEGER")
]

for name, dtype in columns:

    try:
        cursor.execute(
            f"""
            ALTER TABLE prediction_history
            ADD COLUMN {name} {dtype}
            """
        )

        print(f"Added {name}")

    except Exception:

        print(f"{name} already exists")

conn.commit()

conn.close()