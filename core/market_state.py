from dataclasses import dataclass
from datetime import datetime


@dataclass
class MarketState:

    symbol: str

    trade_time: datetime

    spot_price: float

    change_pct: float

    support: float

    resistance: float

    max_pain: float

    pcr: float

    avg_iv: float

    delta: float

    gamma: float

    theta: float

    vega: float

    reward_risk: float

    market_location: str

    expected_move: float

    trade_quality: float

    iv_regime: str

    market_bias: str

    confidence: float

    recommended_strategy: str