from research.model_registry import load_models


def challenger_report():

    models = load_models()

    print("\nChallenger Models")
    print("-" * 40)

    found = False

    for name, info in models.items():

        if info["status"] == "Challenger":

            found = True

            print(f"{name} ({info['version']})")

    if not found:

        print("No challengers registered.")