import sqlite3
from pathlib import Path

import pandas as pd

from analytics.feature_engine import FeatureEngine


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


# ============================================================
# CONFIGURATION
# ============================================================

MIN_HISTORY = 20


# ============================================================
# HISTORICAL FACTOR BUILDER
# ============================================================

def build_factor_history():

    print("\n" + "=" * 70)
    print("MARKETBOT HISTORICAL FACTOR BUILDER")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)

    # --------------------------------------------------------
    # LOAD STOCK HISTORY
    # --------------------------------------------------------

    stocks = pd.read_sql(
        """
        SELECT
            trade_date,
            symbol,
            open,
            high,
            low,
            previous_close,
            close,
            price_change,
            change_pct,
            volume
        FROM stocks_daily
        ORDER BY trade_date, symbol
        """,
        conn
    )

    if stocks.empty:

        print("\nERROR: stocks_daily contains no data.")

        conn.close()
        return

    stocks["trade_date"] = pd.to_datetime(
        stocks["trade_date"]
    )

    stocks = stocks.sort_values(
        [
            "symbol",
            "trade_date"
        ]
    ).reset_index(drop=True)

    print(
        f"Stock records loaded : "
        f"{len(stocks):,}"
    )

    print(
        f"Symbols              : "
        f"{stocks['symbol'].nunique()}"
    )

    print(
        f"Date range           : "
        f"{stocks['trade_date'].min().date()} "
        f"to "
        f"{stocks['trade_date'].max().date()}"
    )

    # --------------------------------------------------------
    # HISTORICAL MARKET RETURN PROXY
    #
    # indices_daily currently contains only one NIFTY50
    # observation. Therefore we cannot use it as the
    # historical benchmark.
    #
    # For this research backfill we calculate the daily
    # equal-weighted return of the available stock universe.
    # --------------------------------------------------------

    # --------------------------------------------------------
    # HISTORICAL NIFTY50 MARKET RETURN
    # --------------------------------------------------------

    indices = pd.read_sql(
        """
        SELECT
            trade_date,
            change_pct
        FROM indices_daily
        WHERE index_name = 'NIFTY50'
        ORDER BY trade_date
        """,
        conn,
    )

    if indices.empty:

        print(
            "\nERROR: NIFTY50 historical data unavailable."
        )

        conn.close()
        return

    indices["trade_date"] = pd.to_datetime(
        indices["trade_date"]
    )

    market_returns = dict(
        zip(
            indices["trade_date"],
            indices["change_pct"]
        )
    )

    print(
        f"NIFTY50 benchmark dates : "
        f"{len(market_returns)}"
    )

    # --------------------------------------------------------
    # CLEAR CURRENT BACKFILL
    # --------------------------------------------------------

    conn.execute(
        "DELETE FROM factor_history"
    )

    conn.commit()

    engine = FeatureEngine()

    records = []

    symbols = sorted(
        stocks["symbol"]
        .dropna()
        .unique()
    )

    print(
        f"Stocks to process    : "
        f"{len(symbols)}"
    )

    total_expected = 0
    total_generated = 0
    total_errors = 0

    # ========================================================
    # PROCESS EACH STOCK
    # ========================================================

    for number, symbol in enumerate(
        symbols,
        start=1
    ):

        history = (
            stocks[
                stocks["symbol"] == symbol
            ]
            .sort_values("trade_date")
            .reset_index(drop=True)
        )

        print(
            f"[{number:02d}/{len(symbols):02d}] "
            f"{symbol:<20} "
            f"{len(history)} rows"
        )

        if len(history) < MIN_HISTORY:

            print(
                f"    SKIPPED: "
                f"less than {MIN_HISTORY} rows"
            )

            continue

        # ----------------------------------------------------
        # Walk through history chronologically.
        #
        # We deliberately use only data available on or before
        # each observation date.
        # ----------------------------------------------------

        for i in range(
            MIN_HISTORY - 1,
            len(history)
        ):

            total_expected += 1

            current = history.iloc[i]

            trade_date = current["trade_date"]

            stock_return = current["change_pct"]

            market_return = market_returns.get(
                trade_date,
                0
            )

            historical_window = history.iloc[
                : i + 1
            ].copy()

            try:

                features = engine.build_features(
                    history_df=historical_window,
                    stock_return=stock_return,
                    market_return=market_return
                )

                record = {

                    "trade_date":
                        trade_date.strftime(
                            "%Y-%m-%d"
                        ),

                    "index_name":
                        symbol,

                    "change_pct":
                        stock_return,

                    "intelligence_score":
                        features.get(
                            "intelligence_score"
                        ),

                    "relative_strength":
                        features.get(
                            "relative_strength"
                        ),

                    "rs_grade":
                        features.get(
                            "rs_grade"
                        ),

                    "trend_score":
                        features.get(
                            "trend_score"
                        ),

                    "trend_grade":
                        features.get(
                            "trend_grade"
                        ),

                    "momentum_score":
                        features.get(
                            "momentum_score"
                        ),

                    "momentum_grade":
                        features.get(
                            "momentum_grade"
                        ),

                    "volatility_score":
                        features.get(
                            "volatility_score"
                        ),

                    "volatility_grade":
                        features.get(
                            "volatility_grade"
                        ),

                    "liquidity_score":
                        features.get(
                            "liquidity_score"
                        ),

                    "liquidity_grade":
                        features.get(
                            "liquidity_grade"
                        )
                }

                records.append(record)

                total_generated += 1

            except Exception as exc:

                total_errors += 1

                print(
                    f"\n    ERROR "
                    f"{symbol} "
                    f"{trade_date.date()}: "
                    f"{exc}"
                )

    # ========================================================
    # WRITE RESULTS
    # ========================================================

    result = pd.DataFrame(records)

    if result.empty:

        print(
            "\nERROR: No factor records generated."
        )

        conn.close()
        return

    result = result.drop_duplicates(
        subset=[
            "trade_date",
            "index_name"
        ],
        keep="last"
    )

    database_columns = [

        "trade_date",
        "index_name",
        "change_pct",

        "intelligence_score",

        "relative_strength",
        "rs_grade",

        "trend_score",
        "trend_grade",

        "momentum_score",
        "momentum_grade",

        "volatility_score",
        "volatility_grade",

        "liquidity_score",
        "liquidity_grade"
    ]

    # --------------------------------------------------------
    # Verify that the database actually has the columns.
    # --------------------------------------------------------

    schema = conn.execute(
        "PRAGMA table_info(factor_history)"
    ).fetchall()

    existing_columns = {
        row[1]
        for row in schema
    }

    missing_columns = [
        column
        for column in database_columns
        if column not in existing_columns
    ]

    if missing_columns:

        print(
            "\nERROR: factor_history is missing:"
        )

        for column in missing_columns:
            print(
                f"  - {column}"
            )

        conn.close()
        return

    result = result[
        database_columns
    ]

    result.to_sql(
        "factor_history",
        conn,
        if_exists="append",
        index=False
    )

    conn.commit()

    # ========================================================
    # VALIDATION
    # ========================================================

    database_rows = conn.execute(
        """
        SELECT COUNT(*)
        FROM factor_history
        """
    ).fetchone()[0]

    trading_dates = conn.execute(
        """
        SELECT COUNT(DISTINCT trade_date)
        FROM factor_history
        """
    ).fetchone()[0]

    symbol_count = conn.execute(
        """
        SELECT COUNT(DISTINCT index_name)
        FROM factor_history
        """
    ).fetchone()[0]

    min_date, max_date = conn.execute(
        """
        SELECT
            MIN(trade_date),
            MAX(trade_date)
        FROM factor_history
        """
    ).fetchone()

    print("\n" + "=" * 70)
    print("FACTOR HISTORY BUILD COMPLETE")
    print("=" * 70)

    print(
        f"Expected observations : "
        f"{total_expected:,}"
    )

    print(
        f"Generated observations: "
        f"{total_generated:,}"
    )

    print(
        f"Errors                : "
        f"{total_errors:,}"
    )

    print(
        f"Database rows         : "
        f"{database_rows:,}"
    )

    print(
        f"Trading dates         : "
        f"{trading_dates}"
    )

    print(
        f"Symbols               : "
        f"{symbol_count}"
    )

    print(
        f"Date range            : "
        f"{min_date} to {max_date}"
    )

    print("=" * 70)

    conn.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    build_factor_history()