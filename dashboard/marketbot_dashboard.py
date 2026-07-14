import streamlit as st
import sqlite3
import pandas as pd

DB_PATH = r"C:\Users\pavan\Documents\Python\Marketbot\market_intelligence.db"

st.set_page_config(
    page_title="MarketBot Dashboard",
    layout="wide"
)

st.title("📈 MarketBot Dashboard")

# ============================================================
# DATABASE
# ============================================================

conn = sqlite3.connect(DB_PATH)

# ============================================================
# LATEST SIGNALS
# ============================================================

signals = pd.read_sql("""

SELECT *
FROM signal_performance

WHERE id IN (

    SELECT MAX(id)
    FROM signal_performance
    GROUP BY symbol

)

ORDER BY symbol

""", conn)

# ============================================================
# MARKET OVERVIEW
# ============================================================

st.header("Market Overview")

cols = st.columns(len(signals))

for i, (_, row) in enumerate(signals.iterrows()):

    with cols[i]:

        st.subheader(row["symbol"])

        st.metric(
            "Spot Price",
            f"{row['spot_price']:,.2f}"
        )

        st.write(f"PCR : {row['pcr']}")
        st.write(f"Regime : {row['regime']}")
        st.write(f"Strategy : {row['strategy']}")
        st.write(f"Confidence : {row['confidence']}%")

# ============================================================
# SIGNAL TABLE
# ============================================================

st.header("Latest Signals")

st.dataframe(
    signals,
    use_container_width=True
)

# ============================================================
# STRATEGY DISTRIBUTION
# ============================================================

st.header("Strategy Distribution")

strategy_count = pd.read_sql("""

SELECT
    strategy,
    COUNT(*) AS total

FROM signal_performance

GROUP BY strategy

ORDER BY total DESC

""", conn)

st.dataframe(
    strategy_count,
    use_container_width=True
)

# ============================================================
# DATABASE HEALTH
# ============================================================

st.header("Database Health")

option_rows = pd.read_sql("""

SELECT COUNT(*) AS total
FROM option_chain_history

""", conn)

signal_rows = pd.read_sql("""

SELECT COUNT(*) AS total
FROM signal_performance

""", conn)

col1, col2 = st.columns(2)

with col1:

    st.metric(
        "Option Chain Rows",
        int(option_rows.iloc[0]["total"])
    )

with col2:

    st.metric(
        "Signal Rows",
        int(signal_rows.iloc[0]["total"])
    )

# ============================================================
# RECENT SIGNAL HISTORY
# ============================================================

st.header("Recent Signal History")

history = pd.read_sql("""

SELECT *
FROM signal_performance

ORDER BY id DESC

LIMIT 20

""", conn)

st.dataframe(
    history,
    use_container_width=True
)

conn.close()