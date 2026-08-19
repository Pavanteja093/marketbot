import pandas as pd


def detect_regime(features):
    """
    Determine the current market regime from
    intelligence score and volatility.
    """

    intelligence = features["intelligence_score"]
    volatility = features["volatility_score"]

    if intelligence >= 70 and volatility <= 40:
        return "STRONG BULL"

    elif intelligence >= 60:
        return "BULL"

    elif intelligence >= 45:
        return "SIDEWAYS"

    elif intelligence >= 30:
        return "BEAR"

    return "STRONG BEAR"


if __name__ == "__main__":

    sample = {
        "intelligence_score": 68,
        "volatility_score": 32
    }

    print(detect_regime(sample))

def get_market_regime():
    """Legacy report API backed by the latest NIFTY/stock snapshot.

    Returns the dictionary expected by the existing reports. This is a
    compatibility layer; the core regime classifier remains detect_regime().
    """
    import sqlite3
    from pathlib import Path

    db = Path(__file__).resolve().parent.parent / "market_intelligence.db"
    conn = sqlite3.connect(str(db))
    try:
        row = conn.execute("""
            SELECT
                COALESCE(
                    (SELECT change_pct FROM indices_daily
                     WHERE index_name = 'NIFTY50'
                     ORDER BY trade_date DESC LIMIT 1), 0.0
                ),
                COALESCE(
                    (SELECT
                        SUM(CASE WHEN change_pct > 0 THEN 1 ELSE 0 END) * 1.0 /
                        NULLIF(COUNT(*), 0)
                     FROM stocks_daily
                     WHERE trade_date = (SELECT MAX(trade_date) FROM stocks_daily)
                    ), 0.5
                )
        """).fetchone()
    finally:
        conn.close()

    nifty_change = float(row[0] or 0.0)
    positive_fraction = float(row[1] or 0.5)
    ad_ratio = positive_fraction / max(1.0 - positive_fraction, 1e-9)

    if nifty_change > 0.75 and ad_ratio >= 1.5:
        regime = "BULLISH TREND"
    elif nifty_change < -0.75 and ad_ratio <= (1 / 1.5):
        regime = "BEARISH TREND"
    else:
        regime = "SIDEWAYS"

    return {
        "regime": regime,
        "nifty_change": round(nifty_change, 2),
        "ad_ratio": round(ad_ratio, 2),
    }
