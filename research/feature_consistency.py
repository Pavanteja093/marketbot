import pandas as pd


def consistency(df):

    return df.std() / df.mean()


if __name__ == "__main__":

    print("Import from dashboard")