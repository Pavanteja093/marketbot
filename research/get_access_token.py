import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

import requests

from config.upstox_config import (
    API_KEY,
    API_SECRET,
    REDIRECT_URI
)
5
AUTH_CODE = "******"
url = "https://api-v2.upstox.com/login/authorization/token"

payload = {
    "code": AUTH_CODE,
    "client_id": API_KEY,
    "client_secret": API_SECRET,
    "redirect_uri": REDIRECT_URI,
    "grant_type": "authorization_code"
}

headers = {
    "accept": "application/json",
    "Api-Version": "2.0",
    "Content-Type": "application/x-www-form-urlencoded"
}

response = requests.post(
    url,
    data=payload,
    headers=headers
)

print(response.status_code)
print(response.json())