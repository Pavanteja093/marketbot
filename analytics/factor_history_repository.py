from database.db import get_connection


def save_factor_history(row):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO factor_history
        (
            trade_date,
            index_name,

            relative_strength,
            rs_grade,

            momentum_score,
            momentum_grade,

            trend_score,
            trend_grade,

            volatility_score,
            volatility_grade,

            liquidity_score,
            liquidity_grade
        )
        VALUES
        (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        (
            row["trade_date"],
            row["symbol"],

            row["relative_strength"],
            row["rs_grade"],

            row["momentum_score"],
            row["momentum_grade"],

            row["trend_score"],
            row["trend_grade"],

            row["volatility_score"],
            row["volatility_grade"],

            row["liquidity_score"],
            row["liquidity_grade"]
        )
    )

    conn.commit()
    conn.close()