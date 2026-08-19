import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import streamlit as st

from services.dashboard_service import get_dashboard_data


st.set_page_config(
    page_title="MarketBot",
    layout="wide"
)

st.title("MarketBot — Live Intelligence")


symbols = ["SENSEX", "NIFTY", "BANKNIFTY", "FINNIFTY"]

for symbol in symbols:

    dashboard = get_dashboard_data(symbol)

    if dashboard is None:
        st.warning(f"{symbol}: No market data available")
        continue

    state = dashboard["state"]
    direction = dashboard["direction"]
    regime = dashboard["regime"]
    decision = dashboard["decision"]

    st.header(symbol)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Spot",
        f"{state.spot_price:,.2f}"
    )

    c2.metric(
        "Direction",
        direction["bias"]
    )

    c3.metric(
        "Regime",
        regime["regime"]
    )

    c4.metric(
        "Confidence",
        f"{decision['confidence']}%"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Support",
        f"{state.support:,.2f}"
    )

    c2.metric(
        "Resistance",
        f"{state.resistance:,.2f}"
    )

    c3.metric(
        "PCR",
        f"{state.pcr:.2f}"
    )

    c4.metric(
        "Average IV",
        f"{state.avg_iv:.2f}"
    )

    st.success(
        f"Strategy: {decision['strategy']}"
    )

    st.info(
        f"Trade: {decision['trade']} | "
        f"Risk: {decision['risk']} | "
        f"Confidence: {decision['confidence']}%"
    )

    st.write("Reasons")

    for reason in decision["reasons"]:
        st.write(f"• {reason}")

    st.divider()
