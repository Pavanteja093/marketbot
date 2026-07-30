import sqlite3
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


class MarketRegimeV2:

    def __init__(self):

        self.conn = sqlite3.connect(DB_PATH)

    # =====================================================
    # LOAD DATA
    # =====================================================

    def load_index(self):

        query = """
        SELECT *

        FROM indices_daily

        WHERE index_name='NIFTY50'

        ORDER BY trade_date DESC

        LIMIT 20
        """

        df = pd.read_sql(query, self.conn)

        if df.empty:
            raise Exception("No NIFTY50 data found.")

        return df

    def load_fii(self):

        query = """
        SELECT *

        FROM fii_dii_daily

        ORDER BY trade_date DESC

        LIMIT 1
        """

        df = pd.read_sql(query, self.conn)

        if df.empty:
            return None

        return df.iloc[0]

    def load_sector_strength(self):

        query = """
        SELECT

            AVG(sector_strength) AS sector_strength

        FROM factor_history

        WHERE trade_date=(

            SELECT MAX(trade_date)

            FROM factor_history

        )
        """

        df = pd.read_sql(query, self.conn)

        if df.empty:
            return 0.0

        value = df.iloc[0]["sector_strength"]

        if pd.isna(value):
            return 0.0

        return float(value)

    # =====================================================
    # FEATURE ENGINEERING
    # =====================================================

    def trend_score(self, latest):

        score = 15

        pct = latest["change_pct"]

        if pct >= 2:
            score = 30

        elif pct >= 1:
            score = 25

        elif pct >= 0.5:
            score = 20

        elif pct <= -2:
            score = 0

        elif pct <= -1:
            score = 5

        elif pct <= -0.5:
            score = 10

        return score

    def volatility_score(self, latest):

        rng = (
            latest["high"] -
            latest["low"]
        ) / latest["close"] * 100

        score = 10

        if rng < 0.8:
            score = 20

        elif rng < 1.5:
            score = 15

        elif rng < 2.5:
            score = 10

        elif rng < 3.5:
            score = 5

        else:
            score = 0

        return score

    def breadth_score(self, latest):

        pct = latest["change_pct"]

        if pct >= 1:
            return 20

        if pct >= 0:
            return 15

        if pct >= -1:
            return 10

        return 0

    def institutional_score(self, fii):

        if fii is None:
            return 7.5

        value = fii["fii_net"]

        if value >= 2000:
            return 15

        if value >= 1000:
            return 12

        if value >= 500:
            return 10

        if value >= 0:
            return 8

        if value >= -500:
            return 6

        if value >= -1000:
            return 4

        return 0

    def sector_score(self, strength):

        if strength >= 2:
            return 15

        if strength >= 1:
            return 12

        if strength >= 0.5:
            return 10

        if strength >= 0:
            return 8

        if strength >= -0.5:
            return 6

        if strength >= -1:
            return 4

        return 0

    # =====================================================
    # REGIME ENGINE
    # =====================================================

    def calculate_regime(self):

        market = self.load_index()

        latest = market.iloc[0]

        fii = self.load_fii()

        sector_strength = self.load_sector_strength()

        trend = self.trend_score(latest)

        volatility = self.volatility_score(latest)

        breadth = self.breadth_score(latest)

        institutional = self.institutional_score(fii)

        sector = self.sector_score(sector_strength)

        regime_score = round(

            trend +
            volatility +
            breadth +
            institutional +
            sector,

            2

        )

        if regime_score >= 80:

            regime = "STRONG_BULL"

        elif regime_score >= 60:

            regime = "WEAK_BULL"

        elif regime_score >= 40:

            regime = "RANGE_BOUND"

        elif regime_score >= 20:

            regime = "WEAK_BEAR"

        else:

            regime = "STRONG_BEAR"

        confidence = round(

            max(
                50,
                abs(regime_score - 50) * 2
            ),

            2

        )

        result = {

            "trade_date": latest["trade_date"],

            "trend_score": trend,

            "volatility_score": volatility,

            "breadth_score": breadth,

            "institutional_score": institutional,

            "sector_score": sector,

            "regime_score": regime_score,

            "market_regime": regime,

            "confidence": confidence

        }

        return result

        # =====================================================
    # SAVE TO DATABASE
    # =====================================================

    def save(self, result):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO market_regime (

                trade_date,

                trend,

                volatility,

                breadth,

                institutional_flow,

                sector_rotation,

                regime_score,

                market_regime,

                confidence

            )

            VALUES (?,?,?,?,?,?,?,?,?)

            """,
            (

                result["trade_date"],

                result["trend_score"],

                result["volatility_score"],

                result["breadth_score"],

                result["institutional_score"],

                result["sector_score"],

                result["regime_score"],

                result["market_regime"],

                result["confidence"]

            )
        )

        self.conn.commit()

    # =====================================================
    # REPORT
    # =====================================================

    def print_report(self, result):

        print("\n")
        print("=" * 65)
        print("              MARKETBOT MARKET REGIME V2")
        print("=" * 65)

        print(f"Trade Date           : {result['trade_date']}")
        print()

        print("Feature Scores")
        print("-" * 65)

        print(f"Trend Score          : {result['trend_score']:>6}")
        print(f"Volatility Score     : {result['volatility_score']:>6}")
        print(f"Breadth Score        : {result['breadth_score']:>6}")
        print(f"Institutional Score  : {result['institutional_score']:>6}")
        print(f"Sector Score         : {result['sector_score']:>6}")

        print("-" * 65)

        print(f"Regime Score         : {result['regime_score']:>6}")
        print(f"Market Regime        : {result['market_regime']}")
        print(f"Confidence           : {result['confidence']}%")

        print("=" * 65)

    # =====================================================
    # RUN
    # =====================================================

    def run(self):

        try:

            result = self.calculate_regime()

            self.save(result)

            self.print_report(result)

        finally:

            self.conn.close()


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    MarketRegimeV2().run()