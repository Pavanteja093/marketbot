from datetime import datetime

def get_days_to_expiry(expiry):

    expiry = datetime.strptime(expiry, "%Y-%m-%d")
    today = datetime.today()

    days = (expiry - today).days

    return max(days, 1)