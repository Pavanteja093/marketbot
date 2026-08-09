import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_FILE = BASE_DIR / "models" / "models.json"


def load_models():

    if MODEL_FILE.exists():

        with open(MODEL_FILE, "r") as f:
            return json.load(f)

    models = {
        "MarketBot V1": {
            "version": "1.0",
            "accuracy": 0.0,
            "status": "Champion"
        }
    }

    save_models(models)

    return models


def save_models(models):

    MODEL_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(MODEL_FILE, "w") as f:

        json.dump(
            models,
            f,
            indent=4
        )


def get_champion():

    models = load_models()

    for name, data in models.items():

        if data.get("status") == "Champion":
            return name

    return None


def get_model(version):

    models = load_models()

    return models.get(version)