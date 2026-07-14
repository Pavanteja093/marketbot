from analytics.scoring_engine import calculate_trade_score

result = calculate_trade_score(
    spot=24430,
    support=24000,
    resistance=24500,
    real_pcr=1.48,
    avg_iv=28.65,
    gamma=0.0003,
    theta=16.57,
    rr=0.16
)

print(result)