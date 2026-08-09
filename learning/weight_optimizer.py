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


class WeightOptimizer:

    def __init__(self):

        self.db_path = DB_PATH

    def load_data(self):

        conn = sqlite3.connect(
            str(self.db_path)
        )

        query = """
        SELECT
            DATE(f.trade_date) AS trade_date,
            f.index_name,

            f.relative_strength,
            f.trend_score,
            f.momentum_score,
            f.volatility_score,
            f.liquidity_score,

            r.return_5d

        FROM factor_history f

        INNER JOIN forward_returns r

            ON DATE(f.trade_date)
            = DATE(r.trade_date)

            AND f.index_name
            = r.index_name

        WHERE
            r.return_5d IS NOT NULL
        """

        df = pd.read_sql(
            query,
            conn
        )

        conn.close()

        return df

    def calculate_daily_ic(
        self,
        df,
        factor,
    ):

        daily_ic = []

        for trade_date, group in df.groupby(
            "trade_date"
        ):

            subset = group[
                [factor, "return_5d"]
            ].dropna()

            if len(subset) < 10:
                continue

            if subset[factor].nunique() < 2:
                continue

            if subset["return_5d"].nunique() < 2:
                continue

            ic = subset[factor].corr(
                subset["return_5d"],
                method="spearman"
            )

            if pd.notna(ic):

                daily_ic.append(
                    {
                        "trade_date": trade_date,
                        "ic": float(ic),
                    }
                )

        return pd.DataFrame(daily_ic)

    def calculate_factor_statistics(
        self,
        df,
    ):

        results = {}

        for factor in FACTORS:

            daily = self.calculate_daily_ic(
                df,
                factor
            )

            if daily.empty:

                results[factor] = {
                    "mean_ic": None,
                    "ic_std": None,
                    "ic_ir": None,
                    "positive_days": None,
                    "observations": 0,
                }

                continue

            mean_ic = daily["ic"].mean()

            ic_std = daily["ic"].std(
                ddof=1
            )

            if (
                pd.notna(ic_std)
                and ic_std > 0
            ):

                ic_ir = (
                    mean_ic
                    / ic_std
                    * (
                        len(daily) ** 0.5
                    )
                )

            else:

                ic_ir = None

            results[factor] = {
                "mean_ic": round(
                    mean_ic,
                    6
                ),

                "ic_std": (
                    round(ic_std, 6)
                    if pd.notna(ic_std)
                    else None
                ),

                "ic_ir": (
                    round(ic_ir, 6)
                    if ic_ir is not None
                    else None
                ),

                "positive_days": int(
                    (
                        daily["ic"] > 0
                    ).sum()
                ),

                "observations": len(
                    daily
                ),
            }

        return results

    def recommend_weights(
        self,
        statistics,
    ):

        valid = {}

        for factor, result in statistics.items():

            mean_ic = result["mean_ic"]

            if mean_ic is None:
                continue

            # Direction is preserved.
            #
            # Factors with negative predictive
            # direction will later be inverted
            # during score construction.
            #
            # Weight magnitude is based on
            # predictive information strength.

            strength = abs(mean_ic)

            if strength <= 0:
                continue

            valid[factor] = {
                "strength": strength,
                "direction": (
                    1
                    if mean_ic > 0
                    else -1
                ),
            }

        if not valid:
            return {}

        total_strength = sum(
            item["strength"]
            for item in valid.values()
        )

        if total_strength == 0:
            return {}

        recommendations = {}

        for factor, item in valid.items():

            recommendations[factor] = {
                "weight": round(
                    item["strength"]
                    / total_strength,
                    4
                ),

                "direction": item[
                    "direction"
                ],
            }

        return recommendations

    def optimize(self):

        print("\n" + "=" * 70)
        print(
            "MARKETBOT FACTOR WEIGHT RESEARCH"
        )
        print("=" * 70)

        df = self.load_data()

        print(
            f"\nMatched observations : "
            f"{len(df):,}"
        )

        if df.empty:

            print(
                "No matched factor/return data."
            )

            return None

        statistics = (
            self.calculate_factor_statistics(
                df
            )
        )

        print(
            "\nCROSS-SECTIONAL FACTOR IC"
        )

        print("-" * 70)

        for factor, result in (
            statistics.items()
        ):

            print(
                f"{factor:<22}"
                f" MeanIC={str(result['mean_ic']):<10}"
                f" ICIR={str(result['ic_ir']):<10}"
                f" PositiveDays={str(result['positive_days']):<8}"
                f" N={result['observations']}"
            )

        recommended = (
            self.recommend_weights(
                statistics
            )
        )

        print(
            "\nRESEARCH WEIGHT SUGGESTION"
        )

        print("-" * 70)

        for factor, result in (
            recommended.items()
        ):

            direction = (
                "POSITIVE"
                if result["direction"] > 0
                else "NEGATIVE"
            )

            print(
                f"{factor:<22}"
                f" weight={result['weight']:.4f}"
                f" direction={direction}"
            )

        print("\nIMPORTANT:")
        print(
            "These are RESEARCH recommendations."
        )
        print(
            "They are NOT automatically promoted "
            "to production."
        )

        return {
            "statistics": statistics,
            "recommended_weights": recommended,
        }


if __name__ == "__main__":

    WeightOptimizer().optimize()