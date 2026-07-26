"""
MarketBot Authentication Manager

Purpose:
    Centralize all authentication logic.

Responsibilities:
    - Read access token
    - Refresh token (future)
    - Validate token (future)
    - Switch broker implementations (future)

Version:
    Sprint 1
"""

import os
from dotenv import load_dotenv

load_dotenv()


def get_access_token():
    """
    Returns the configured access token.

    Future versions will automatically refresh
    expired tokens.
    """
    return os.getenv("UPSTOX_ACCESS_TOKEN")