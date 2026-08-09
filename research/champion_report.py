from research.model_registry import load_models


def champion_report():

    models = load_models()

    print("\nChampion Model")
    print("-" * 40)

    for name, info in models.items():

        if info["status"] == "Champion":

            print(f"Name     : {name}")
            print(f"Version  : {info['version']}")
            print(f"Accuracy : {info['accuracy']:.2%}")
            print(f"Status   : {info['status']}")


if __name__ == "__main__":
    champion_report()