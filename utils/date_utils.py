import pandas as pd


def normalize_trade_date(series):
    """
    Convert any datetime-like series to YYYY-MM-DD strings.
    """

    return (
        pd.to_datetime(series)
        .dt.strftime("%Y-%m-%d")
    )