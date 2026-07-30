from dataclasses import dataclass


@dataclass
class MarketState:
    # Identity
    symbol: str
    trade_time: str

    # Price
    spot_price: float
    change_pct: float = 0.0

    # Market Structure
    support: float = 0.0
    resistance: float = 0.0
    max_pain: float = 0.0

    # Options
    pcr: float = 0.0
    avg_iv: float = 0.0

    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0

    # Analytics
    reward_risk: float = 0.0
    market_location: str = "UNKNOWN"
    expected_move: float = 0.0
    trade_quality: float = 0.0

    # Intelligence
    iv_regime: str = "UNKNOWN"
    market_bias: str = "NEUTRAL"
    confidence: float = 0.0
    recommended_strategy: str = ""