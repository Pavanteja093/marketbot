"""
MarketBot Feature Engineering

Utility Functions
"""

import pandas as pd

import numpy as np


def true_range(high, low, previous_close):

    tr1 = high - low
    tr2 = abs(high - previous_close)
    tr3 = abs(low - previous_close)

    return pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)


def atr(df: pd.DataFrame, period: int = 14):

    previous_close = df["close"].shift(1)

    tr = true_range(
        df["high"],
        df["low"],
        previous_close,
    )

    return tr.rolling(period).mean()


def historical_volatility(series, period=20):

    returns = np.log(
        series / series.shift(1)
    )

    return (
        returns
        .rolling(period)
        .std()
        * np.sqrt(252)
    )


def ema(series: pd.Series, period: int):

    return series.ewm(
        span=period,
        adjust=False
    ).mean()


def sma(series: pd.Series, period: int):

    return series.rolling(period).mean()


def roc(series: pd.Series, period: int):

    return (
        (series - series.shift(period))
        / series.shift(period)
    ) * 100


def momentum(series: pd.Series, period: int):

    return series.pct_change(period) * 100


def safe_divide(a, b):

    return a.divide(b.where(b != 0))

def rolling_mean(series: pd.Series, period: int):

    return series.rolling(period).mean()


def rolling_std(series: pd.Series, period: int):

    return series.rolling(period).std()


def relative_volume(volume: pd.Series, period: int):

    avg_volume = rolling_mean(volume, period)

    return safe_divide(volume, avg_volume)


def volume_ratio(volume: pd.Series):

    return safe_divide(volume, volume.shift(1))


def volume_change(volume: pd.Series):

    return volume.pct_change() * 100

def zscore(series: pd.Series, period: int):

    mean = rolling_mean(series, period)
    std = rolling_std(series, period)

    return safe_divide(series - mean, std)