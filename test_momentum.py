import pandas as pd

from analytics.momentum_score import calculate_momentum

df = pd.DataFrame(
    {
        "trade_date": pd.date_range("2026-01-01", periods=15),
        "close": [
            100,
            101,
            102,
            103,
            105,
            104,
            106,
            107,
            109,
            111,
            112,
            114,
            116,
            118,
            121,
        ],
    }
)

score, grade = calculate_momentum(df)

print(score)
print(grade)