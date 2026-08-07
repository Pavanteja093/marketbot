def explain(row):

    reasons = []

    if row["relative_strength"] >= 80:
        reasons.append("Strong Relative Strength")

    if row["momentum_score"] >= 80:
        reasons.append("Strong Momentum")

    if row["trend_score"] >= 80:
        reasons.append("Strong Trend")

    if row["liquidity_score"] >= 80:
        reasons.append("High Liquidity")

    if row["volatility_score"] >= 80:
        reasons.append("Low Volatility")

    return reasons