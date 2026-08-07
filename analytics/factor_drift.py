import pandas as pd


def factor_drift(today, yesterday):

    return (

        today

        -

        yesterday

    ).round(2)