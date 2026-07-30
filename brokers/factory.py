"""
Broker Factory

Provides the configured broker implementation.
"""

from brokers.upstox_broker import UpstoxBroker


def get_broker():
    """
    Return the active broker instance.
    """
    return UpstoxBroker()