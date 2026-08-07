import json

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

WEIGHT_FILE = BASE_DIR / "weights.json"


DEFAULT_WEIGHTS = {

    "relative_strength":0.20,

    "trend_score":0.20,

    "momentum_score":0.20,

    "volatility_score":0.20,

    "liquidity_score":0.20

}


def load_weights():

    if WEIGHT_FILE.exists():

        with open(WEIGHT_FILE,"r") as f:

            return json.load(f)

    return DEFAULT_WEIGHTS