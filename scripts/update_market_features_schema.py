from database.db import get_connection

conn = get_connection()
cursor = conn.cursor()

columns = [row[1] for row in cursor.execute(
    "PRAGMA table_info(market_features)"
).fetchall()]

new_columns = [
    ("expected_move", "REAL"),
    ("reward_risk", "REAL"),
    ("market_location", "TEXT"),
    ("trade_quality", "REAL"),
]

for name, dtype in new_columns:
    if name not in columns:
        cursor.execute(
            f"ALTER TABLE market_features ADD COLUMN {name} {dtype}"
        )
        print(f"Added: {name}")
    else:
        print(f"Already exists: {name}")

conn.commit()
conn.close()

print("\nSchema updated successfully.")