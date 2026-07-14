import sqlite3
import pandas as pd
from analytics.scoring_engine import calculate_trade_score

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

conn = sqlite3.connect(DB_PATH)

symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY"]

print("\n" + "=" * 70)
print("MARKETBOT BRAIN v1")
print("=" * 70)

for symbol in symbols:

    query = f"""
    SELECT *

    FROM option_chain_history

    WHERE symbol='{symbol}'

    AND trade_time=(

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

    # ---------------------------------
    # TRADE QUALITY SCORE
    # ---------------------------------

    score = 50

    reasons = []

    score_breakdown = []

    # PCR

    if real_pcr > 1:
        score += 15
        score_breakdown.append(("PCR", +15))
        reasons.append("Bullish PCR")
    else:
        score -= 15
        score_breakdown.append(("PCR", +15))
        reasons.append("Bearish PCR")

    # Support / Resistance

    distance_support = abs(spot - support)
    distance_resistance = abs(resistance - spot)

    if distance_support < distance_resistance:
        score += 10
        reasons.append("Closer to Support")
    else:
        score -= 20
        score_breakdown.append(("Support Position", -20))
        reasons.append("Closer to Resistance")
    
    reward = abs(resistance - spot)
    risk_points = abs(spot - support)

    rr = reward / risk_points if risk_points else 0

    # Market Location

    range_width = resistance - support
    position = (spot - support) / range_width if range_width else 0

    if position < 0.3:
        location = "LOWER RANGE"

    elif position > 0.7:
        location = "UPPER RANGE"

    else:
        location = "MIDDLE RANGE"

    # IV

    if avg_iv > 25:
        score += 10
        reasons.append("High IV")
    else:
        reasons.append("Normal IV")

    # Gamma

    if gamma < 0.02:
        score += 5
        reasons.append("Low Gamma")

    # Theta

    if theta > 0.5:
        score += 10
        reasons.append("High Theta")

    # ---------------------------------
    # Reward / Risk
    # ---------------------------------

    if rr >= 2:
        score += 10
        reasons.append("Excellent Reward/Risk")

    elif rr >= 1:
        score += 5
        reasons.append("Good Reward/Risk")

    else:
        score -= 10
        reasons.append("Poor Reward/Risk")

    score = max(0, min(score, 100))

    # ---------------------------------
    # Decision
    # ---------------------------------

    if score >= 80:

        bias = "BULLISH"
        strategy = "Bull Put Spread"
        confidence = score

    elif score >= 65:

        bias = "SLIGHTLY BULLISH"
        strategy = "Iron Condor"
        confidence = score

    elif score <= 20:

        bias = "BEARISH"
        strategy = "Bear Call Spread"
        confidence = 100 - score

    elif score <= 35:

        bias = "SLIGHTLY BEARISH"
        strategy = "Iron Condor"
        confidence = 100 - score

    else:

        bias = "NEUTRAL"
        strategy = "Wait"
        confidence = 60

    if score >= 80:
        risk = "LOW"

    elif score >= 60:
        risk = "MEDIUM"

    else:
        risk = "HIGH"

    if score >= 75:
        trade = "YES"

    elif score >= 60:

        if distance_support < distance_resistance:
            trade = "WAIT FOR BOUNCE FROM SUPPORT"
        else:
            trade = "WAIT FOR BREAKOUT ABOVE RESISTANCE"



    else:
        trade = "NO"

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

    print("\n" + "=" * 70)

    print(symbol)

    print("=" * 70)

    print(f"Spot Price      : {spot:.2f}")

    print(f"Real PCR        : {real_pcr:.2f}")

    print(f"Support         : {support}")

    print(f"Resistance      : {resistance}")

    print(f"Reward/Risk    : {rr:.2f}")

    print(f"Max Pain        : {max_pain}")

    print(f"Market Location: {location}")

    print(f"Average IV      : {avg_iv:.2f}")

    print(f"Expected Move   : ±{expected_move:.2f}")
    
    print(f"Expected Range  : {lower_target:.2f} - {upper_target:.2f}")

    print(f"Delta           : {delta:.4f}")

    print(f"Gamma           : {gamma:.4f}")

    print(f"Theta           : {theta:.4f}")

    print(f"Vega            : {vega:.4f}")

    print("\nMarket Bias")

    print(bias)

    print(f"\nTrade Quality : {score}/100")

    print(f"Risk            : {risk}")

    print(f"Trade Decision : {trade}")

    print("\nRecommended Strategy")

    print(strategy)

    print(f"\nConfidence : {confidence}%")

    print("\nReasons")

    for r in reasons:

        print("-", r)

conn.close()