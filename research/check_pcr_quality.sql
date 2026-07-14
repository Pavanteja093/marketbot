SELECT
    symbol,
    SUM(put_oi) AS total_put_oi,
    SUM(call_oi) AS total_call_oi
FROM option_chain_history
WHERE trade_time = (
    SELECT MAX(trade_time)
    FROM option_chain_history o2
    WHERE o2.symbol = option_chain_history.symbol
)
GROUP BY symbol;