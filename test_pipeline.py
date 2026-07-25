import pandas as pd

from feature_engineering import FeaturePipeline


data = {
    "open": [100, 105, 103],
    "high": [108, 107, 110],
    "low": [99, 101, 102],
    "close": [106, 103, 109],
}

df = pd.DataFrame(data)

pipeline = FeaturePipeline()

result = pipeline.run(df)

print("\nGenerated Columns\n")

for column in result.columns:
    print(column)

print("\n")

print(result.head())