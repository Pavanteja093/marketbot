import numpy as np


def calculate_liquidity(history_df):
    """
    Calculates liquidity score using average traded volume.

    Returns:
        score (0-100)
        grade (A+ to C)
    """

    if history_df.empty:
        return 0, "C"

    avg_volume = history_df["volume"].tail(20).mean()

    if np.isnan(avg_volume):
        return 0, "C"

    if avg_volume >= 10_000_000:
        return 100, "A+"

    elif avg_volume >= 5_000_000:
        return 90, "A"

    elif avg_volume >= 2_000_000:
        return 80, "B+"

    elif avg_volume >= 1_000_000:
        return 70, "B"

    elif avg_volume >= 500_000:
        return 60, "C+"

    return 40, "C"