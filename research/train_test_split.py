from research.ml_dataset import build_ml_dataset


def split_dataset():

    df = build_ml_dataset()

    if df is None:
        return

    split = int(len(df)*0.8)

    train = df.iloc[:split]

    test = df.iloc[split:]

    print()

    print("="*60)

    print("TRAIN / TEST SPLIT")

    print("="*60)

    print("Training :",len(train))

    print("Testing  :",len(test))

    return train,test


if __name__=="__main__":

    split_dataset()