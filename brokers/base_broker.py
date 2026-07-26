"""
Base Broker Interface

Every broker implementation must inherit from this class.

Examples:
    - UpstoxBroker
    - ZerodhaBroker
    - AngelOneBroker
"""

from abc import ABC, abstractmethod


class BaseBroker(ABC):

    @abstractmethod
    def authenticate(self):
        """Authenticate with broker."""
        pass

    @abstractmethod
    def get_option_chain(self, symbol, expiry):
        """Fetch option chain."""
        pass

    @abstractmethod
    def get_market_quote(self, symbol):
        """Fetch latest quote."""
        pass