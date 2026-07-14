from database.repository import get_market_state
from models.regime_model import RegimeModel

state = get_market_state("NIFTY")
if state is None:
    raise RuntimeError("No market state found.")

model = RegimeModel()

result = model.predict(state)

print()
print("=" * 60)
print("MARKETBOT REGIME MODEL")
print("=" * 60)

print("Symbol      :", state.symbol)
print("Regime      :", result["regime"])
print("Confidence  :", result["confidence"])
print("Strategy    :", result["strategy"])