import sqlite3
import pandas as pd
from analytics.scoring_engine import calculate_trade_score
from analytics.market_levels import get_market_levels

DB_PATH = r"C:\Users\pavan\Documents\Python\Marketbot\market_intelligence.db"

def save_market_features(data):

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR REPLACE INTO market_features
    (
        trade_time,
        symbol,
        spot_price,
        avg_iv,
        iv_regime,
        strategy,
        real_pcr,
        support,
        resistance,
        max_pain,
        delta,
        gamma,
        theta,
        vega,
        market_bias,
        confidence
    )

    VALUES
    (
        ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
    ) 
    """, (

        data["trade_time"],
        data["symbol"],
        data["spot_price"],
        data["avg_iv"],
        data["iv_regime"],
        data["strategy"],
        data["real_pcr"],
        data["support"],
        data["resistance"],
        data["max_pain"],
        data["delta"],
        data["gamma"],
        data["theta"],
        data["vega"],
        data["market_bias"],
        data["confidence"]

    ))

    conn.commit()
    conn.close()                                 

def get_market_brain():

    conn = sqlite3.connect(DB_PATH)

    symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY"]

    results = {}

    for symbol in symbols:

        query = f"""
        SELECT *

        FROM option_chain_history

        WHERE symbol='{symbol}'

        AND trade_time = (

            SELECT MAX(trade_time)

            FROM option_chain_history

            WHERE symbol='{symbol}'
        )
        """

        df = pd.read_sql(query, conn)

        if df.empty:
            continue

        # ---------------------------------
        # Spot Price
        # ---------------------------------

        spot = float(df["spot_price"].iloc[0])

        # ---------------------------------
        # REAL PCR
        # ---------------------------------

        total_put = df["put_oi"].sum()

        total_call = df["call_oi"].sum()

        real_pcr = total_put / total_call if total_call else 0

        # ---------------------------------
        # Support / Resistance
        # ---------------------------------
        
        support = float(df["strike"][df["put_oi"].idxmax()])

        resistance = float(df["strike"][df["call_oi"].idxmax()])
        

        # ---------------------------------
        # Max Pain
        # ---------------------------------

        df["pain"] = df["call_oi"] + df["put_oi"]

        max_pain = float(df["strike"][df["pain"].idxmax()])

        # ---------------------------------
        # IV
        # ---------------------------------

        avg_iv = (
            df["call_iv"].mean() +
            df["put_iv"].mean()
        ) / 2

        # ---------------------------------
        # Expected Move
        # ---------------------------------

        import math

        days_to_expiry = 7   # temporary

        expected_move = (
            spot *
            (avg_iv / 100) *
            math.sqrt(days_to_expiry / 365)
        )

        upper_target = spot + expected_move
        lower_target = spot - expected_move


        # ---------------------------------
        # Greeks
        # ---------------------------------

        delta = (
            df["call_delta"].mean() +
            abs(df["put_delta"].mean())
        ) / 2

        gamma = (
            df["call_gamma"].mean() +
            df["put_gamma"].mean()
        ) / 2

        theta = (
            abs(df["call_theta"].mean()) +
            abs(df["put_theta"].mean())
        ) / 2

        vega = (
            df["call_vega"].mean() +
            df["put_vega"].mean()
        ) / 2

        levels = get_market_levels(df)

        if not levels:
            continue

        support = levels["support"]
        resistance = levels["resistance"]

        distance_support = abs(spot - support)
        distance_resistance = abs(resistance - spot)

        risk_distance = max(distance_support, 1)
        reward_distance = max(distance_resistance, 1)

        rr = reward_distance / risk_distance

        range_width = resistance - support
        position = (spot - support) / range_width if range_width else 0

        if position < 0.3:
            location = "LOWER RANGE"
        elif position > 0.7:
            location = "UPPER RANGE"
        else:
            location = "MIDDLE RANGE"

        decision = calculate_trade_score(
            spot=spot,
            support=support,
            resistance=resistance,
            real_pcr=real_pcr,
            avg_iv=avg_iv,
            gamma=gamma,
            theta=theta,
            rr=rr
        )

        score = decision["score"]
        bias = decision["bias"]
        confidence = decision["confidence"]
        risk = decision["risk"]
        trade = decision["trade"]
        strategy = decision["strategy"]
        reasons = decision["reasons"]

        save_market_features({

        "trade_time": df["trade_time"].iloc[0],

        "symbol": symbol,

        "spot_price": spot,

        "avg_iv": avg_iv,

        "iv_regime": "HIGH VOLATILITY" if avg_iv > 25 else "LOW VOLATILITY",

        "strategy": strategy,

        "real_pcr": real_pcr,

        "support": support,

        "resistance": resistance,

        "max_pain": max_pain,

        "delta": delta,

        "gamma": gamma,

        "theta": theta,

        "vega": vega,

        "market_bias": bias,

        "confidence": confidence

    })

        results[symbol] = {
            
            "symbol": symbol,

            "spot_price": spot,

            "real_pcr": real_pcr,

            "support": support,
            "resistance": resistance,
            "max_pain": max_pain,

            "avg_iv": avg_iv,

            "expected_move": expected_move,
            "upper_target": upper_target,
            "lower_target": lower_target,

            "delta": delta,
            "gamma": gamma,
            "theta": theta,
            "vega": vega,

            "reward_risk": rr,
            "market_location": location,

            "score": score,
            "bias": bias,
            "confidence": confidence,
            "risk": risk,
            "trade": trade,
            "strategy": strategy,
            "reasons": reasons
        }

    conn.close()
    return results


if __name__ == "__main__":
    from pprint import pprint

    results = get_market_brain()
    pprint(results)