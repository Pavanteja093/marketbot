CREATE TABLE indices_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_date DATE,
    index_name TEXT,

    open REAL,
    high REAL,
    low REAL,

    previous_close REAL,
    close REAL,

    price_change REAL,
    change_pct REAL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(trade_date,index_name)
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
    index_name TEXT,

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

    index_name TEXT,

    sector TEXT,

    score REAL,

    rank INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS signal_history_v2 (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_date DATE,

    index_name TEXT,

    sector TEXT,

    intelligence_score REAL,

    rank INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS factor_history (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_date DATE,

    index_name TEXT,

    sector TEXT,

    change_pct REAL,

    sector_strength REAL,

    position_pct REAL,

    total_score REAL,

    intelligence_score REAL,

    relative_strength REAL,

    rs_grade TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(trade_date, symbol)
);

CREATE TABLE IF NOT EXISTS forward_returns (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_date DATE,
    index_name TEXT,

    return_1d REAL,
    return_5d REAL,
    return_10d REAL,
    return_20d REAL
);

CREATE TABLE IF NOT EXISTS prediction_history (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_date DATE,

    index_name TEXT,

    sector TEXT,

    rank INTEGER,

    grade TEXT,

    intelligence_score REAL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(trade_date, symbol)
);

CREATE TABLE IF NOT EXISTS prediction_outcomes (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    prediction_date DATE,

    index_name TEXT,

    rank INTEGER,

    intelligence_score REAL,

    return_5d REAL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(prediction_date, symbol)
);

CREATE TABLE IF NOT EXISTS factor_library (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_date DATE,
    index_name TEXT,

    position_52w REAL,
    breakout_distance REAL,
    volume_expansion REAL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(trade_date, symbol)
);

CREATE TABLE IF NOT EXISTS direction_predictions (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    prediction_time TEXT,

    index_name TEXT,

    bullish_probability REAL,

    bearish_probability REAL,

    neutral_probability REAL,

    confidence REAL,

    direction TEXT

);

CREATE TABLE IF NOT EXISTS iv_analysis (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    analysis_time TEXT,

    index_name TEXT,

    avg_call_iv REAL,

    avg_put_iv REAL,

    avg_iv REAL,

    iv_regime TEXT,

    recommendation TEXT

);

CREATE TABLE IF NOT EXISTS learning_history (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_date DATE,

    index_name TEXT,

    prediction TEXT,

    actual_outcome TEXT,

    confidence REAL,

    strategy TEXT,

    trade_quality REAL,

    spot_price REAL,

    next_close REAL,

    next_day_return REAL,

    five_day_return REAL,

    correct INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(trade_date, symbol)

);

CREATE TABLE IF NOT EXISTS market_prediction_history (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_time TIMESTAMP,

    index_name TEXT,

    prediction TEXT,

    confidence REAL,

    strategy TEXT,

    trade TEXT,

    risk TEXT,

    score REAL,

    support REAL,

    resistance REAL,

    spot_price REAL,

    pcr REAL,

    avg_iv REAL,

    processed INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(trade_time, symbol)

);

CREATE TABLE IF NOT EXISTS trend_day_research (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_date DATE,

    index_name TEXT,

    opening_gap REAL,

    pcr REAL,

    avg_iv REAL,

    india_vix REAL,

    breadth REAL,

    trendiness_score REAL,

    trend_day INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(trade_date, index_name)

);

CREATE TABLE IF NOT EXISTS market_regime (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    trade_date DATE UNIQUE,

    trend REAL,

    volatility REAL,

    breadth REAL,

    institutional_flow REAL,

    sector_rotation REAL,

    regime_score REAL,

    market_regime TEXT,

    confidence REAL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);