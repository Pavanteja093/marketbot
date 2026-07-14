import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

sys.path.append(str(BASE_DIR))

from analytics.alpha_signal_v3 import alpha_signal_v3


def recommendation_widget():

    signals = alpha_signal_v3()

    if len(signals) == 0:
        return None

    return signals