import json


def challenger_statistics():

    with open("models/model_registry.json") as f:

        registry = json.load(f)

    print("\nCHALLENGER STATUS")

    print("-" * 40)

    for model, data in registry.items():

        if data["status"] != "Champion":

            print(model)

            print("Accuracy :", data["accuracy"])

            print("Wins      :", data["wins"])

            print("Losses    :", data["losses"])

            print()