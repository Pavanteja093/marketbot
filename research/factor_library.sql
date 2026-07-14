CREATE TABLE factor_library (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_date DATE,
    symbol TEXT,

    position_52w REAL,
    breakout_distance REAL,
    volume_expansion REAL,
    volatility_rank REAL,

    UNIQUE(trade_date, symbol)
);