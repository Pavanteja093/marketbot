import json
from datetime import datetime
from pathlib import Path


def save_evolution():

    registry_file = Path("models/model_registry.json")

    with open(registry_file) as f:
        registry = json.load(f)

    print("\nMODEL EVOLUTION SNAPSHOT")
    print("-" * 50)

    print("Captured at:", datetime.now().strftime("%Y-%m-%d %H:%M"))

    for model, info in registry.items():
        print(
            f"{model} | "
            f"Version {info['version']} | "
            f"Accuracy {info['accuracy']}"
        )