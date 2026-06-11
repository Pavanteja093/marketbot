CREATE TABLE IF NOT EXISTS indices_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_date DATE,
    symbol TEXT,

    open REAL,
    high REAL,
    low REAL,

    previous_close REAL,
    close REAL,

    price_change REAL,
    change_pct REAL,

    volume INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS indices_intraday (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    timestamp DATETIME,
    index_name TEXT,

    open REAL,
    high REAL,
    low REAL,
    close REAL
);

CREATE TABLE IF NOT EXISTS stocks_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_date DATE,
    symbol TEXT,

    open REAL,
    high REAL,
    low REAL,
    

    previous_close REAL,
    close REAL,


    price_change REAL,
    change_pct REAL,

    volume INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(trade_date, symbol)
);

CREATE TABLE IF NOT EXISTS fii_dii_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_date DATE,

    fii_buy REAL,
    fii_sell REAL,
    fii_net REAL,

    dii_buy REAL,
    dii_sell REAL,
    dii_net REAL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS options_summary (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_date DATE,

    index_name TEXT,

    spot_price REAL,

    pcr REAL,

    max_pain INTEGER,

    atm_strike INTEGER,

    highest_call_oi INTEGER,

    highest_put_oi INTEGER,

    market_bias TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(trade_date, index_name)
);

CREATE TABLE IF NOT EXISTS signal_history (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_date DATE,

    symbol TEXT,

    sector TEXT,

    score REAL,

    rank INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);