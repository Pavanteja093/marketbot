import sqlite3

def save_decision(result):

    conn = sqlite3.connect("market_intelligence.db")

    conn.execute("""

    CREATE TABLE IF NOT EXISTS decision_history(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        regime TEXT,

        confidence REAL,

        risk TEXT,

        recommendation TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    )

    """)

    conn.execute("""

    INSERT INTO decision_history(

        regime,

        confidence,

        risk,

        recommendation

    )

    VALUES(?,?,?,?)

    """,(

        result["regime"],

        result["confidence"],

        result["risk"],

        result["recommendation"]["action"]

    ))

    conn.commit()

    conn.close()