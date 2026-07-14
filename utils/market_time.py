from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def now():

    return datetime.now(IST)


def market_open():

    current = now()

    if current.weekday() >= 5:
        return False

    minutes = current.hour * 60 + current.minute

    return 555 <= minutes <= 930