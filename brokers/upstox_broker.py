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

from authentication.token_manager import get_access_token
from brokers.base_broker import BaseBroker


class UpstoxBroker(BaseBroker):

    def authenticate(self):
        return get_access_token()

    def get_option_chain(self, symbol, expiry):
        raise NotImplementedError

    def get_market_quote(self, symbol):
        raise NotImplementedError