from database.db import get_connection
import pandas as pd

conn = get_connection()

df = pd.read_sql("""
SELECT *
FROM market_features
LIMIT 5
""", conn)

conn.close()

print("\nMARKET FEATURES\n")
print(df)

print("\nCOLUMNS\n")
print(df.columns.tolist())