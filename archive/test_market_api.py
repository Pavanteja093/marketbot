import sys
from pathlib import Path
import upstox_client

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from config.upstox_config import ACCESS_TOKEN

configuration = upstox_client.Configuration()
configuration.access_token = ACCESS_TOKEN

client = upstox_client.ApiClient(configuration)

market_api = upstox_client.MarketQuoteApi(client)

print("SUCCESS")
print(type(market_api))