import pandas as pd

from database.db import get_connection


def dataset_health():

    conn = get_connection()

    factor = pd.read_sql(
        "SELECT COUNT(*) AS n FROM factor_history",
        conn
    )

    forward = pd.read_sql(
        "SELECT COUNT(*) AS n FROM forward_returns",
        conn
    )

    conn.close()

    print("\nDataset Health")

    print("Factor Records :", factor.iloc[0]["n"])
    print("Forward Records:", forward.iloc[0]["n"])


if __name__ == "__main__":
    dataset_health()