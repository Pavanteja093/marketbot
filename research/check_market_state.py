from database.repository import get_market_state

state = get_market_state("NIFTY")

print()

print("="*60)
print("CURRENT MARKET STATE")
print("="*60)

print("Symbol       :", state.symbol)
print("Spot Price   :", state.spot_price)
print("Average IV   :", state.avg_iv)
print("IV Regime    :", state.iv_regime)
print("Strategy     :", state.recommended_strategy)
print("Market Bias  :", state.market_bias)
print("Confidence   :", state.confidence)