from dataclasses import dataclass


@dataclass
class TradeScore:

    score: int

    bias: str

    confidence: int

    risk: str

    trade: str

    strategy: str

    reasons: list[str]