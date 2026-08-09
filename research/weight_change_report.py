import json
from pathlib import Path


def weight_change_report():

    path = Path("models/adaptive_weights.json")

    if not path.exists():

        print("No adaptive weights found.")
        return

    with open(path) as f:

        weights = json.load(f)

    print("\n" + "=" * 60)
    print("CURRENT MODEL WEIGHTS")
    print("=" * 60)

    total = 0

    for factor, weight in sorted(
        weights.items(),
        key=lambda x: x[1],
        reverse=True
    ):

        print(f"{factor:25} {weight:.3f}")

        total += weight

    print("-" * 60)

    print(f"Total Weight : {total:.3f}")