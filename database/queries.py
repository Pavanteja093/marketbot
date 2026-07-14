LATEST_OPTION_CHAIN = """
SELECT *
FROM option_chain_history
WHERE symbol=?
AND trade_time=(
    SELECT MAX(trade_time)
    FROM option_chain_history
    WHERE symbol=?
)
"""


LATEST_SIGNAL = """
SELECT *
FROM performance_signals
ORDER BY signal_time DESC
LIMIT 1
"""


LATEST_SYSTEM_STATUS = """
SELECT *
FROM system_status
"""