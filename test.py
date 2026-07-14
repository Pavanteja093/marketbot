import sqlite3

DB_PATH = r"C:\Users\pavan\Documents\Python\Marketbot\market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS system_status (

    component TEXT PRIMARY KEY,

    last_successful_write TEXT,
               
    rows_inserted INTEGER,

    last_error TEXT,

    status TEXT

)
""")

conn.commit()
conn.close()

print("system_status created")