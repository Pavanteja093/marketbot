import sqlite3
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


FACTORS = [
    "relative_strength",
    "trend_score",
    "momentum_score",
    "volatility_score",
    "liquidity_score",
]


def load_data():

    conn = sqlite3.connect(str(DB_PATH))

    df = pd.read_sql(
        """
        SELECT
            p.prediction_date,
            p.index_name,
            p.return_5d,

            f.relative_strength,
            f.trend_score,
            f.momentum_score,
            f.volatility_score,
            f.liquidity_score

        FROM prediction_outcomes p

        INNER JOIN factor_history f
            ON p.prediction_date = f.trade_date
            AND p.index_name = f.index_name

        WHERE
            p.return_5d IS NOT NULL

        ORDER BY
            p.prediction_date,
            p.index_name
        """,
        conn
    )

    conn.close()

    return df


def daily_ic(group, factor):

    x = pd.to_numeric(
        group[factor],
        errors="coerce"
    )

    y = pd.to_numeric(
        group["return_5d"],
        errors="coerce"
    )

    valid = pd.concat(
        [x, y],
        axis=1
    ).dropna()

    if len(valid) < 5:
        return None

    if valid[factor].nunique() < 2:
        return None

    if valid["return_5d"].nunique() < 2:
        return None

    value = valid[factor].corr(
        valid["return_5d"]
    )

    if pd.isna(value):
        return None

    return float(value)


def analyze_factor(df, factor):

    rows = []

    for date, group in df.groupby(
        "prediction_date"
    ):

        ic = daily_ic(
            group,
            factor
        )

        if ic is not None:

            rows.append(
                {
                    "prediction_date": date,
                    "ic": ic
                }
            )

    result = pd.DataFrame(rows)

    if result.empty:
        return None

    ic = result["ic"]

    positive = int(
        (ic > 0).sum()
    )

    negative = int(
        (ic < 0).sum()
    )

    return {
        "factor": factor,
        "days": len(ic),
        "mean_ic": ic.mean(),
        "median_ic": ic.median(),
        "std_ic": ic.std(),
        "positive_days": positive,
        "negative_days": negative,
        "positive_pct": (
            positive / len(ic) * 100
        ),
        "negative_pct": (
            negative / len(ic) * 100
        ),
        "min_ic": ic.min(),
        "max_ic": ic.max(),
    }


def main():

    print("\n" + "=" * 80)
    print("MARKETBOT FACTOR STABILITY ANALYSIS")
    print("=" * 80)

    df = load_data()

    if df.empty:

        print("\nNo matched factor/outcome data.")
        return

    print(
        f"\nObservations : {len(df):,}"
    )

    print(
        f"Trading dates : "
        f"{df['prediction_date'].nunique():,}"
    )

    print(
        f"Symbols : "
        f"{df['index_name'].nunique():,}"
    )

    results = []

    for factor in FACTORS:

        result = analyze_factor(
            df,
            factor
        )

        if result:
            results.append(result)

    summary = pd.DataFrame(results)

    print("\n" + "=" * 80)
    print("FACTOR STABILITY")
    print("=" * 80)

    print(
        summary.round(4).to_string(
            index=False
        )
    )

    print("\n" + "=" * 80)
    print("FACTOR VERDICTS")
    print("=" * 80)

    for _, row in summary.iterrows():

        if row["positive_pct"] >= 60:

            verdict = "STABLE POSITIVE"

        elif row["negative_pct"] >= 60:

            verdict = "STABLE NEGATIVE"

        else:

            verdict = "UNSTABLE / REGIME DEPENDENT"

        print(
            f"{row['factor']:<25}"
            f"{verdict}"
        )


if __name__ == "__main__":
    main()