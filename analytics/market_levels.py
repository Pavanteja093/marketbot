import pandas as pd


def get_market_levels(df, window=10):
    """
    Determine support and resistance using nearby Open Interest clusters.

    Parameters
    ----------
    df : pandas.DataFrame
        Option chain containing at least:
            strike
            spot_price
            call_oi
            put_oi

    window : int
        Number of strikes above/below ATM to analyse.

    Returns
    -------
    dict
    """

    if df.empty:
        return {
            "spot_price": 0,
            "atm_strike": 0,
            "support": 0,
            "resistance": 0,
            "major_support": 0,
            "major_resistance": 0,
            "support_strength": 0,
            "resistance_strength": 0,
            "analysis_window": 0,
        }


    df = df.copy()

    spot = float(df["spot_price"].iloc[0])

    strikes = sorted(df["strike"].unique())

    # -------------------------
    # Find ATM Strike
    # -------------------------

    atm = min(strikes, key=lambda x: abs(x - spot))

    atm_index = strikes.index(atm)

    start = max(0, atm_index - window)
    end = min(len(strikes), atm_index + window + 1)

    nearby = strikes[start:end]

    local_df = df[df["strike"].isin(nearby)].copy()

    # -------------------------
    # Support
    # -------------------------

    support_df = local_df[local_df["strike"] <= spot]

    if support_df.empty:
        support = atm
        support_strength = 0
    else:
        idx = support_df["put_oi"].idxmax()
        support = float(support_df.loc[idx, "strike"])
        support_strength = int(support_df.loc[idx, "put_oi"])

    # -------------------------
    # Resistance
    # -------------------------

    resistance_df = local_df[local_df["strike"] >= spot]

    if resistance_df.empty:
        resistance = atm
        resistance_strength = 0
    else:
        idx = resistance_df["call_oi"].idxmax()
        resistance = float(resistance_df.loc[idx, "strike"])
        resistance_strength = int(resistance_df.loc[idx, "call_oi"])

    return {

        "spot_price": spot,
        "atm_strike": atm,

        "support": support,
        "resistance": resistance,

        "major_support": support,
        "major_resistance": resistance,

        "support_strength": support_strength,
        "resistance_strength": resistance_strength,

        "analysis_window": len(local_df)

    }