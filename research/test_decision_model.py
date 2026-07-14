from database.repository import get_market_state
from models.decision_model import DecisionModel

state = get_market_state("NIFTY")

if state is None:
    raise RuntimeError("No market state found.")

model = DecisionModel()

result = model.predict(state)

print()
print("=" * 60)
print("MARKETBOT DECISION MODEL")
print("=" * 60)

print("Symbol      :", state.symbol)
print("Direction   :", result["prediction"])
print("Regime      :", result["regime"])
print("Trade       :", result["trade"])
print("Strategy    :", result["strategy"])
print("Risk        :", result["risk"])
print("Confidence  :", result["confidence"])

print()
print("Reasons")
print("-" * 60)

for reason in result["reasons"]:
    print("✓", reason)