from feature_engineering.feature_catalog import FeatureCatalog

catalog = FeatureCatalog()

print("\nFeature Catalog\n")

for feature in catalog.list_features():
    print(feature)