"""
Base Broker Interface

Every broker implementation must inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseBroker(ABC):

    @abstractmethod
    def authenticate(self) -> str | None:
        """
        Authenticate with broker.

        Returns:
            Access token if successful.
        """
        pass

    @abstractmethod
    def get_option_chain(self, symbol: str, expiry: str) -> Any:
        """
        Return option chain data.
        """
        pass

    @abstractmethod
    def get_market_quote(self, symbol: str) -> Any:
        """
        Return market quote.
        """
        pass