import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

sys.path.append(str(BASE_DIR))

import streamlit as st
import sqlite3
import pandas as pd

from dashboard.recommendation_widget import recommendation_widget
from dashboard.performance_widget import performance_widget
from services.dashboard_service import get_dashboard_data

DB_PATH = BASE_DIR / "market_intelligence.db"

st.set_page_config(
    page_title="MarketBot",
    layout="wide"
)

st.title("📈 MarketBot Dashboard")

dashboard = get_dashboard_data("NIFTY")


if dashboard is not None:
    state = dashboard["state"]
    direction = dashboard["direction"]
    regime = dashboard["regime"]
    decision = dashboard["decision"]

    st.header("Market Intelligence")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Direction",
        direction["bias"]
    )

    c2.metric(
        "Regime",
        regime["regime"]
    )

    c3.metric(
        "Confidence",
        f"{decision['confidence']}%"
    )

    c4, c5, c6 = st.columns(3)

    c4.metric(
        "Support",
        state.support
    )

    c5.metric(
        "Resistance",
        state.resistance
    )

    c6.metric(
        "PCR",
        round(state.pcr, 2)
    )

    st.success(
        f"Strategy : {decision['strategy']}"
    )

    st.info(
        decision["trade"]
    )

# --------------------------------------------------
# Current Regime
# --------------------------------------------------

conn = sqlite3.connect(str(DB_PATH))

regime_df = pd.read_sql(
    """
    SELECT *
    FROM market_regime
    ORDER BY trade_date DESC
    LIMIT 1
    """,
    conn
)

conn.close()

current_regime = regime_df.iloc[0]["regime"]

st.metric(
    "Current Market Regime",
    current_regime
)

# --------------------------------------------------
# Today's Signals
# --------------------------------------------------

signals = recommendation_widget()

st.subheader("Today's Candidates")

if signals is not None:

    st.dataframe(
        signals[
            [
                "symbol",
                "sector",
                "position_52w",
                "volume_expansion",
                "sector_strength",
                "expected_return",
                "confidence"
            ]
        ],
        use_container_width=True
    )

# --------------------------------------------------
# Top Recommendation
# --------------------------------------------------

if signals is not None and len(signals) > 0:

    top = signals.iloc[0]

    st.subheader("Top Recommendation")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Symbol",
        top["symbol"]
    )

    col2.metric(
        "Expected Return",
        f"{top['expected_return']:.2f}%"
    )

    col3.metric(
        "Confidence",
        top["confidence"]
    )

# --------------------------------------------------
# Historical Recommendations
# --------------------------------------------------

st.subheader("Recommendation History")

conn = sqlite3.connect(str(DB_PATH))

history = pd.read_sql(
    """
    SELECT *
    FROM daily_recommendations
    ORDER BY id DESC
    LIMIT 20
    """,
    conn
)

conn.close()

st.dataframe(
    history,
    use_container_width=True
)

# --------------------------------------------------
# Performance Summary
# --------------------------------------------------

st.subheader("Performance Summary")

perf = performance_widget()

st.dataframe(
    perf,
    use_container_width=True
)