"""Compatibility adapter for the retired V1 stock scorer.

Production currently uses Stock Scoring V2.  Older research/report modules
still import analytics.stock_scoring, so this adapter deliberately delegates
to the V2 implementation rather than maintaining two scoring algorithms.
"""

from analytics.stock_scoring_v2 import get_stock_scores_v2


def get_stock_scores(trade_date=None):
    return get_stock_scores_v2(trade_date)


if __name__ == "__main__":
    df = get_stock_scores()
    print(df.head(15).to_string(index=False))
