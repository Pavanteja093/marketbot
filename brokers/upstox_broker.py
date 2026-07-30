"""
Upstox Broker

Current status:
    Skeleton implementation.

Future responsibilities:
    - Authentication
    - Token Refresh
    - Option Chain
    - Market Quotes
"""
from typing import Any

from authentication.token_manager import get_access_token
from brokers.base_broker import BaseBroker



class UpstoxBroker(BaseBroker):

    def authenticate(self) -> str | None:
        return get_access_token()

    def get_option_chain(self, symbol: str, expiry: str) -> Any:
        raise NotImplementedError

    def get_market_quote(self, symbol: str) -> Any:
        raise NotImplementedError