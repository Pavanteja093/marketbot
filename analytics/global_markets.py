import yfinance as yf
import pandas as pd

ASSETS = {
    "NASDAQ": "^IXIC",
    "S&P500": "^GSPC",
    "DOWJONES": "^DJI",
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "CRUDE": "CL=F",
    "DOLLAR_INDEX": "DX-Y.NYB",
    "INDIA_VIX": "^INDIAVIX"
}


def get_global_markets():

    results = []

    for name, ticker in ASSETS.items():

        try:

            data = yf.download(
                ticker,
                period="5d",
                auto_adjust=True,
                progress=False
            )

            if data.empty:
                continue

            if len(data) < 2:
                continue

            # Handle MultiIndex columns from yfinance
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            close = data["Close"].iloc[-1]
            prev_close = data["Close"].iloc[-2]

            close = float(close)
            prev_close = float(prev_close)

            change_pct = round(
                ((close - prev_close) / prev_close) * 100,
                2
            )

            results.append(
                [
                    name,
                    round(close, 2),
                    change_pct
                ]
            )

        except Exception as e:

            print(f"ERROR: {name}")
            print(e)

    df = pd.DataFrame(
        results,
        columns=[
            "Asset",
            "Price",
            "Change %"
        ]
    )

    return df


if __name__ == "__main__":

    df = get_global_markets()

    print("\n" + "=" * 60)
    print("GLOBAL MARKETS")
    print("=" * 60)

    if len(df) > 0:

        print(
            df.to_string(
                index=False
            )
        )

    else:

        print("No data available.")