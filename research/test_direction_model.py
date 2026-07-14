from database.repository import get_market_state
from models.direction_model import DirectionModel


state = get_market_state("NIFTY")

model = DirectionModel()

result = model.predict(state)

print()
print("=" * 60)
print("MARKETBOT DIRECTION MODEL")
print("=" * 60)

print(f"Symbol                 : {state.symbol}")
print(f"Spot Price             : {state.spot_price:.2f}")
print()

print(f"Bullish Probability    : {result['bullish_probability']}%")
print(f"Bearish Probability    : {result['bearish_probability']}%")
print(f"Range Probability      : {result['neutral_probability']}%")
print()

print(f"Prediction             : {result['bias']}")
print(f"Confidence             : {result['confidence']}%")
print(f"Trade Quality          : {result['score']}/100")
print(f"Risk                   : {result['risk']}")
print(f"Trade                  : {result['trade']}")
print(f"Strategy               : {result['strategy']}")

print()
print("Reasons")
print("-" * 60)

for reason in result["reasons"]:
    print(f"✓ {reason}")