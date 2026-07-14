from database.repository import get_market_state

state = get_market_state("NIFTY")

print(state)
print()

print("pcr =", state.pcr)
print("avg_iv =", state.avg_iv)
print("support =", state.support)
print("resistance =", state.resistance)
print("max_pain =", state.max_pain)