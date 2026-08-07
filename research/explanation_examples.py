import pandas as pd

from database.db import get_connection

from analytics.explainability_engine import explain


def explanation_examples():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT *
        FROM factor_history
        ORDER BY intelligence_score DESC
        LIMIT 5
        """,
        conn
    )

    conn.close()

    print("\n" + "=" * 60)
    print("EXPLAINABILITY EXAMPLES")
    print("=" * 60)

    for _, row in df.iterrows():

        result = explain(row)

        print()

        print(result["summary"])


if __name__ == "__main__":
    explanation_examples()